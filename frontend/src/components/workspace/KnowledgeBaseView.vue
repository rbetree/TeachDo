<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import type { KBFile, TeachingMaterial } from '#root/types';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useI18n } from 'vue-i18n';
import { aiService } from '@/services/aiService';
import { KB_USER_ID, useAppStore } from '@/stores/appStore';
import { getKbSource, getKbSourceUi } from '@/utils/kbSource';

type KnowledgeBaseViewVariant = 'page' | 'panel';
type KnowledgeBaseSourceFilter = 'all' | 'uploaded';

interface Props {
  variant?: KnowledgeBaseViewVariant;
  currentMaterial?: TeachingMaterial | null;
  sourceFilter?: KnowledgeBaseSourceFilter;
}

const props = defineProps<Props>();
const { t } = useI18n();
const store = useAppStore();

const isPanel = computed(() => props.variant === 'panel');
const sourceFilter = computed<KnowledgeBaseSourceFilter>(() => props.sourceFilter ?? 'all');
const activeMaterial = computed(() => props.currentMaterial ?? store.currentMaterial);

const isDragging = ref(false);
const searchQuery = ref('');
const uploadTimers = new Map<string, number>();
const fileInputRef = ref<HTMLInputElement | null>(null);
const syncing = ref(false);
const exportingFileId = ref<string | null>(null);

const files = computed(() => {
  const all = store.kbFiles || [];
  if (sourceFilter.value === 'uploaded') {
    return all.filter((f) => (typeof f.folderId === 'number' ? f.folderId : 0) === 0);
  }
  return all;
});

const filteredFiles = computed(() => {
  const query = searchQuery.value.toLowerCase();
  return files.value.filter((f) => f.name.toLowerCase().includes(query));
});

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

const selectedKbFileIdSet = computed(() => {
  const raw = normalizeStringArray(activeMaterial.value?.kbFileIds);
  if (sourceFilter.value === 'uploaded') {
    return new Set(raw.filter((id) => !isGenFileId(id)));
  }
  return new Set(raw);
});
const selectedKbFileCount = computed(() => selectedKbFileIdSet.value.size);

const isKbFileSelected = (fileId: string) => selectedKbFileIdSet.value.has(fileId);

const persistKbFileIds = (nextIds: string[]) => {
  const material = activeMaterial.value;
  if (!material) return;
  store.patchMaterial(material.id, { kbFileIds: normalizeStringArray(nextIds) });
};

const toggleKbFileSelected = (fileId: string) => {
  const material = activeMaterial.value;
  if (!material) return;

  const current = normalizeStringArray(material.kbFileIds);
  const next = new Set(current);
  if (next.has(fileId)) next.delete(fileId);
  else next.add(fileId);
  persistKbFileIds(Array.from(next));
};

const clearSelectedKbFiles = () => {
  const material = activeMaterial.value;
  if (!material) return;
  const current = normalizeStringArray(material.kbFileIds);
  if (sourceFilter.value === 'uploaded') {
    // 仅清空“参考资料”（非 gen:），避免影响右侧产物的全文注入选择
    persistKbFileIds(current.filter((id) => isGenFileId(id)));
    return;
  }
  persistKbFileIds([]);
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

const formatSize = (bytes: number) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const idx = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, idx);
  return `${value.toFixed(1)} ${units[idx]}`;
};

const normalizeExt = (value: unknown) => String(value ?? '')
  .trim()
  .toLowerCase()
  .replace(/^\./, '');

const getNameExt = (name: string) => {
  const trimmed = (name || '').trim();
  const idx = trimmed.lastIndexOf('.');
  if (idx <= 0 || idx >= trimmed.length - 1) return '';
  return normalizeExt(trimmed.slice(idx + 1));
};

