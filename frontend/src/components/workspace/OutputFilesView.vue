<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import type { KBFile, TeachingMaterial } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { KB_USER_ID, useAppStore } from '@/stores/appStore';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import type { ArtifactMeta } from '@/services/ai/artifactService';

interface Props {
  currentMaterial: TeachingMaterial;
}

const props = defineProps<Props>();
const router = useRouter();
const { t } = useI18n();
const store = useAppStore();

const exportingKbFileId = ref<string | null>(null);
const loadingArtifacts = ref(false);
const artifacts = ref<ArtifactMeta[]>([]);
const artifactsError = ref<string | null>(null);
const downloadingArtifactId = ref<string | null>(null);
const deletingArtifactId = ref<string | null>(null);

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
const selectedGenCount = computed(() => selectedGenIdSet.value.size);

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

const docxArtifacts = computed(() => artifacts.value.filter((a) => a.kind === 'docx'));
const pptxArtifacts = computed(() => artifacts.value.filter((a) => a.kind === 'pptx'));

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

const handleDeleteArtifact = async (artifact: ArtifactMeta) => {
  if (!artifact?.artifact_id) return;
  if (!confirm('确认删除该文件？')) return;
  deletingArtifactId.value = artifact.artifact_id;
  try {
    await aiService.deleteArtifact({ userId: KB_USER_ID, materialId: props.currentMaterial.id, artifactId: artifact.artifact_id });
    toast.success('已删除');
    await refreshArtifacts();
  } catch (e) {
    console.error(e);
    toast.error(t('kb.toast.delete_failed'));
  } finally {
    deletingArtifactId.value = null;
  }
};

const goToLessonTab = async () => {
  await router.push({ name: 'material-tab', params: { materialId: props.currentMaterial.id, tab: 'lesson' } });
};

