<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { KBFile, TeachingMaterial } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import Skeleton from '@/components/common/Skeleton.vue';
import { KB_USER_ID, useAppStore } from '@/stores/appStore';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import type { ArtifactKind, ArtifactMeta } from '@/services/ai/artifactService';
import { isFullTextKbFileId, isFullUploadKbFileId } from '@/utils/kbFileId';
import { getKbSource, getKbSourceUi } from '@/utils/kbSource';
import { parseGenOutputFileId } from '@/utils/genOutputFileId';
import { matchArtifactByTime } from '@/utils/matchArtifactByTime';
import { trapTabKey } from '@/utils/focusTrap';
import { escapeHtml } from '@/utils/safeHtml';

interface Props {
  currentMaterial: TeachingMaterial;
}

const props = defineProps<Props>();
const { t } = useI18n();
const store = useAppStore();

const exportingKbFileId = ref<string | null>(null);
const loadingArtifacts = ref(false);
const artifacts = ref<ArtifactMeta[]>([]);
const artifactsError = ref<string | null>(null);
const downloadingArtifactId = ref<string | null>(null);
const deletingKbFileId = ref<string | null>(null);

const previewOpen = ref(false);
const previewLoading = ref(false);
const previewError = ref<string | null>(null);
const previewTitle = ref('');
const previewHtml = ref('');
const previewKbFile = ref<KBFile | null>(null);
const previewSourceArtifact = ref<ArtifactMeta | null>(null);
const previewDialogRef = ref<HTMLElement | null>(null);
const previewCloseButtonRef = ref<HTMLButtonElement | null>(null);
const previewRestoreFocusEl = ref<HTMLElement | null>(null);

const isDragging = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);

const normalizeStringArray = (raw: unknown): string[] => {
  if (!Array.isArray(raw)) return [];
  const result: string[] = [];
  const seen = new Set<string>();
  for (const item of raw) {
    const id = typeof item === 'string' ? item.trim() : '';
    if (!id) continue;
    if (seen.has(id)) continue;
    seen.add(id);
    result.push(id);
  }
  return result;
};

const selectedFullIdSet = computed(() => new Set(normalizeStringArray(props.currentMaterial.kbFileIds).filter(isFullTextKbFileId)));

const persistKbFileIds = (nextIds: string[]) => {
  store.patchMaterial(props.currentMaterial.id, { kbFileIds: normalizeStringArray(nextIds) });
};

const toggleFullSelected = (fileId: string) => {
  if (!fileId) return;
  const current = normalizeStringArray(props.currentMaterial.kbFileIds);
  const next = new Set(current);
  if (next.has(fileId)) next.delete(fileId);
  else next.add(fileId);
  persistKbFileIds(Array.from(next));
};

const clearSelectedFull = () => {
  const current = normalizeStringArray(props.currentMaterial.kbFileIds);
  persistKbFileIds(current.filter((id) => !isFullTextKbFileId(id)));
};

const kbOutputFiles = computed(() => {
  const materialId = props.currentMaterial.id;
  const prefix = `gen:${KB_USER_ID}:${materialId}:`;
  return (store.kbFiles || []).filter((file) => {
    const folderId = typeof file.folderId === 'number' ? file.folderId : 0;
    if (folderId !== 1) return false;
    if (file.sourceMaterialId && file.sourceMaterialId === materialId) return true;
    return (file.id || '').startsWith(prefix);
  });
});

const kbFullUploadFiles = computed(() => {
  const materialId = props.currentMaterial.id;
  const prefix = `full:${KB_USER_ID}:${materialId}:`;
  return (store.kbFiles || []).filter((file) => {
    const folderId = typeof file.folderId === 'number' ? file.folderId : 0;
    if (folderId !== 2) return false;
    return (file.id || '').startsWith(prefix) && isFullUploadKbFileId(file.id);
  });
});

const formatSize = (bytes: number) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const idx = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, idx);
  return `${value.toFixed(1)} ${units[idx]}`;
};

const formatDateTime = (value: unknown) => {
  if (value instanceof Date) {
    if (Number.isNaN(value.getTime())) return '';
    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(value);
  }

  const asNumber = typeof value === 'number' ? value : Number(value);
  if (Number.isFinite(asNumber) && asNumber > 0) {
    const ms = asNumber < 1_000_000_000_000 ? Math.floor(asNumber * 1000) : Math.floor(asNumber);
    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(ms));
  }

  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

const normalizeOutputKind = (value: string) => (value || '').trim().toLowerCase();

const getGenOutputKind = (fileId: string): string => {
  return parseGenOutputFileId(fileId)?.kind || '';
};

