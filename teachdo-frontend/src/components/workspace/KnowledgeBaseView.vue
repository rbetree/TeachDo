<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue';
import type { CourseGroup, KBFile } from '#root/types';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useI18n } from 'vue-i18n';

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
    if (first) simulateUpload(first);
  }
};

const simulateUpload = (file: File) => {
  const newFile: KBFile = {
    id: Date.now().toString(),
    name: file.name,
    size: file.size,
    type: file.name.split('.').pop() || 'unknown',
    status: 'uploading',
    uploadedAt: new Date(),
    progress: 0,
  };

  updateFiles([...files.value, newFile]);

  let progress = 0;
  const timer = window.setInterval(() => {
    progress += 10;
    if (progress > 100) {
      progress = 100;
    }
    if (progress >= 100) {
      window.clearInterval(timer);
      uploadTimers.delete(newFile.id);
      updateFileStatus(newFile.id, 'processing', 100);
      // 与 React 版保持一致的索引等待
      window.setTimeout(() => updateFileStatus(newFile.id, 'ready'), 2000);
    } else {
      updateFileStatus(newFile.id, 'uploading', progress);
    }
  }, 300);
  uploadTimers.set(newFile.id, timer);
};

const updateFileStatus = (fileId: string, status: KBFile['status'], progress?: number) => {
  const next = files.value.map((f) => (f.id === fileId ? { ...f, status, progress: progress ?? f.progress } : f));
  updateFiles(next);
};

const handleDelete = (id: string) => {
  if (!confirm(t('kb.confirm.delete'))) return;
  const next = files.value.filter((f) => f.id !== id);
  updateFiles(next);
  toast.success(t('kb.action.delete'));
};

onBeforeUnmount(() => {
  uploadTimers.forEach((timer) => window.clearInterval(timer));
  uploadTimers.clear();
});
</script>

<template>
  <div class="h-full flex flex-col gap-6">
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
