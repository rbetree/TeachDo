<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { KBFile, TeachingMaterial } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import Skeleton from '@/components/common/Skeleton.vue';
import { KB_USER_ID, useAppStore } from '@/stores/appStore';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import type { ArtifactKind, ArtifactMeta } from '@/services/ai/artifactService';

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

const isGenFileId = (fileId: string) => (fileId || '').startsWith('gen:');

const selectedGenIdSet = computed(() => new Set(normalizeStringArray(props.currentMaterial.kbFileIds).filter(isGenFileId)));

const persistKbFileIds = (nextIds: string[]) => {
  store.patchMaterial(props.currentMaterial.id, { kbFileIds: normalizeStringArray(nextIds) });
};

const toggleGenSelected = (fileId: string) => {
  if (!fileId) return;
  const current = normalizeStringArray(props.currentMaterial.kbFileIds);
  const next = new Set(current);
  if (next.has(fileId)) next.delete(fileId);
  else next.add(fileId);
  persistKbFileIds(Array.from(next));
};

const clearSelectedGen = () => {
  const current = normalizeStringArray(props.currentMaterial.kbFileIds);
  persistKbFileIds(current.filter((id) => !isGenFileId(id)));
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

const parseGenFileId = (fileId: string) => {
  const parts = (fileId || '').split(':');
  if (parts[0] !== 'gen' || parts.length < 4) return null;
  const user = (parts[1] || '').trim();
  const materialId = (parts[2] || '').trim();
  const kind = parts.slice(3).join(':').trim();
  if (!user || !materialId || !kind) return null;
  return { user, materialId, kind };
};

const getGenTag = (fileId: string) => {
  const meta = parseGenFileId(fileId);
  if (!meta) return (fileId || '').trim();
  return `gen:${meta.user}`;
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
    const ak = parseGenFileId(a.id)?.kind || '';
    const bk = parseGenFileId(b.id)?.kind || '';
    const aw = outputKindWeight(ak);
    const bw = outputKindWeight(bk);
    if (aw !== bw) return aw - bw;
    return (a.name || a.id).localeCompare(b.name || b.id);
  });
});

interface OutputCard {
  key: string;
  title: string;
  genTag: string;
  kbFile: KBFile | null;
  artifactKind: ArtifactKind | null;
  artifacts: ArtifactMeta[];
  latestArtifact: ArtifactMeta | null;
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

  for (const file of kbOutputFilesSorted.value) {
    const genKind = parseGenFileId(file.id)?.kind || '';
    const artifactKind = inferArtifactKindFromGenKind(genKind);
    const artifactsForCard = artifactKind === 'docx' ? docxArtifacts.value : artifactKind === 'pptx' ? pptxArtifacts.value : [];
    if (artifactKind) usedArtifactKinds.add(artifactKind);

    cards.push({
      key: file.id,
      title: (file.name || '').trim() || file.id,
      genTag: getGenTag(file.id),
      kbFile: file,
      artifactKind,
      artifacts: artifactsForCard,
      latestArtifact: artifactsForCard[0] || null,
    });
  }

  if (docxArtifacts.value.length > 0 && !usedArtifactKinds.has('docx')) {
    cards.push({
      key: 'artifact:docx',
      title: buildFallbackTitle('docx'),
      genTag: 'artifact:docx',
      kbFile: null,
      artifactKind: 'docx',
      artifacts: docxArtifacts.value,
      latestArtifact: docxArtifacts.value[0] || null,
    });
  }

  if (pptxArtifacts.value.length > 0 && !usedArtifactKinds.has('pptx')) {
    cards.push({
      key: 'artifact:pptx',
      title: buildFallbackTitle('pptx'),
      genTag: 'artifact:pptx',
      kbFile: null,
      artifactKind: 'pptx',
      artifacts: pptxArtifacts.value,
      latestArtifact: pptxArtifacts.value[0] || null,
    });
  }