const getKbFileTimeMs = (file: KBFile | null | undefined): number => {
  const parsed = file?.id ? parseGenOutputFileId(file.id) : null;
  if (parsed?.epochMs && Number.isFinite(parsed.epochMs) && parsed.epochMs > 0) return parsed.epochMs;
  const uploadedAt = (file as any)?.uploadedAt;
  const t = uploadedAt instanceof Date ? uploadedAt.getTime() : Number(uploadedAt) || 0;
  return Number.isFinite(t) && t > 0 ? t : 0;
};

type OutputGroup = 'outline' | 'lesson' | 'ppt' | 'other';

const classifyOutputGroup = (kind: string): OutputGroup => {
  const normalized = normalizeOutputKind(kind);
  if (!normalized) return 'other';
  if (normalized === 'outline') return 'outline';
  if (normalized === 'lesson' || normalized.includes('lesson')) return 'lesson';
  if (normalized === 'slides' || normalized === 'slides_final' || normalized === 'ppt' || normalized.includes('slide') || normalized.includes('ppt')) {
    return 'ppt';
  }
  return 'other';
};

const lockedOutputIdSet = computed(() => {
  const set = new Set<string>();
  const outputs = kbOutputFiles.value;
  if (!Array.isArray(outputs) || outputs.length === 0) return set;

  const pickLatest = (items: KBFile[]) => {
    let latest: KBFile | null = null;
    let bestT = 0;
    for (const f of items) {
      const t = getKbFileTimeMs(f);
      if (!latest || t > bestT) {
        latest = f;
        bestT = t;
      }
    }
    return latest;
  };

  const byOutline: KBFile[] = [];
  const byLesson: KBFile[] = [];
  const byPpt: KBFile[] = [];

  for (const file of outputs) {
    const kind = getGenOutputKind(file.id);
    const group = classifyOutputGroup(kind);
    if (group === 'outline') byOutline.push(file);
    else if (group === 'lesson') byLesson.push(file);
    else if (group === 'ppt') byPpt.push(file);
  }

  const latestOutline = pickLatest(byOutline);
  const latestLesson = pickLatest(byLesson);
  const latestPpt = pickLatest(byPpt);
  if (latestOutline?.id) set.add(latestOutline.id);
  if (latestLesson?.id) set.add(latestLesson.id);
  if (latestPpt?.id) set.add(latestPpt.id);
  return set;
});

const isLockedGeneratedOutput = (file: KBFile | null | undefined): boolean => {
  const id = (file?.id || '').trim();
  if (!id.startsWith('gen:')) return false;
  return lockedOutputIdSet.value.has(id);
};

const inferArtifactKindFromGenKind = (genKind: string): ArtifactKind | null => {
  const kind = (genKind || '').trim().toLowerCase();
  if (!kind) return null;
  if (kind === 'lesson' || kind.includes('lesson')) return 'docx';
  if (kind === 'slides' || kind.includes('slide') || kind === 'ppt' || kind.includes('ppt')) return 'pptx';
  return null;
};

const outputKindWeight = (kind: string) => {
  const normalized = (kind || '').trim().toLowerCase();
  if (normalized === 'outline') return 10;
  if (normalized === 'lesson') return 20;
  if (normalized === 'slides' || normalized === 'ppt') return 30;
  if (normalized === 'slides_final') return 31;
  return 999;
};

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || 'download';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const updateFiles = (next: KBFile[]) => {
  store.setKbFiles(next);
};

const updateFileStatus = (fileId: string, status: KBFile['status'], progress?: number) => {
  const next = (store.kbFiles || []).map((f) => (f.id === fileId ? { ...f, status, progress: progress ?? f.progress } : f));
  updateFiles(next);
};

const buildFullUploadFileId = (materialId: string) => {
  const epochMs = Date.now();
  const rand = Math.floor(Math.random() * 1000)
    .toString()
    .padStart(3, '0');
  return `full:${KB_USER_ID}:${materialId}:${epochMs}:${rand}`;
};

const openFilePicker = () => {
  fileInputRef.value?.click();
};

const handleFilePicked = (e: Event) => {
  const input = e.target as HTMLInputElement | null;
  const file = input?.files?.[0];
  if (input) input.value = '';
  if (!file) return;
  void uploadFullTextFile(file);
};

const handleDragOver = (e: DragEvent) => {
  e.preventDefault();
  isDragging.value = true;
};

const handleDragLeave = (e: DragEvent) => {
  e.preventDefault();
  isDragging.value = false;
};

const handleDrop = (e: DragEvent) => {
  e.preventDefault();
  isDragging.value = false;
  const droppedFiles = Array.from(e.dataTransfer?.files || []);
  if (droppedFiles.length > 0) {
    const first = droppedFiles[0];
    if (first) void uploadFullTextFile(first);
  }
};

