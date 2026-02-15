<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import type { CourseGroup, KBFile } from '#root/types';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useI18n } from 'vue-i18n';
import { aiService } from '@/services/aiService';

interface Props {
  currentCourse: CourseGroup;
}

interface Emits {
  (e: 'updateCourse', updates: Partial<CourseGroup>): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const isDragging = ref(false);
const searchQuery = ref('');
const uploadTimers = new Map<string, number>();
const fileInputRef = ref<HTMLInputElement | null>(null);
const syncing = ref(false);

const files = computed(() => props.currentCourse.kbFiles || []);

const filteredFiles = computed(() => {
  const query = searchQuery.value.toLowerCase();
  return files.value.filter((f) => f.name.toLowerCase().includes(query));
});

const formatSize = (bytes: number) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const idx = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, idx);
  return `${value.toFixed(1)} ${units[idx]}`;
};

const updateFiles = (next: KBFile[]) => {
  emit('updateCourse', { kbFiles: next });
};

const mergeServerFiles = (serverFiles: Array<{ file_id: string; file_name: string; file_type: string; folder_id: number }>) => {
  const now = new Date();
  const pending = files.value.filter((f) => f.status === 'uploading' || f.status === 'processing');
  const mapped = serverFiles.map((it) => {
    const existing = files.value.find((f) => f.id === it.file_id);
    return {
      id: it.file_id,
      name: it.file_name || it.file_id,
      size: existing?.size || 0,
      type: it.file_type || 'unknown',
      status: 'ready' as const,
      uploadedAt: existing?.uploadedAt || now,
      folderId: typeof it.folder_id === 'number' ? it.folder_id : 0,
    } satisfies KBFile;
  });
  updateFiles([...pending, ...mapped]);
};

const refreshFromBackend = async () => {
  syncing.value = true;
  try {
    const list = await aiService.kbListFiles({ userId: props.currentCourse.id });
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
      userId: props.currentCourse.id,
      file,
      folderId: 0,
    });

    window.clearInterval(timer);
    uploadTimers.delete(localId);

    const next = files.value.map((f) =>
      f.id === localId
        ? {
            ...f,
            id: res.file_id,
            name: res.file_name || file.name,
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
    await aiService.kbDeleteFile({ userId: props.currentCourse.id, fileId: id });
    updateFiles(files.value.filter((f) => f.id !== id));
    toast.success(t('kb.action.delete'));
    await refreshFromBackend();
  } catch (e) {
    console.error(e);
    toast.error(t('kb.toast.delete_failed'));
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
  <div class="h-full flex flex-col gap-6">
    <input ref="fileInputRef" type="file" class="hidden" @change="handleFilePicked" />
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
      <div>
        <h2 class="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <LucideIcon name="database" :size="24" class="text-indigo-600" />
          {{ t('kb.title') }}
        </h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {{ t('nav.assistant') }} / {{ t('nav.kb') }} · {{ props.currentCourse.name }}
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
            class="w-full pl-9 pr-4 py-2 bg-slate-100 dark:bg-slate-800 border-transparent focus:bg-white dark:focus:bg-slate-900 border focus:border-indigo-500 rounded-lg text-sm outline-none transition-all"
          />
        </div>
      </div>
    </div>

    <div class="flex-1 flex flex-col md:flex-row gap-6 overflow-hidden">
      <div class="flex-1 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col overflow-hidden">
	        <div
	          class="m-4 p-8 border-2 border-dashed rounded-xl flex flex-col items-center justify-center transition-all duration-200 cursor-pointer"
	          :class="isDragging ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20' : 'border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 hover:bg-slate-50 dark:hover:bg-slate-800'"
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
        </div>

        <div class="grid grid-cols-12 gap-4 px-6 py-3 border-b border-slate-100 dark:border-slate-800 text-xs font-bold text-slate-400 uppercase tracking-wider bg-slate-50/50 dark:bg-slate-900/50">
          <div class="col-span-6">{{ t('kb.table.name') }}</div>
          <div class="col-span-2">{{ t('kb.table.size') }}</div>
          <div class="col-span-3">{{ t('kb.table.status') }}</div>
          <div class="col-span-1 text-right">{{ t('kb.table.action') }}</div>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar">
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
                  {{ file.type }}
                </div>
                <div class="min-w-0">
                  <div class="font-bold text-sm text-slate-800 dark:text-slate-200 truncate" :title="file.name">{{ file.name }}</div>
                  <div class="text-xs text-slate-400">{{ new Date(file.uploadedAt).toLocaleDateString() }}</div>
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
                    <div class="h-full bg-indigo-500 transition-all duration-300" :style="{ width: `${file.progress ?? 0}%` }"></div>
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
                <button
                  type="button"
                  class="text-slate-400 hover:text-red-500 transition-colors"
                  :disabled="file.status === 'uploading'"
                  @click="handleDelete(file.id)"
                >
                  <LucideIcon name="trash-2" :size="16" :title="t('kb.action.delete')" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="w-full md:w-72 flex-shrink-0 space-y-4">
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
</style>