  return cards.sort((a, b) => {
    const ak = a.kbFile ? parseGenFileId(a.kbFile.id)?.kind || '' : a.artifactKind || '';
    const bk = b.kbFile ? parseGenFileId(b.kbFile.id)?.kind || '' : b.artifactKind || '';
    const aw = outputKindWeight(ak);
    const bw = outputKindWeight(bk);
    if (aw !== bw) return aw - bw;
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

watch(
  () => props.currentMaterial.id,
  () => {
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
});

defineExpose({
  refreshArtifacts,
  loadingArtifacts,
  clearSelectedGen,
});
</script>

<template>
  <div class="space-y-3">
    <div v-if="artifactsError" class="text-xs text-red-600 dark:text-red-300">
      {{ artifactsError }}
    </div>

    <div v-if="outputCards.length === 0" class="text-xs text-slate-500 dark:text-slate-400">
      暂无产物。生成大纲/PPT/教案后，这里会出现可下载的文件。
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="card in outputCards"
        :key="card.key"
        class="rounded-2xl border-2 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 py-3"
      >
        <div class="flex items-start gap-3">
          <input
            v-if="card.kbFile"
            type="checkbox"
            class="mt-1 w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500/40 disabled:opacity-40"
            :checked="selectedGenIdSet.has(card.kbFile.id)"
            :disabled="card.kbFile.status !== 'ready'"
            :aria-label="t('kb.picker.toggle')"
            @change="() => toggleGenSelected(card.kbFile!.id)"
          />
          <div v-else class="w-4 h-4 mt-1"></div>

          <div class="min-w-0 flex-1">
            <div class="text-sm font-extrabold text-slate-800 dark:text-slate-100 truncate" :title="card.title">
              {{ card.title }}
            </div>

            <div class="mt-1 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-2 min-w-0">
              <span class="font-mono truncate">{{ card.genTag }}</span>
              <span v-if="card.kbFile?.size" class="shrink-0">{{ formatSize(card.kbFile.size) }}</span>
              <span v-if="card.kbFile?.uploadedAt" class="shrink-0">{{ formatDateTime(card.kbFile.uploadedAt) }}</span>
            </div>

            <div class="mt-3 flex flex-wrap items-center gap-3">
              <button
                v-if="card.kbFile"
                type="button"
                class="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors disabled:opacity-40"
                :disabled="card.kbFile.status !== 'ready' || exportingKbFileId === card.kbFile.id"
                @click="handleExportKb(card.kbFile)"
              >
                <LucideIcon name="download" class="w-4 h-4" />
                下载md
              </button>
              <button
                v-else
                type="button"
                class="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-100 opacity-50 cursor-not-allowed"
                disabled
              >
                <LucideIcon name="download" class="w-4 h-4" />
                下载md
              </button>

              <button
                type="button"
                class="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors disabled:opacity-40"
                :disabled="!card.latestArtifact || downloadingArtifactId === card.latestArtifact.artifact_id"
                @click="card.latestArtifact ? handleDownloadArtifact(card.latestArtifact) : null"
              >
                <LucideIcon name="download" class="w-4 h-4" />
                下载源文件
              </button>
            </div>

            <div v-if="card.artifactKind && loadingArtifacts && !artifactsError && card.artifacts.length === 0" class="mt-3 space-y-2" role="status" aria-live="polite">
              <div
                v-for="i in 2"
                :key="`artifact-skel-${card.key}-${i}`"
                class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl border border-slate-200/60 dark:border-slate-800/60 bg-white/70 dark:bg-slate-900/30"
              >
                <div class="min-w-0 flex-1">
                  <Skeleton class="h-4 w-2/3" />
                  <Skeleton class="h-3 w-1/2 mt-2 opacity-80" />
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <Skeleton class="w-10 h-10 rounded-xl" />
                  <Skeleton class="w-10 h-10 rounded-xl" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