const refreshKbFilesFromBackend = async () => {
  try {
    const list = await aiService.kbListFiles({ userId: KB_USER_ID });
    const now = new Date();
    const pending = (store.kbFiles || []).filter((f) => f.status === 'uploading' || f.status === 'processing');
    const mapped = list.map((it) => {
      const existing = (store.kbFiles || []).find((f) => f.id === it.file_id);
      const createdAt = typeof it.created_at === 'number' && it.created_at > 0
        ? new Date(it.created_at < 1_000_000_000_000 ? it.created_at * 1000 : it.created_at)
        : existing?.uploadedAt || now;
      return {
        id: it.file_id,
        name: it.file_name || it.file_id,
        size: typeof it.file_size === 'number' ? it.file_size : existing?.size || 0,
        type: it.file_type || existing?.type || 'unknown',
        status: 'ready' as const,
        uploadedAt: createdAt,
        folderId: typeof it.folder_id === 'number' ? it.folder_id : existing?.folderId || 0,
        sourceType: it.source_type || existing?.sourceType,
        sourceMaterialId: it.source_material_id || existing?.sourceMaterialId,
        sourceMaterialTitle: it.source_material_title || existing?.sourceMaterialTitle,
      } satisfies KBFile;
    });
    updateFiles([...pending, ...mapped]);
  } catch (e) {
    console.warn('知识库列表同步失败（已忽略）', e);
  }
};

const uploadFullTextFile = async (file: File) => {
  const materialId = props.currentMaterial.id;
  const fileId = buildFullUploadFileId(materialId);

  const newFile: KBFile = {
    id: fileId,
    name: file.name,
    size: file.size,
    type: file.name.split('.').pop() || 'unknown',
    status: 'uploading',
    uploadedAt: new Date(),
    progress: 0,
    folderId: 2,
    sourceType: 'upload',
  };

  updateFiles([...(store.kbFiles || []), newFile]);

  try {
    updateFileStatus(fileId, 'processing', 95);

    await aiService.kbUpload({
      userId: KB_USER_ID,
      file,
      folderId: 2,
      fileId,
    });

    updateFileStatus(fileId, 'ready', 100);
    toast.success(t('kb.toast.uploaded'));
    await refreshKbFilesFromBackend();
  } catch (e) {
    updateFileStatus(fileId, 'error');
    console.error(e);
    toast.error(t('kb.toast.upload_failed'));
  }
};

const purgeKbFileReferences = (fileId: string) => {
  const target = fileId.trim();
  if (!target) return;

  for (const material of store.materials) {
    const ids = normalizeStringArray(material.kbFileIds);
    if (!ids.includes(target)) continue;
    store.patchMaterial(material.id, { kbFileIds: ids.filter((id) => id !== target) });
  }
};

const handleDeleteKbFile = async (file: KBFile) => {
  const id = (file?.id || '').trim();
  if (!id) return;
  if (isLockedGeneratedOutput(file)) {
    toast.info(t('kb.toast.locked_output'));
    return;
  }
  if (!confirm(t('kb.confirm.delete'))) return;

  // 本地错误条目：直接移除
  if (file.status === 'error') {
    updateFiles((store.kbFiles || []).filter((f) => f.id !== id));
    purgeKbFileReferences(id);
    toast.success(t('kb.action.delete'));
    return;
  }

  deletingKbFileId.value = id;
  try {
    await aiService.kbDeleteFile({ userId: KB_USER_ID, fileId: id });
    updateFiles((store.kbFiles || []).filter((f) => f.id !== id));
    purgeKbFileReferences(id);
    toast.success(t('kb.action.delete'));
    await refreshKbFilesFromBackend();
  } catch (e) {
    console.error(e);
    toast.error(t('kb.toast.delete_failed'));
  } finally {
    if (deletingKbFileId.value === id) deletingKbFileId.value = null;
  }
};

const handleExportKb = async (file: KBFile) => {
  if (file.status !== 'ready') return;
  exportingKbFileId.value = file.id;
  try {
    const { blob, filename } = await aiService.kbExportFile({ userId: KB_USER_ID, fileId: file.id });
    downloadBlob(blob, filename || file.name || 'output.md');
    toast.success(t('kb.toast.exported'));
  } catch (e) {
    console.error(e);
    toast.error(t('kb.toast.export_failed'));
  } finally {
    exportingKbFileId.value = null;
  }
};

const refreshArtifacts = async () => {
  artifactsError.value = null;
  loadingArtifacts.value = true;
  try {
    artifacts.value = await aiService.listArtifacts({ userId: KB_USER_ID, materialId: props.currentMaterial.id });
  } catch (e: any) {
    console.error(e);
    artifactsError.value = (e?.message as string) || '加载失败';
    artifacts.value = [];
  } finally {
    loadingArtifacts.value = false;
  }
};

const sortArtifactsByCreatedAtDesc = (items: ArtifactMeta[]) =>
  [...items].sort((a, b) => (b.created_at ?? 0) - (a.created_at ?? 0));