const getDisplayType = (file: KBFile) => normalizeExt(file.type) || getNameExt(file.name) || 'unknown';

	const getDisplayName = (file: KBFile) => {
	  const name = (file.name || '').trim() || file.id;
	  if (getNameExt(name)) return name;
	  const ext = getDisplayType(file);
	  if (!ext || ext === 'unknown') return name;
	  return `${name}.${ext}`;
	};

	const normalizeTimestampMs = (value: unknown): number | null => {
	  const asNumber = typeof value === 'number' ? value : Number.NaN;
	  if (!Number.isFinite(asNumber) || asNumber <= 0) return null;
	  // 兼容秒级时间戳
	  return asNumber < 1_000_000_000_000 ? Math.floor(asNumber * 1000) : Math.floor(asNumber);
	};

	const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
	  year: 'numeric',
	  month: '2-digit',
	  day: '2-digit',
	  hour: '2-digit',
	  minute: '2-digit',
	});

	const formatDateTime = (value: Date | unknown) => {
	  const date = value instanceof Date ? value : new Date(String(value));
	  if (Number.isNaN(date.getTime())) return '';
	  return dateTimeFormatter.format(date);
	};

	const normalizeSourceType = (value: unknown): KBFile['sourceType'] | null => {
	  const s = String(value ?? '').trim().toLowerCase();
	  if (s === 'upload' || s === 'material') return s;
	  return null;
	};

	const parseMaterialIdFromGenFileId = (fileId: string): string | null => {
	  if (!fileId.startsWith('gen:')) return null;
	  const parts = fileId.split(':');
	  if (parts.length < 4) return null;
	  return parts[2] || null;
	};

	const getSourceTagUi = (file: KBFile) => getKbSourceUi(getKbSource(file.folderId));

const updateFiles = (next: KBFile[]) => {
  store.setKbFiles(next);
};

	const mergeServerFiles = (
	  serverFiles: Array<{
	    file_id: string;
	    file_name: string;
	    file_type: string;
	    file_size?: number;
	    folder_id: number;
	    created_at?: number;
	    source_type?: 'upload' | 'material';
	    source_material_id?: string;
	    source_material_title?: string;
	  }>,
	) => {
	  const now = new Date();
	  const pending = files.value.filter((f) => f.status === 'uploading' || f.status === 'processing');
	  const mapped = serverFiles.map((it) => {
	    const existing = files.value.find((f) => f.id === it.file_id);
	    const createdAtMs = normalizeTimestampMs(it.created_at);
	    const inferredSourceType =
	      normalizeSourceType(it.source_type) ||
	      (it.file_id.startsWith('upload:') || it.folder_id === 0 ? 'upload' : it.folder_id === 1 || it.file_id.startsWith('gen:') ? 'material' : null);
	    const inferredMaterialId =
	      (typeof it.source_material_id === 'string' && it.source_material_id.trim() ? it.source_material_id.trim() : null) ||
	      (inferredSourceType === 'material' ? parseMaterialIdFromGenFileId(it.file_id) : null);
	    return {
	      id: it.file_id,
	      name: it.file_name || it.file_id,
	      size: typeof it.file_size === 'number' ? it.file_size : existing?.size || 0,
	      type: it.file_type || 'unknown',
	      status: 'ready' as const,
	      uploadedAt: createdAtMs ? new Date(createdAtMs) : existing?.uploadedAt || now,
	      folderId: typeof it.folder_id === 'number' ? it.folder_id : 0,
	      sourceType: inferredSourceType || existing?.sourceType,
	      sourceMaterialId: inferredMaterialId || existing?.sourceMaterialId,
	      sourceMaterialTitle:
	        (typeof it.source_material_title === 'string' && it.source_material_title.trim() ? it.source_material_title.trim() : null) ||
	        existing?.sourceMaterialTitle,
	    } satisfies KBFile;
	  });
	  updateFiles([...pending, ...mapped]);
	};

const refreshFromBackend = async () => {
  syncing.value = true;
  try {
    const list = await aiService.kbListFiles({ userId: KB_USER_ID });
    mergeServerFiles(list);
  } catch (e) {
    console.warn('知识库列表同步失败（已忽略）', e);
  } finally {
    syncing.value = false;
  }
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
    if (first) void uploadFile(first);
  }
};

const openFilePicker = () => {
  fileInputRef.value?.click();
};

const handleFilePicked = (e: Event) => {
  const input = e.target as HTMLInputElement | null;
  const file = input?.files?.[0];
  if (input) input.value = '';
  if (!file) return;
  void uploadFile(file);
};

