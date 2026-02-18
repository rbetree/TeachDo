<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { KBFile } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { toast } from '@/utils/toast';
import { aiService } from '@/services/aiService';
import { KB_USER_ID, useAppStore } from '@/stores/appStore';
import { getKbSource, getKbSourceUi } from '@/utils/kbSource';

type FolderFilter = 'all' | 'upload' | 'generated';

interface Props {
  open: boolean;
  files: KBFile[];
  selectedIds: string[];
  restoreFocusEl: HTMLElement | null;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'confirm', selectedIds: string[]): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();
const store = useAppStore();

const dialogRef = ref<HTMLElement | null>(null);
const searchQuery = ref('');
const folderFilter = ref<FolderFilter>('all');
const draftSelected = ref<Set<string>>(new Set());
const fileInputRef = ref<HTMLInputElement | null>(null);
const isDragging = ref(false);
const syncing = ref(false);
const uploadTimers = new Map<string, number>();

const close = () => emit('update:open', false);

const normalizeTimestampMs = (value: unknown): number | null => {
  const asNumber = typeof value === 'number' ? value : Number.NaN;
  if (!Number.isFinite(asNumber) || asNumber <= 0) return null;
  // 兼容秒级时间戳
  return asNumber < 1_000_000_000_000 ? Math.floor(asNumber * 1000) : Math.floor(asNumber);
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

const files = computed(() => (store.kbFiles || props.files || []));
const readyFiles = computed(() => files.value.filter((f) => f.status === 'ready'));

const filteredFiles = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  const filter = folderFilter.value;
  return readyFiles.value.filter((f) => {
    const source = getKbSource(typeof f.folderId === 'number' ? f.folderId : undefined);
    if (filter === 'upload' && source !== 'uploaded') return false;
    if (filter === 'generated' && source !== 'generated') return false;
    if (!query) return true;
    return (f.name || '').toLowerCase().includes(query) || (f.id || '').toLowerCase().includes(query);
  });
});

const selectedCount = computed(() => draftSelected.value.size);

const getSourceTagUi = (file: KBFile) => getKbSourceUi(getKbSource(typeof file.folderId === 'number' ? file.folderId : undefined));

const toggleId = (id: string) => {
  const next = new Set(draftSelected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  draftSelected.value = next;
};

const selectAllFiltered = () => {
  const next = new Set(draftSelected.value);
  for (const f of filteredFiles.value) next.add(f.id);
  draftSelected.value = next;
};

const clearAll = () => {
  draftSelected.value = new Set();
};

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
  if (!droppedFiles.length) return;
  const first = droppedFiles[0];
  if (first) void uploadFile(first);
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

const updateFileStatus = (fileId: string, status: KBFile['status'], progress?: number) => {
  const next = files.value.map((f) => (f.id === fileId ? { ...f, status, progress: progress ?? f.progress } : f));
  updateFiles(next);
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

    const selected = new Set(draftSelected.value);
    selected.add(res.file_id);
    draftSelected.value = selected;

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

const confirm = () => {
  emit('confirm', Array.from(draftSelected.value));
  close();
};

const onKeydown = (e: KeyboardEvent) => {
  if (e.key !== 'Escape') return;
  if (!props.open) return;
  close();
};

watch(
  () => props.open,
  async (open) => {
    if (open) {
      draftSelected.value = new Set((props.selectedIds || []).filter(Boolean));
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', onKeydown);
      void refreshFromBackend();
      await nextTick();
      dialogRef.value?.focus();
      return;
    }

    document.body.style.overflow = '';
    document.removeEventListener('keydown', onKeydown);
    await nextTick();
    const el = props.restoreFocusEl;
    if (el && document.contains(el)) el.focus();
  },
  { flush: 'post' },
);

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown);
  document.body.style.overflow = '';
  uploadTimers.forEach((timer) => window.clearInterval(timer));
  uploadTimers.clear();
});
</script>