const docxArtifacts = computed(() => sortArtifactsByCreatedAtDesc(artifacts.value.filter((a) => a.kind === 'docx')));
const pptxArtifacts = computed(() => sortArtifactsByCreatedAtDesc(artifacts.value.filter((a) => a.kind === 'pptx')));

const kbOutputFilesSorted = computed(() => {
  return [...kbOutputFiles.value].sort((a, b) => {
    const ak = getGenOutputKind(a.id);
    const bk = getGenOutputKind(b.id);
    const aw = outputKindWeight(ak);
    const bw = outputKindWeight(bk);
    if (aw !== bw) return aw - bw;
    const at = getKbFileTimeMs(a);
    const bt = getKbFileTimeMs(b);
    if (at !== bt) return bt - at;
    return (a.name || a.id).localeCompare(b.name || b.id);
  });
});

const kbFullUploadFilesSorted = computed(() => {
  return [...kbFullUploadFiles.value].sort((a, b) => {
    const at = a.uploadedAt instanceof Date ? a.uploadedAt.getTime() : Number(a.uploadedAt) || 0;
    const bt = b.uploadedAt instanceof Date ? b.uploadedAt.getTime() : Number(b.uploadedAt) || 0;
    if (at !== bt) return bt - at;
    return (a.name || a.id).localeCompare(b.name || b.id);
  });
});

type OutputCardMode = 'full_upload' | 'output' | 'artifact';

type SourceTagUi = ReturnType<typeof getKbSourceUi>;

interface OutputCard {
  key: string;
  title: string;
  mode: OutputCardMode;
  kbFile: KBFile | null;
  artifactKind: ArtifactKind | null;
  artifacts: ArtifactMeta[];
  latestArtifact: ArtifactMeta | null;
  sourceUi: SourceTagUi;
}

const buildFallbackTitle = (kind: ArtifactKind) => {
  const base = (props.currentMaterial.title || '').trim();
  if (kind === 'pptx') return `PPT:${base || '未命名'}`;
  if (kind === 'docx') return `教案:${base || '未命名'}`;
  return base || '未命名';
};

const outputCards = computed<OutputCard[]>(() => {
  const cards: OutputCard[] = [];
  const usedArtifactKinds = new Set<ArtifactKind>();

  for (const file of kbFullUploadFilesSorted.value) {
    cards.push({
      key: file.id,
      title: (file.name || '').trim() || file.id,
      mode: 'full_upload',
      kbFile: file,
      artifactKind: null,
      artifacts: [],
      latestArtifact: null,
      sourceUi: getKbSourceUi(getKbSource(typeof file.folderId === 'number' ? file.folderId : undefined)),
    });
  }

  for (const file of kbOutputFilesSorted.value) {
    const genKind = getGenOutputKind(file.id);
    const artifactKind = inferArtifactKindFromGenKind(genKind);
    const artifactsForCard = artifactKind === 'docx' ? docxArtifacts.value : artifactKind === 'pptx' ? pptxArtifacts.value : [];
    if (artifactKind) usedArtifactKinds.add(artifactKind);
    const matchedArtifact = artifactKind ? matchArtifactByTime(artifactsForCard, getKbFileTimeMs(file) || null) : null;

    cards.push({
      key: file.id,
      title: (file.name || '').trim() || file.id,
      mode: 'output',
      kbFile: file,
      artifactKind,
      artifacts: artifactsForCard,
      latestArtifact: matchedArtifact,
      sourceUi: getKbSourceUi(getKbSource(typeof file.folderId === 'number' ? file.folderId : undefined)),
    });
  }

  if (docxArtifacts.value.length > 0 && !usedArtifactKinds.has('docx')) {
    cards.push({
      key: 'artifact:docx',
      title: buildFallbackTitle('docx'),
      mode: 'artifact',
      kbFile: null,
      artifactKind: 'docx',
      artifacts: docxArtifacts.value,
      latestArtifact: docxArtifacts.value[0] || null,
      sourceUi: getKbSourceUi('generated'),
    });
  }

  if (pptxArtifacts.value.length > 0 && !usedArtifactKinds.has('pptx')) {
    cards.push({
      key: 'artifact:pptx',
      title: buildFallbackTitle('pptx'),
      mode: 'artifact',
      kbFile: null,
      artifactKind: 'pptx',
      artifacts: pptxArtifacts.value,
      latestArtifact: pptxArtifacts.value[0] || null,
      sourceUi: getKbSourceUi('generated'),
    });
  }

  return cards.sort((a, b) => {
    const modeWeight = (mode: OutputCardMode) => (mode === 'full_upload' ? 0 : mode === 'output' ? 1 : 2);

    const mw = modeWeight(a.mode) - modeWeight(b.mode);
    if (mw !== 0) return mw;

    if (a.mode === 'full_upload' && b.mode === 'full_upload') {
      const at = a.kbFile?.uploadedAt instanceof Date ? a.kbFile.uploadedAt.getTime() : Number(a.kbFile?.uploadedAt) || 0;
      const bt = b.kbFile?.uploadedAt instanceof Date ? b.kbFile.uploadedAt.getTime() : Number(b.kbFile?.uploadedAt) || 0;
      if (at !== bt) return bt - at;
      return a.title.localeCompare(b.title);
    }

    if (a.mode === 'output' && b.mode === 'output') {
      const ak = a.kbFile ? getGenOutputKind(a.kbFile.id) : '';
      const bk = b.kbFile ? getGenOutputKind(b.kbFile.id) : '';
      const aw = outputKindWeight(ak);
      const bw = outputKindWeight(bk);
      if (aw !== bw) return aw - bw;
      const at = getKbFileTimeMs(a.kbFile);
      const bt = getKbFileTimeMs(b.kbFile);
      if (at !== bt) return bt - at;
      return a.title.localeCompare(b.title);
    }

    return a.title.localeCompare(b.title);
  });
});