const goToPptEditor = async () => {
  await router.push({ name: 'material-ppt-editor', params: { materialId: props.currentMaterial.id } });
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
</script>

<template>
  <div class="h-full flex flex-col gap-4">
    <section class="bg-white/60 dark:bg-slate-900/30 rounded-2xl border border-slate-200/60 dark:border-slate-800/60 overflow-hidden">
      <header class="px-4 py-3 border-b border-slate-200/60 dark:border-slate-800/60 flex items-center justify-between gap-2">
        <div class="min-w-0">
          <div class="text-sm font-extrabold text-slate-800 dark:text-slate-100 truncate">文本产物（Markdown）</div>
          <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">勾选后将全文加入上下文（不检索）</div>
        </div>

        <button
          type="button"
          class="px-2 py-1 rounded-lg text-[11px] font-bold text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
          :disabled="selectedGenCount === 0"
          @click="clearSelectedGen"
        >
          清空
        </button>
      </header>

      <div class="max-h-[38vh] overflow-auto custom-scrollbar">
        <div v-if="kbOutputFiles.length === 0" class="p-4 text-xs text-slate-500 dark:text-slate-400">
          暂无文本产物。生成大纲/PPT/教案后，这里会出现可勾选的产物。
        </div>

        <div v-else class="divide-y divide-slate-200/50 dark:divide-slate-800/50">
          <div
            v-for="file in kbOutputFiles"
            :key="file.id"
            class="px-4 py-3 flex items-start justify-between gap-3 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors"
          >
            <label class="flex items-start gap-3 min-w-0 cursor-pointer">
              <input
                type="checkbox"
                class="mt-1 w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500/40"
                :checked="selectedGenIdSet.has(file.id)"
                @change="() => toggleGenSelected(file.id)"
              />
              <div class="min-w-0">
                <div class="text-sm font-bold text-slate-800 dark:text-slate-100 truncate" :title="file.name">{{ file.name }}</div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-2">
                  <span class="font-mono truncate">{{ file.id }}</span>
                  <span v-if="file.size" class="shrink-0">{{ formatSize(file.size) }}</span>
                  <span v-if="file.uploadedAt" class="shrink-0">{{ formatDateTime(file.uploadedAt) }}</span>
                </div>
              </div>
            </label>

            <div class="flex items-center gap-2 shrink-0">
              <button
                type="button"
                class="w-10 h-10 inline-flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-900 transition-colors disabled:opacity-40"
                :aria-label="t('kb.action.export')"
                :title="t('kb.action.export')"
                :disabled="file.status !== 'ready' || exportingKbFileId === file.id"
                @click="handleExportKb(file)"
              >
                <LucideIcon name="download" class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="bg-white/60 dark:bg-slate-900/30 rounded-2xl border border-slate-200/60 dark:border-slate-800/60 overflow-hidden">
      <header class="px-4 py-3 border-b border-slate-200/60 dark:border-slate-800/60 flex items-center justify-between gap-2">
        <div class="min-w-0">
          <div class="text-sm font-extrabold text-slate-800 dark:text-slate-100 truncate">导出文件（DOCX/PPTX）</div>
          <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">后端持久化存储，可再次下载</div>
        </div>

        <button
          type="button"
          class="w-10 h-10 inline-flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-900 transition-colors disabled:opacity-40"
          :aria-label="t('kb.action.refresh')"
          :title="t('kb.action.refresh')"
          :disabled="loadingArtifacts"
          @click="refreshArtifacts"
        >
          <LucideIcon name="refresh-cw" class="w-4 h-4" :class="loadingArtifacts ? 'animate-spin' : ''" />
        </button>
      </header>

      <div class="p-4 space-y-3">
        <div v-if="artifactsError" class="text-xs text-red-600 dark:text-red-300">
          {{ artifactsError }}
        </div>

        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <div class="text-xs font-bold text-slate-600 dark:text-slate-300">教案（DOCX）</div>
            <button
              v-if="docxArtifacts.length === 0"
              type="button"
              class="text-[11px] font-bold text-indigo-600 hover:text-indigo-700 hover:underline"
              @click="goToLessonTab"
            >
              去教案页导出并保存
            </button>
          </div>

          <div v-if="docxArtifacts.length === 0" class="text-xs text-slate-500 dark:text-slate-400">
            暂无教案 DOCX。
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="a in docxArtifacts"
              :key="a.artifact_id"
              class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl border border-slate-200/60 dark:border-slate-800/60 bg-white/70 dark:bg-slate-900/30"
            >
              <div class="min-w-0">
                <div class="text-sm font-bold text-slate-800 dark:text-slate-100 truncate" :title="a.file_name">{{ a.file_name }}</div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-2">
                  <span class="font-mono truncate">{{ a.artifact_id }}</span>
                  <span v-if="typeof a.size === 'number'" class="shrink-0">{{ formatSize(a.size) }}</span>
                  <span v-if="typeof a.created_at === 'number'" class="shrink-0">{{ formatDateTime(a.created_at) }}</span>
                </div>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  class="w-10 h-10 inline-flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-900 transition-colors disabled:opacity-40"
                  :disabled="downloadingArtifactId === a.artifact_id"
                  @click="handleDownloadArtifact(a)"
                >
                  <LucideIcon name="download" class="w-4 h-4" />
                </button>
                <button
                  type="button"
                  class="w-10 h-10 inline-flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 hover:text-red-600 hover:border-red-200 dark:hover:border-red-800/40 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-40"
                  :disabled="deletingArtifactId === a.artifact_id"
                  @click="handleDeleteArtifact(a)"
                >
                  <LucideIcon name="trash-2" class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-2 pt-2 border-t border-slate-200/60 dark:border-slate-800/60">
          <div class="flex items-center justify-between">
            <div class="text-xs font-bold text-slate-600 dark:text-slate-300">幻灯片（PPTX）</div>
            <button
              v-if="pptxArtifacts.length === 0"
              type="button"
              class="text-[11px] font-bold text-indigo-600 hover:text-indigo-700 hover:underline"
              @click="goToPptEditor"
            >
              去编辑器导出并保存
            </button>
          </div>

          <div v-if="pptxArtifacts.length === 0" class="text-xs text-slate-500 dark:text-slate-400">
            暂无 PPTX。
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="a in pptxArtifacts"
              :key="a.artifact_id"
              class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl border border-slate-200/60 dark:border-slate-800/60 bg-white/70 dark:bg-slate-900/30"
            >
              <div class="min-w-0">
                <div class="text-sm font-bold text-slate-800 dark:text-slate-100 truncate" :title="a.file_name">{{ a.file_name }}</div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-2">
                  <span class="font-mono truncate">{{ a.artifact_id }}</span>
                  <span v-if="typeof a.size === 'number'" class="shrink-0">{{ formatSize(a.size) }}</span>
                  <span v-if="typeof a.created_at === 'number'" class="shrink-0">{{ formatDateTime(a.created_at) }}</span>
                </div>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  class="w-10 h-10 inline-flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-900 transition-colors disabled:opacity-40"
                  :disabled="downloadingArtifactId === a.artifact_id"
                  @click="handleDownloadArtifact(a)"
                >
                  <LucideIcon name="download" class="w-4 h-4" />
                </button>
                <button
                  type="button"
                  class="w-10 h-10 inline-flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 hover:text-red-600 hover:border-red-200 dark:hover:border-red-800/40 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-40"
                  :disabled="deletingArtifactId === a.artifact_id"
                  @click="handleDeleteArtifact(a)"
                >
                  <LucideIcon name="trash-2" class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
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