const uploadFile = async (file: File) => {
  const localId = `temp:${Date.now()}`;
	  const newFile: KBFile = {
	    id: localId,
	    name: file.name,
	    size: file.size,
	    type: file.name.split('.').pop() || 'unknown',
	    status: 'uploading',
	    uploadedAt: new Date(),
	    progress: 0,
	    folderId: 0,
	    sourceType: 'upload',
	  };

  updateFiles([...files.value, newFile]);

  let progress = 0;
  const timer = window.setInterval(() => {
    progress += 8;
    if (progress > 90) progress = 90;
    updateFileStatus(localId, 'uploading', progress);
  }, 250);
  uploadTimers.set(localId, timer);

  try {
    updateFileStatus(localId, 'processing', 95);

    const res = await aiService.kbUpload({
      userId: KB_USER_ID,
      file,
      folderId: 0,
    });

    window.clearInterval(timer);
    uploadTimers.delete(localId);

    const next: KBFile[] = files.value.map((f) =>
      f.id === localId
        ? {
            ...f,
            id: res.file_id,
            name: res.file_name || file.name,
            size: typeof res.file_size === 'number' ? res.file_size : f.size,
            type: res.file_type || f.type,
            status: 'ready',
            progress: 100,
            folderId: res.folder_id ?? 0,
          }
        : f,
    );
    updateFiles(next);
    toast.success(t('kb.toast.uploaded'));

    await refreshFromBackend();
  } catch (e) {
    window.clearInterval(timer);
    uploadTimers.delete(localId);
    updateFileStatus(localId, 'error');
    console.error(e);
    toast.error(t('kb.toast.upload_failed'));
  }
};

const updateFileStatus = (fileId: string, status: KBFile['status'], progress?: number) => {
  const next = files.value.map((f) => (f.id === fileId ? { ...f, status, progress: progress ?? f.progress } : f));
  updateFiles(next);
};

const handleDelete = async (id: string) => {
  if (!confirm(t('kb.confirm.delete'))) return;
  const target = files.value.find((f) => f.id === id);
  if (!target) return;

  // 本地临时条目，直接删除即可
  if (id.startsWith('temp:') || target.status === 'error') {
    const timer = uploadTimers.get(id);
    if (timer) window.clearInterval(timer);
    uploadTimers.delete(id);
    updateFiles(files.value.filter((f) => f.id !== id));
    toast.success(t('kb.action.delete'));
    return;
  }

  try {
    await aiService.kbDeleteFile({ userId: KB_USER_ID, fileId: id });
    updateFiles(files.value.filter((f) => f.id !== id));
    purgeKbFileReferences(id);
    toast.success(t('kb.action.delete'));
    await refreshFromBackend();
  } catch (e) {
    console.error(e);
    toast.error(t('kb.toast.delete_failed'));
  }
};

const handleExport = async (file: KBFile) => {
  if (file.status !== 'ready') return;
  exportingFileId.value = file.id;
  try {
    const { blob, filename } = await aiService.kbExportFile({ userId: KB_USER_ID, fileId: file.id });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || getDisplayName(file) || 'export.md';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success(t('kb.toast.exported'));
  } catch (e) {
    console.error(e);
    toast.error(t('kb.toast.export_failed'));
  } finally {
    if (exportingFileId.value === file.id) exportingFileId.value = null;
  }
};

onMounted(() => {
  void refreshFromBackend();
});

onBeforeUnmount(() => {
  uploadTimers.forEach((timer) => window.clearInterval(timer));
  uploadTimers.clear();
});
</script>