const handleDownloadArtifact = async (artifact: ArtifactMeta) => {
  if (!artifact?.artifact_id) return;
  downloadingArtifactId.value = artifact.artifact_id;
  try {
    const { blob, filename } = await aiService.downloadArtifact({
      userId: KB_USER_ID,
      materialId: props.currentMaterial.id,
      artifactId: artifact.artifact_id,
    });
    downloadBlob(blob, filename || artifact.file_name || 'artifact');
    toast.success(t('kb.toast.exported'));
  } catch (e) {
    console.error(e);
    toast.error(t('kb.toast.export_failed'));
  } finally {
    downloadingArtifactId.value = null;
  }
};

const renderInlineStyles = (text: string) => {
  const parts = String(text || '').split(/(\*\*.*?\*\*)/g);
  return parts
    .map((part) => {
      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        return `<strong class="font-bold text-slate-900 dark:text-white bg-indigo-50 dark:bg-indigo-900/30 px-1 rounded mx-0.5">${escapeHtml(part.slice(2, -2))}</strong>`;
      }
      return escapeHtml(part);
    })
    .join('');
};

const renderMarkdownToHtml = (content: string) => {
  const raw = String(content || '');
  if (!raw.trim()) return '';

  const lines = raw.split('\n');
  return lines
    .map((line, idx) => {
      if (line.startsWith('# ')) {
        return `<h1 key="${idx}" class="text-xl md:text-2xl font-black text-slate-900 dark:text-white mt-2 mb-3 border-b pb-2 border-slate-200 dark:border-slate-700">${escapeHtml(line.replace('# ', ''))}</h1>`;
      }
      if (line.startsWith('## ')) {
        return `<h2 key="${idx}" class="text-base md:text-lg font-extrabold text-indigo-600 dark:text-indigo-400 mt-4 mb-2">${escapeHtml(line.replace('## ', ''))}</h2>`;
      }
      if (line.startsWith('### ')) {
        return `<h3 key="${idx}" class="text-sm md:text-base font-bold text-slate-700 dark:text-slate-200 mt-3 mb-1">${escapeHtml(line.replace('### ', ''))}</h3>`;
      }

      if (line.startsWith('- ') || line.startsWith('* ')) {
        const text = line.replace(/^[-*] /, '');
        return `<li key="${idx}" class="ml-4 list-disc marker:text-indigo-400 pl-2">${renderInlineStyles(text)}</li>`;
      }

      if (!line.trim()) {
        return `<br key="${idx}" />`;
      }

      return `<p key="${idx}" class="text-sm leading-6 text-slate-700 dark:text-slate-200">${renderInlineStyles(line)}</p>`;
    })
    .join('');
};

const closePreview = () => {
  previewOpen.value = false;
};

const openPreview = async (card: OutputCard) => {
  const file = card.kbFile;
  if (!file) return;
  if (file.status !== 'ready') return;

  previewKbFile.value = file;
  previewSourceArtifact.value = card.latestArtifact;
  previewTitle.value = card.title;
  previewError.value = null;
  previewHtml.value = '';
  previewLoading.value = true;
  previewOpen.value = true;

  try {
    const { blob } = await aiService.kbExportFile({ userId: KB_USER_ID, fileId: file.id });
    const text = await blob.text();
    previewHtml.value = renderMarkdownToHtml(text);
  } catch (e) {
    console.error(e);
    previewError.value = '预览加载失败，请稍后重试。';
    previewHtml.value = '';
  } finally {
    previewLoading.value = false;
  }
};

const handlePreviewKeydown = (e: KeyboardEvent) => {
  if (!previewOpen.value) return;
  if (e.key === 'Escape') {
    closePreview();
    return;
  }
  if (e.key === 'Tab' && previewDialogRef.value) {
    trapTabKey(e, previewDialogRef.value);
  }
};