<template>
  <Teleport to="body">
    <Transition name="td-modal">
      <div v-if="props.open" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <input ref="fileInputRef" type="file" class="hidden" @change="handleFilePicked" />
        <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" @click="close" />

        <div
          ref="dialogRef"
          class="relative w-full max-w-3xl rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl outline-none td-modal-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="kb-picker-title"
          tabindex="-1"
          @click.stop
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200/60 dark:border-slate-800/60">
            <div class="flex items-center gap-2 min-w-0">
              <LucideIcon name="file" :size="18" class="text-slate-500" />
              <h3 id="kb-picker-title" class="text-sm font-black text-slate-900 dark:text-white truncate">
                {{ t('kb.picker.title') }}
              </h3>
              <span class="text-xs font-bold text-slate-400">
                {{ t('kb.picker.selected', { count: selectedCount }) }}
              </span>
            </div>
            <button
              type="button"
              class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              :aria-label="t('common.close')"
              @click="close"
            >
              <LucideIcon name="x" :size="18" />
            </button>
          </div>

          <div class="px-5 py-4 space-y-3 max-h-[min(70vh,720px)] overflow-y-auto custom-scrollbar">
            <button
              type="button"
              class="w-full p-4 border-2 border-dashed rounded-2xl text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 dark:focus-visible:ring-offset-slate-900"
              :class="isDragging
                ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                : 'border-indigo-300/80 dark:border-indigo-700/70 bg-indigo-50/50 dark:bg-indigo-900/10 hover:bg-indigo-50 dark:hover:bg-indigo-900/20'"
              @click="openFilePicker"
              @dragover.prevent="handleDragOver"
              @dragleave.prevent="handleDragLeave"
              @drop="handleDrop"
            >
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl border border-indigo-200 dark:border-indigo-800/50 bg-white/80 dark:bg-slate-900/40 flex items-center justify-center flex-shrink-0">
                  <LucideIcon name="upload-cloud" :size="18" :class="isDragging ? 'text-indigo-600 dark:text-indigo-300' : 'text-indigo-500 dark:text-indigo-400'" />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-bold text-slate-800 dark:text-slate-100 truncate">{{ t('kb.drop.title') }}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ t('kb.drop.desc') }}</p>
                </div>
                <span class="text-xs font-bold text-indigo-700 dark:text-indigo-200 px-3 py-1.5 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-700/50">
                  {{ t('kb.action.upload') }}
                </span>
              </div>
            </button>

            <div class="flex flex-col md:flex-row md:items-center gap-3">
              <div class="relative flex-1">
                <LucideIcon name="search" :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  v-model="searchQuery"
                  type="text"
                  :placeholder="t('kb.picker.search')"
                  class="w-full pl-9 pr-3 py-2 bg-white/70 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-indigo-400 dark:focus:border-indigo-700 rounded-xl text-sm outline-none transition-all"
                />
              </div>

              <div class="flex items-center flex-wrap gap-2">
                <div
                  class="inline-flex items-center p-1 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30"
                  role="group"
                  :aria-label="t('kb.picker.folder')"
                >
                  <button
                    type="button"
                    class="px-3 py-2 rounded-lg text-sm font-bold transition-colors"
                    :class="folderFilter === 'all'
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800'"
                    :aria-pressed="folderFilter === 'all'"
                    @click="folderFilter = 'all'"
                  >
                    {{ t('kb.picker.filter.all') }}
                  </button>
                  <button
                    type="button"
                    class="px-3 py-2 rounded-lg text-sm font-bold transition-colors"
                    :class="folderFilter === 'upload'
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800'"
                    :aria-pressed="folderFilter === 'upload'"
                    @click="folderFilter = 'upload'"
                  >
                    {{ t('kb.source.uploaded') }}
                  </button>
                  <button
                    type="button"
                    class="px-3 py-2 rounded-lg text-sm font-bold transition-colors"
                    :class="folderFilter === 'generated'
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800'"
                    :aria-pressed="folderFilter === 'generated'"
                    @click="folderFilter = 'generated'"
                  >
                    {{ t('kb.source.generated') }}
                  </button>
                </div>

                <button
                  type="button"
                  class="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 text-sm font-bold text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  @click="selectAllFiltered"
                >
                  {{ t('kb.picker.select_all') }}
                </button>

                <button
                  type="button"
                  class="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 text-sm font-bold text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  @click="clearAll"
                >
                  {{ t('kb.picker.clear') }}
                </button>

                <button
                  type="button"
                  class="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 text-sm font-bold text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors inline-flex items-center gap-1.5"
                  :aria-label="t('kb.action.refresh')"
                  :title="t('kb.action.refresh')"
                  @click="refreshFromBackend"
                >
                  <LucideIcon name="refresh-cw" :size="14" :class="syncing ? 'animate-spin' : ''" />
                  <span>{{ t('kb.action.refresh') }}</span>
                </button>
              </div>
            </div>

            <div class="rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div class="grid grid-cols-12 gap-3 px-4 py-2 text-xs font-bold text-slate-400 uppercase tracking-wider bg-slate-50/60 dark:bg-slate-950/30">
                <div class="col-span-7">{{ t('kb.table.name') }}</div>
                <div class="col-span-3">{{ t('kb.picker.folder') }}</div>
                <div class="col-span-2 text-right">{{ t('kb.picker.action') }}</div>
              </div>

              <div class="max-h-[420px] overflow-y-auto custom-scrollbar divide-y divide-slate-100 dark:divide-slate-800">
                <div v-if="filteredFiles.length === 0" class="px-6 py-10 text-center text-sm text-slate-400">
                  {{ t('kb.picker.empty') }}
                </div>
                <button
                  v-for="file in filteredFiles"
                  :key="file.id"
                  type="button"
                  class="w-full grid grid-cols-12 gap-3 px-4 py-3 items-center text-left hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                  @click="toggleId(file.id)"
                >
                  <div class="col-span-7 min-w-0">
                    <div class="flex items-center gap-3 min-w-0">
                      <div class="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-900/25 text-indigo-600 dark:text-indigo-300 flex items-center justify-center border border-indigo-100 dark:border-indigo-800/40 flex-shrink-0">
                        <LucideIcon name="file" :size="16" />
                      </div>
                      <div class="min-w-0">
                        <div class="text-sm font-bold text-slate-800 dark:text-slate-200 truncate" :title="file.name || file.id">
                          {{ file.name || file.id }}
                        </div>
                        <div class="text-[11px] text-slate-400 truncate">{{ file.id }}</div>
                      </div>
                    </div>
                  </div>
                  <div class="col-span-3">
                    <span
                      :class="getSourceTagUi(file).className"
                      :title="t(getSourceTagUi(file).i18nTitleKey)"
                      :aria-label="t(getSourceTagUi(file).i18nTitleKey)"
                    >
                      <LucideIcon :name="getSourceTagUi(file).icon" :size="12" />
                      {{ t(getSourceTagUi(file).i18nKey) }}
                    </span>
                  </div>
                  <div class="col-span-2 flex items-center justify-end">
                    <input
                      type="checkbox"
                      class="h-4 w-4 accent-indigo-600"
                      :checked="draftSelected.has(file.id)"
                      :aria-label="t('kb.picker.toggle')"
                      @click.stop="toggleId(file.id)"
                    />
                  </div>
                </button>
              </div>
            </div>
          </div>

          <div class="px-5 py-4 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center justify-between gap-2 bg-slate-50/40 dark:bg-slate-950/20">
            <div class="text-xs text-slate-500 dark:text-slate-400">
              {{ t('kb.picker.ready_only') }}
            </div>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 font-bold text-sm hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                @click="close"
              >
                {{ t('sidebar.cancel') }}
              </button>
              <button
                type="button"
                class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md transition-colors"
                @click="confirm"
              >
                {{ t('kb.picker.confirm') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.5);
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(71, 85, 105, 0.5);
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(71, 85, 105, 0.7);
}

.td-modal-enter-active,
.td-modal-leave-active {
  transition: opacity 150ms ease;
}

.td-modal-enter-from,
.td-modal-leave-to {
  opacity: 0;
}

.td-modal-enter-active .td-modal-panel,
.td-modal-leave-active .td-modal-panel {
  transition: transform 150ms ease, opacity 150ms ease;
}

.td-modal-enter-from .td-modal-panel,
.td-modal-leave-to .td-modal-panel {
  opacity: 0;
  transform: translateY(6px) scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .td-modal-enter-active,
  .td-modal-leave-active,
  .td-modal-enter-active .td-modal-panel,
  .td-modal-leave-active .td-modal-panel {
    transition: none;
  }
}
</style>