<template>
  <div :class="['h-full flex flex-col', isPanel ? 'gap-2' : 'gap-6']">
    <input ref="fileInputRef" type="file" class="hidden" @change="handleFilePicked" />

    <!-- Panel Variant: 紧凑侧栏布局 -->
    <div
      v-if="isPanel"
      class="px-4 py-4 border-b border-slate-200/60 dark:border-slate-800/60 bg-white/50 dark:bg-slate-900/30 backdrop-blur"
    >
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <div class="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-900/25 text-indigo-600 dark:text-indigo-300 flex items-center justify-center border border-indigo-100 dark:border-indigo-800/40 flex-shrink-0">
            <LucideIcon name="database" :size="18" />
          </div>
          <div class="min-w-0">
            <div class="text-sm font-extrabold text-slate-800 dark:text-slate-100 truncate">
              {{ sourceFilter === 'uploaded' ? t('workspace.references.title') : t('kb.title') }}
            </div>
            <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              <template v-if="sourceFilter === 'uploaded'">
                {{ t('workspace.references.subtitle') }} · {{ t('kb.stats.total') }} {{ files.length }}
              </template>
              <template v-else>
                {{ t('kb.global') }} · {{ t('kb.stats.total') }} {{ files.length }}
              </template>
            </div>
          </div>
        </div>

        <button
          type="button"
          class="w-10 h-10 inline-flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-900 transition-colors"
          :aria-label="t('kb.action.refresh')"
          :title="t('kb.action.refresh')"
          @click="refreshFromBackend"
        >
          <LucideIcon name="refresh-cw" :size="18" :class="syncing ? 'animate-spin' : ''" />
        </button>
      </div>

      <div class="mt-4">
        <div v-if="activeMaterial" class="flex items-center justify-between gap-2 mb-3">
          <div class="text-[11px] font-bold text-slate-500 dark:text-slate-400">
            {{ t('kb.picker.selected', { count: selectedKbFileCount }) }}
          </div>
          <button
            type="button"
            class="px-2 py-1 rounded-lg text-[11px] font-bold text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
            :disabled="selectedKbFileCount === 0"
            @click="clearSelectedKbFiles"
          >
            {{ t('kb.picker.clear') }}
          </button>
        </div>

	        <div class="relative">
	          <LucideIcon name="search" :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
	          <input
	            v-model="searchQuery"
	            type="text"
	            :placeholder="t('kb.search')"
              :aria-label="t('kb.search')"
              name="kb-search"
              autocomplete="off"
	            class="w-full pl-9 pr-3 py-2 bg-white/70 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-indigo-400 dark:focus:border-indigo-700 rounded-xl text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-indigo-500/30 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 dark:focus-visible:ring-offset-slate-900"
	          />
	        </div>
	      </div>
    </div>

    <!-- Page Variant: 原页面布局 -->
    <div
      v-else
      class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm"
    >
      <div>
        <h2 class="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <LucideIcon name="database" :size="24" class="text-indigo-600" />
          {{ t('kb.title') }}
        </h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {{ t('nav.assistant') }} / {{ t('nav.kb') }} · {{ t('kb.global') }}
        </p>
      </div>
      <div class="flex items-center gap-3 w-full md:w-auto">
        <div v-if="syncing" class="hidden md:flex items-center gap-2 text-xs font-bold text-slate-400">
          <LucideIcon name="loader-2" :size="14" class="animate-spin" /> {{ t('kb.status.syncing') }}
        </div>
        <div class="relative flex-1 md:w-64">
          <LucideIcon name="search" :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
	          <input
	            v-model="searchQuery"
	            type="text"
	            :placeholder="t('kb.search')"
              :aria-label="t('kb.search')"
              name="kb-search"
              autocomplete="off"
	            class="w-full pl-9 pr-4 py-2 bg-slate-100 dark:bg-slate-800 border-transparent focus:bg-white dark:focus:bg-slate-900 border focus:border-indigo-500 rounded-lg text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-indigo-500/30 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900"
	          />
	        </div>
	      </div>
    </div>

    <div :class="['flex-1 flex overflow-hidden', isPanel ? 'flex-col gap-0' : 'flex-col md:flex-row gap-6']">
      <div
        :class="[
          'flex-1 flex flex-col overflow-hidden',
          isPanel ? '' : 'bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm',
        ]"
      >
        <!-- Panel Variant：紧凑上传区 + 列表 -->
        <template v-if="isPanel">
          <button
            type="button"
            class="mx-4 mt-3 mb-3 p-4 border-2 border-dashed rounded-2xl flex items-center gap-3 transition-colors text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 dark:focus-visible:ring-offset-slate-900"
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
            <div v-if="filteredFiles.length === 0" class="flex flex-col items-center justify-center py-10 text-slate-400">
              <LucideIcon name="file" :size="32" class="mb-2 opacity-40" />
              <p class="text-sm">{{ t('kb.empty') }}</p>
            </div>

			            <div v-else class="px-4 pb-4 space-y-1">
				              <div
				                v-for="file in filteredFiles"
				                :key="file.id"
				                class="group rounded-2xl border shadow-sm transition-[background-color,border-color,box-shadow] duration-200 px-3 pt-2 pb-1"
			                    :class="activeMaterial && isKbFileSelected(file.id)
                            ? 'border-indigo-300/80 bg-indigo-50/90 dark:border-indigo-700/60 dark:bg-indigo-900/20 ring-2 ring-indigo-500/30 ring-inset'
                            : 'border-slate-200/70 dark:border-slate-800/60 bg-indigo-50/60 dark:bg-indigo-900/10 hover:bg-indigo-50/80 dark:hover:bg-indigo-900/20 hover:border-indigo-200 dark:hover:border-indigo-700/40'"
				              >
					                <div class="flex items-start justify-between gap-2">
                        <label
                          v-if="activeMaterial"
                          :for="`kb-select-${file.id}`"
                          class="min-w-0 flex-1 cursor-pointer"
                        >
                          <div class="font-bold text-[12px] leading-tight text-slate-800 dark:text-slate-100 truncate" :title="getDisplayName(file)">
                            {{ getDisplayName(file) }}
                          </div>
                          <div class="mt-0.5 flex items-center gap-1 text-[10px] leading-tight text-slate-500 dark:text-slate-400 min-w-0">
                            <span class="font-mono shrink-0">{{ formatSize(file.size || 0) }}</span>
                            <span class="text-slate-300 dark:text-slate-700 shrink-0">•</span>
                            <span class="shrink-0">{{ formatDateTime(file.uploadedAt) }}</span>
                          </div>
                        </label>

                        <div v-else class="min-w-0 flex-1">
                          <div class="font-bold text-[12px] leading-tight text-slate-800 dark:text-slate-100 truncate" :title="getDisplayName(file)">
                            {{ getDisplayName(file) }}
                          </div>
                          <div class="mt-0.5 flex items-center gap-1 text-[10px] leading-tight text-slate-500 dark:text-slate-400 min-w-0">
                            <span class="font-mono shrink-0">{{ formatSize(file.size || 0) }}</span>
                            <span class="text-slate-300 dark:text-slate-700 shrink-0">•</span>
                            <span class="shrink-0">{{ formatDateTime(file.uploadedAt) }}</span>
                          </div>
                        </div>

                        <input
                          v-if="activeMaterial"
                          :id="`kb-select-${file.id}`"
                          type="checkbox"
                          class="mt-0.5 h-4 w-4 accent-indigo-600 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 dark:focus-visible:ring-offset-slate-900"
                          :checked="isKbFileSelected(file.id)"
                          :disabled="file.status !== 'ready'"
                          :aria-label="t('kb.picker.toggle')"
                          @change="toggleKbFileSelected(file.id)"
                        />
					                </div>

				                      <div class="mt-0.5 flex items-center justify-between gap-2">
				                        <div class="flex flex-wrap items-center gap-1 min-w-0 flex-1">
				                          <span
				                            v-if="file.status === 'ready'"
				                            class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] leading-none font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/25 dark:text-emerald-200"
				                          >
				                            <LucideIcon name="check-circle" :size="11" /> {{ t('kb.status.ready') }}
				                          </span>
				                          <span
				                            v-else-if="file.status === 'processing'"
				                            class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] leading-none font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/25 dark:text-amber-200"
				                          >
				                            <LucideIcon name="loader-2" :size="11" class="animate-spin" /> {{ t('kb.status.processing') }}
				                          </span>

				                          <span
				                            v-else-if="file.status === 'uploading'"
				                            class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] leading-none font-bold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/25 dark:text-indigo-200"
				                          >
				                            <LucideIcon name="loader-2" :size="11" class="animate-spin" /> {{ t('kb.status.uploading') }}
				                          </span>
				                          <span
				                            v-else-if="file.status === 'error'"
				                            class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] leading-none font-bold bg-red-100 text-red-700 dark:bg-red-900/25 dark:text-red-300"
				                          >
				                            <LucideIcon name="alert-circle" :size="11" /> {{ t('kb.status.error') }}
				                          </span>

                          <span
                            :class="getSourceTagUi(file).className"
                            :title="t(getSourceTagUi(file).i18nTitleKey)"
                            :aria-label="t(getSourceTagUi(file).i18nTitleKey)"
                            class="shrink-0"
                          >
                            <LucideIcon :name="getSourceTagUi(file).icon" :size="12" />
                            {{ t(getSourceTagUi(file).i18nKey) }}
                          </span>
				                        </div>

				                        <div class="flex items-center gap-1 shrink-0">
				                          <button
				                            type="button"
				                            class="w-9 h-9 inline-flex items-center justify-center rounded-xl text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
				                            :aria-label="t('kb.action.export')"
				                            :title="t('kb.action.export')"
				                            :disabled="file.status !== 'ready' || exportingFileId === file.id"
				                            @click="handleExport(file)"
				                          >
				                            <LucideIcon name="download" :size="16" />
				                          </button>
				                          <button
				                            type="button"
				                            class="w-9 h-9 inline-flex items-center justify-center rounded-xl text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/40"
				                            :aria-label="t('kb.action.delete')"
				                            :title="t('kb.action.delete')"
				                            :disabled="file.status === 'uploading'"
				                            @click="handleDelete(file.id)"
				                          >
				                            <LucideIcon name="trash-2" :size="16" />
				                          </button>
				                        </div>
				                      </div>

				                      <div v-if="file.status === 'uploading'" class="mt-0.5 space-y-1">
				                        <div class="flex justify-between text-[10px] font-bold text-indigo-600 dark:text-indigo-300">
				                          <span>{{ t('kb.status.uploading') }}</span>
				                          <span>{{ file.progress ?? 0 }}%</span>
				                        </div>
				                        <div class="h-1 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
				                          <div class="h-full bg-indigo-500 transition-[width] duration-300" :style="{ width: `${file.progress ?? 0}%` }"></div>
				                        </div>
				                      </div>
				              </div>
            </div>
          </div>
        </template>

        <!-- Page Variant：原表格布局 -->
        <template v-else>
	          <button
	            type="button"
	            class="m-4 p-8 border-2 border-dashed rounded-xl flex flex-col items-center justify-center transition-colors duration-200 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 dark:focus-visible:ring-offset-slate-900"
	            :class="isDragging
	              ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
	              : 'border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 hover:bg-slate-50 dark:hover:bg-slate-800'"
	            @click="openFilePicker"
	            @dragover.prevent="handleDragOver"
	            @dragleave.prevent="handleDragLeave"
	            @drop="handleDrop"
	          >
            <div class="w-12 h-12 bg-white dark:bg-slate-800 rounded-full flex items-center justify-center shadow-sm mb-3">
              <LucideIcon name="upload-cloud" :size="24" :class="isDragging ? 'text-indigo-600' : 'text-slate-400'" />
            </div>
            <div class="text-center">
              <p class="text-sm font-bold text-slate-700 dark:text-slate-200">
                {{ isDragging ? t('kb.drop.title') : t('kb.drop.title') }}
              </p>
	              <p class="text-xs text-slate-500 mt-1">{{ t('kb.drop.desc') }}</p>
	            </div>
	          </button>

          <div class="grid grid-cols-12 gap-4 px-6 py-3 border-b border-slate-100 dark:border-slate-800 text-xs font-bold text-slate-400 uppercase tracking-wider bg-slate-50/50 dark:bg-slate-900/50">
            <div class="col-span-6">{{ t('kb.table.name') }}</div>
            <div class="col-span-2">{{ t('kb.table.size') }}</div>
            <div class="col-span-3">{{ t('kb.table.status') }}</div>
            <div class="col-span-1 text-right">{{ t('kb.table.action') }}</div>
          </div>

          <div class="flex-1 overflow-y-auto overscroll-contain custom-scrollbar">
            <div v-if="filteredFiles.length === 0" class="flex flex-col items-center justify-center h-48 text-slate-400">
              <LucideIcon name="file" :size="40" class="mb-2 opacity-40" />
              <p class="text-sm">{{ t('kb.empty') }}</p>
            </div>
            <div v-else class="divide-y divide-slate-100 dark:divide-slate-800">
              <div
                v-for="file in filteredFiles"
                :key="file.id"
                class="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group"
              >
	                <div class="col-span-6 flex items-center gap-3 overflow-hidden">
	                  <div class="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400 flex-shrink-0 font-bold text-xs uppercase">
	                    {{ getDisplayType(file) }}
	                  </div>
	                  <div class="min-w-0">
		                    <div class="flex items-center gap-2 min-w-0">
                          <div class="font-bold text-sm text-slate-800 dark:text-slate-200 truncate flex-1 min-w-0" :title="getDisplayName(file)">{{ getDisplayName(file) }}</div>
                          <span
                            :class="getSourceTagUi(file).className"
                            :title="t(getSourceTagUi(file).i18nTitleKey)"
                            :aria-label="t(getSourceTagUi(file).i18nTitleKey)"
                            class="flex-shrink-0"
                          >
                            <LucideIcon :name="getSourceTagUi(file).icon" :size="12" />
                            {{ t(getSourceTagUi(file).i18nKey) }}
                          </span>
                        </div>
			                    <div class="text-xs text-slate-400">{{ formatDateTime(file.uploadedAt) }}</div>
		                  </div>
		                </div>
                <div class="col-span-2 text-sm text-slate-500 font-mono">
                  {{ formatSize(file.size || 0) }}
                </div>
                <div class="col-span-3">
                  <span
                    v-if="file.status === 'ready'"
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                  >
                    <LucideIcon name="check-circle" :size="14" /> {{ t('kb.status.ready') }}
                  </span>
                  <span
                    v-else-if="file.status === 'processing'"
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 animate-pulse"
                  >
                    <LucideIcon name="loader-2" :size="14" class="animate-spin" /> {{ t('kb.status.processing') }}
                  </span>
                  <div v-else-if="file.status === 'uploading'" class="w-full max-w-[140px] space-y-1">
                    <div class="flex justify-between text-[10px] font-bold text-indigo-600">
                      <span>{{ t('kb.status.uploading') }}</span>
                      <span>{{ file.progress ?? 0 }}%</span>
                    </div>
	                    <div class="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
	                      <div class="h-full bg-indigo-500 transition-[width] duration-300" :style="{ width: `${file.progress ?? 0}%` }"></div>
	                    </div>
	                  </div>
                  <span
                    v-else
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                  >
                    <LucideIcon name="alert-circle" :size="14" /> {{ t('kb.status.error') }}
                  </span>
	                </div>
	                <div class="col-span-1 text-right">
		                  <div class="inline-flex items-center justify-end gap-2">
		                    <button
		                      type="button"
		                      class="w-11 h-11 inline-flex items-center justify-center rounded-md text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
		                      :aria-label="t('kb.action.export')"
		                      :title="t('kb.action.export')"
		                      :disabled="file.status !== 'ready' || exportingFileId === file.id"
		                      @click="handleExport(file)"
		                    >
	                      <LucideIcon name="download" :size="16" />
	                    </button>
		                    <button
		                      type="button"
		                      class="w-11 h-11 inline-flex items-center justify-center rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/40"
		                      :aria-label="t('kb.action.delete')"
		                      :title="t('kb.action.delete')"
		                      :disabled="file.status === 'uploading'"
		                      @click="handleDelete(file.id)"
		                    >
	                      <LucideIcon name="trash-2" :size="16" />
	                    </button>
	                  </div>
	                </div>
	              </div>
	            </div>
	          </div>
        </template>
      </div>

      <div v-if="!isPanel" class="w-full md:w-72 flex-shrink-0 space-y-4">
        <div class="bg-indigo-50 dark:bg-indigo-900/20 p-5 rounded-2xl border border-indigo-100 dark:border-indigo-800/50">
          <h3 class="font-bold text-indigo-900 dark:text-indigo-100 mb-2">{{ t('kb.rag.title') }}</h3>
          <p class="text-xs text-indigo-700 dark:text-indigo-300 leading-relaxed">
            {{ t('kb.rag.desc') }}
          </p>
        </div>

        <div class="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800">
          <h3 class="font-bold text-slate-800 dark:text-white mb-3 text-sm">{{ t('kb.stats.title') }}</h3>
          <div class="space-y-3">
            <div class="flex justify-between text-sm">
              <span class="text-slate-500">{{ t('kb.stats.total') }}</span>
              <span class="font-bold text-slate-800 dark:text-white">{{ files.length }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-slate-500">{{ t('kb.stats.storage') }}</span>
              <span class="font-bold text-slate-800 dark:text-white">
                {{ formatSize(files.reduce((acc, f) => acc + (f.size || 0), 0)) }}
              </span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-slate-500">{{ t('kb.stats.last') }}</span>
              <span class="font-bold text-slate-800 dark:text-white">{{ t('kb.stats.just_now') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