watch(
  () => previewOpen.value,
  async (open) => {
    if (typeof window === 'undefined') return;
    if (open) {
      previewRestoreFocusEl.value = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', handlePreviewKeydown);
      await nextTick();
      previewCloseButtonRef.value?.focus?.();
      if (document.activeElement !== previewCloseButtonRef.value) {
        previewDialogRef.value?.focus?.();
      }
      return;
    }

    document.body.style.overflow = '';
    document.removeEventListener('keydown', handlePreviewKeydown);
    previewKbFile.value = null;
    previewSourceArtifact.value = null;
    previewLoading.value = false;
    previewError.value = null;
    previewTitle.value = '';
    previewHtml.value = '';
    await nextTick();
    const el = previewRestoreFocusEl.value;
    if (el && document.contains(el)) el.focus();
  },
  { flush: 'post' },
);

watch(
  () => props.currentMaterial.id,
  () => {
    closePreview();
    void refreshArtifacts();
  },
  { immediate: true },
);

const handleArtifactsUpdated = (evt: Event) => {
  const detail = (evt as CustomEvent<any>)?.detail;
  const materialId = typeof detail?.materialId === 'string' ? detail.materialId : null;
  if (materialId && materialId !== props.currentMaterial.id) return;
  void refreshArtifacts();
};

onMounted(() => {
  if (typeof window === 'undefined') return;
  window.addEventListener('teachdo:artifacts-updated', handleArtifactsUpdated as EventListener);
});

onBeforeUnmount(() => {
  if (typeof window === 'undefined') return;
  window.removeEventListener('teachdo:artifacts-updated', handleArtifactsUpdated as EventListener);
  document.removeEventListener('keydown', handlePreviewKeydown);
  document.body.style.overflow = '';
});

defineExpose({
  refreshArtifacts,
  loadingArtifacts,
  clearSelectedFull,
});
</script>

<template>
  <div class="h-full flex flex-col gap-2">
    <input ref="fileInputRef" type="file" class="hidden" @change="handleFilePicked" />

    <button
      type="button"
      class="mx-4 mt-3 mb-3 p-4 border-2 border-dashed rounded-2xl flex items-center gap-3 transition-colors text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-100 dark:focus-visible:ring-offset-slate-950"
      :class="isDragging
        ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
        : 'border-indigo-300/80 dark:border-indigo-700/70 bg-indigo-50/50 dark:bg-indigo-900/10 hover:bg-indigo-50 dark:hover:bg-indigo-900/20'"
      @click="openFilePicker"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop="handleDrop"
    >
      <div class="w-10 h-10 rounded-xl bg-white/80 dark:bg-slate-900/40 border border-indigo-200 dark:border-indigo-700/50 flex items-center justify-center flex-shrink-0">
        <LucideIcon name="upload-cloud" :size="18" :class="isDragging ? 'text-indigo-600 dark:text-indigo-300' : 'text-indigo-500 dark:text-indigo-400'" />
      </div>
      <div class="min-w-0">
        <p class="text-sm font-bold text-slate-800 dark:text-slate-100 truncate">{{ t('kb.drop.title') }}</p>
        <p class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ t('kb.drop.desc') }}</p>
      </div>
    </button>

    <div class="flex-1 overflow-y-auto overscroll-contain custom-scrollbar">
      <div v-if="artifactsError" class="px-4 pb-2 text-xs text-red-600 dark:text-red-300">
        {{ artifactsError }}
      </div>

      <div v-if="loadingArtifacts && outputCards.length === 0" class="px-4 pb-4 space-y-2" role="status" aria-live="polite">
        <div
          v-for="i in 6"
          :key="`out-skel-${i}`"
          class="rounded-2xl border border-slate-200/70 dark:border-slate-800/60 bg-indigo-50/60 dark:bg-indigo-900/10 px-3 py-3"
        >
          <Skeleton class="h-4 w-3/4" />
          <Skeleton class="h-3 w-1/2 mt-2 opacity-80" />
        </div>
      </div>

      <div v-else-if="outputCards.length === 0" class="flex flex-col items-center justify-center py-10 text-slate-400 px-4">
        <LucideIcon name="file" :size="32" class="mb-2 opacity-40" />
        <p class="text-sm font-bold text-slate-600 dark:text-slate-300">{{ t('workspace.outputs.empty_title') }}</p>
        <p class="mt-1 text-xs text-slate-500 dark:text-slate-400 text-center">{{ t('workspace.outputs.empty_desc') }}</p>
      </div>

      <div v-else class="px-4 pb-4 space-y-1">
        <div
          v-for="card in outputCards"
          :key="card.key"
          class="group rounded-2xl border shadow-sm transition-[background-color,border-color,box-shadow] duration-200 px-3 pt-2 pb-1"
          :class="card.kbFile && selectedFullIdSet.has(card.kbFile.id)
            ? 'border-indigo-300/80 bg-indigo-50/90 dark:border-indigo-700/60 dark:bg-indigo-900/20 ring-2 ring-indigo-500/30 ring-inset'
            : 'border-slate-200/70 dark:border-slate-800/60 bg-indigo-50/60 dark:bg-indigo-900/10 hover:bg-indigo-50/80 dark:hover:bg-indigo-900/20 hover:border-indigo-200 dark:hover:border-indigo-700/40'"
        >
          <div class="flex items-start justify-between gap-2">
            <label
              v-if="card.kbFile"
              :for="`out-select-${card.key}`"
              class="min-w-0 flex-1 cursor-pointer"
	            >
	              <div class="font-bold text-[12px] leading-tight text-slate-800 dark:text-slate-100 truncate" :title="card.title">
	                {{ card.title }}
	              </div>
	              <div class="mt-0.5 flex items-center gap-1 text-[10px] leading-tight text-slate-500 dark:text-slate-400 min-w-0">
	                <template v-if="card.kbFile.size">
	                  <span class="font-mono shrink-0">{{ formatSize(card.kbFile.size) }}</span>
	                </template>
	                <template v-if="card.kbFile.uploadedAt">
	                  <span v-if="card.kbFile.size" class="text-slate-300 dark:text-slate-700 shrink-0">•</span>
	                  <span class="shrink-0">{{ formatDateTime(card.kbFile.uploadedAt) }}</span>
	                </template>
	              </div>
	            </label>

	            <div v-else class="min-w-0 flex-1">
	              <div class="font-bold text-[12px] leading-tight text-slate-800 dark:text-slate-100 truncate" :title="card.title">
	                {{ card.title }}
	              </div>
	              <div class="mt-0.5 flex items-center gap-1 text-[10px] leading-tight text-slate-500 dark:text-slate-400 min-w-0">
	                <template v-if="card.latestArtifact?.size">
	                  <span class="font-mono shrink-0">{{ formatSize(card.latestArtifact.size) }}</span>
	                </template>
	                <template v-if="card.latestArtifact?.created_at">
	                  <span v-if="card.latestArtifact?.size" class="text-slate-300 dark:text-slate-700 shrink-0">•</span>
	                  <span class="shrink-0">{{ formatDateTime(card.latestArtifact.created_at) }}</span>
	                </template>
	              </div>
	            </div>

            <input
              v-if="card.kbFile"
              :id="`out-select-${card.key}`"
              type="checkbox"
              class="mt-0.5 h-4 w-4 accent-indigo-600 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-100 dark:focus-visible:ring-offset-slate-950"
              :checked="selectedFullIdSet.has(card.kbFile.id)"
              :disabled="card.kbFile.status !== 'ready'"
              :aria-label="t('kb.picker.toggle')"
              @change="() => toggleFullSelected(card.kbFile!.id)"
            />
            <div v-else class="mt-0.5 w-4 h-4"></div>
          </div>

	          <div class="mt-0.5 flex items-center justify-between gap-2">
	            <div class="flex flex-wrap items-center gap-1 min-w-0 flex-1">
	              <span
	                v-if="card.kbFile?.status === 'processing'"
	                class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] leading-none font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/25 dark:text-amber-200"
	              >
	                <LucideIcon name="loader-2" :size="11" class="animate-spin" /> {{ t('kb.status.processing') }}
	              </span>
	              <span
	                v-else-if="card.kbFile?.status === 'uploading'"
	                class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] leading-none font-bold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/25 dark:text-indigo-200"
	              >
	                <LucideIcon name="loader-2" :size="11" class="animate-spin" /> {{ t('kb.status.uploading') }}
	              </span>
	              <span
	                v-else-if="card.kbFile?.status === 'error'"
	                class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] leading-none font-bold bg-red-100 text-red-700 dark:bg-red-900/25 dark:text-red-300"
	              >
	                <LucideIcon name="alert-circle" :size="11" /> {{ t('kb.status.error') }}
	              </span>

	              <span
	                :class="card.sourceUi.className"
	                :title="t(card.sourceUi.i18nTitleKey)"
	                :aria-label="t(card.sourceUi.i18nTitleKey)"
	                class="shrink-0"
	              >
	                <LucideIcon :name="card.sourceUi.icon" :size="12" />
	                {{ t(card.sourceUi.i18nKey) }}
	              </span>
	            </div>

            <div class="flex items-center gap-1 shrink-0">
              <button
                v-if="card.mode === 'output' && card.kbFile"
                type="button"
                class="w-9 h-9 inline-flex items-center justify-center rounded-xl text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
                aria-label="预览"
                title="预览"
                :disabled="card.kbFile.status !== 'ready'"
                @click="openPreview(card)"
              >
                <LucideIcon name="eye" :size="16" />
              </button>

              <button
                type="button"
                class="w-9 h-9 inline-flex items-center justify-center rounded-xl text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
                aria-label="下载md"
                title="下载md"
                :disabled="!card.kbFile || card.kbFile.status !== 'ready' || exportingKbFileId === card.kbFile.id"
                @click="card.kbFile ? handleExportKb(card.kbFile) : null"
              >
                <LucideIcon name="download" :size="16" />
              </button>

              <button
                v-if="card.mode !== 'full_upload' && (card.mode === 'artifact' || card.artifactKind)"
                type="button"
                class="w-9 h-9 inline-flex items-center justify-center rounded-xl text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
                aria-label="下载源文件"
                :title="card.latestArtifact ? '下载源文件' : t('kb.tooltip.source_not_ready')"
                :disabled="!card.latestArtifact || downloadingArtifactId === card.latestArtifact.artifact_id"
                @click="card.latestArtifact ? handleDownloadArtifact(card.latestArtifact) : null"
              >
                <LucideIcon name="file-down" :size="16" />
              </button>

		              <button
		                v-if="card.kbFile"
		                type="button"
		                class="w-9 h-9 inline-flex items-center justify-center rounded-xl text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/40"
		                :aria-label="isLockedGeneratedOutput(card.kbFile) ? t('kb.action.locked') : t('kb.action.delete')"
		                :title="isLockedGeneratedOutput(card.kbFile) ? t('kb.tooltip.locked_output') : t('kb.action.delete')"
		                :disabled="card.kbFile.status === 'uploading' || card.kbFile.status === 'processing' || deletingKbFileId === card.kbFile.id"
		                @click="handleDeleteKbFile(card.kbFile)"
		              >
		                <LucideIcon :name="isLockedGeneratedOutput(card.kbFile) ? 'lock' : 'trash-2'" :size="16" />
		              </button>
	            </div>
	          </div>
	        </div>
	      </div>
    </div>
  </div>

  <Teleport to="body">
    <Transition name="td-modal">
      <div v-if="previewOpen" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <button
          type="button"
          class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
          :aria-label="t('common.close')"
          @click="closePreview"
        />

        <div
          ref="previewDialogRef"
          class="relative w-full max-w-3xl rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl outline-none td-modal-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="output-preview-title"
          tabindex="-1"
          @click.stop
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200/60 dark:border-slate-800/60">
            <div class="min-w-0">
              <h3 id="output-preview-title" class="text-sm font-black text-slate-900 dark:text-white truncate" :title="previewTitle">
                {{ previewTitle || '预览' }}
              </h3>
              <div v-if="previewKbFile" class="mt-1 flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
                <span v-if="previewKbFile.size" class="font-mono">{{ formatSize(previewKbFile.size) }}</span>
                <span v-if="previewKbFile.size && previewKbFile.uploadedAt" class="text-slate-300 dark:text-slate-700">•</span>
                <span v-if="previewKbFile.uploadedAt">{{ formatDateTime(previewKbFile.uploadedAt) }}</span>
              </div>
            </div>
            <button
              ref="previewCloseButtonRef"
              type="button"
              class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              :aria-label="t('common.close')"
              @click="closePreview"
            >
              <LucideIcon name="x" :size="18" />
            </button>
          </div>

          <div class="px-5 py-4">
            <div v-if="previewError" class="mb-3 text-xs font-bold text-red-600 dark:text-red-300">
              {{ previewError }}
            </div>

            <div v-if="previewLoading" class="flex items-center gap-2 text-xs font-bold text-slate-500 dark:text-slate-300">
              <LucideIcon name="loader-2" :size="14" class="animate-spin" />
              <span>{{ t('common.loading') }}</span>
            </div>

            <div v-else class="max-h-[65vh] overflow-y-auto custom-scrollbar pr-1">
              <div v-if="previewHtml" class="space-y-2" v-html="previewHtml"></div>
              <div v-else class="text-xs text-slate-400">
                暂无内容
              </div>
            </div>
          </div>

          <div class="px-5 py-4 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center justify-end gap-2 bg-slate-50/40 dark:bg-slate-950/20">
            <button type="button" class="td-btn-secondary" @click="closePreview">
              {{ t('sidebar.cancel') }}
            </button>
            <button
              type="button"
              class="td-btn-secondary"
              :disabled="!previewKbFile || previewKbFile.status !== 'ready' || exportingKbFileId === previewKbFile.id"
              @click="previewKbFile ? handleExportKb(previewKbFile) : null"
            >
              <LucideIcon name="download" class="w-4 h-4" />
              下载 md
            </button>
            <button
              type="button"
              class="td-btn-primary"
              :disabled="!previewSourceArtifact || downloadingArtifactId === previewSourceArtifact.artifact_id"
              :title="previewSourceArtifact ? '下载源文件' : t('kb.tooltip.source_not_ready')"
              @click="previewSourceArtifact ? handleDownloadArtifact(previewSourceArtifact) : null"
            >
              <LucideIcon name="file-down" class="w-4 h-4" />
              下载源文件
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
