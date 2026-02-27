<script setup lang="ts">
import { computed, defineAsyncComponent, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import WorkspaceLeftPanel from '@/components/workspace/WorkspaceLeftPanel.vue';
import WorkspaceOutputPanel from '@/components/workspace/WorkspaceOutputPanel.vue';
import TeachingMaterialDeleteDialog from '@/components/workspace/TeachingMaterialDeleteDialog.vue';
import { KB_USER_ID, useAppStore } from '@/stores/appStore';
import { useWorkspaceUiStore } from '@/stores/workspaceUiStore';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import type { TeachingMaterial } from '#root/types';
import type { IconName } from '@/components/common/LucideIcon.vue';

const OutlineView = defineAsyncComponent(() => import('@/components/workspace/OutlineView.vue'));
const LessonPlanView = defineAsyncComponent(() => import('@/components/workspace/LessonPlanView.vue'));
const PPTView = defineAsyncComponent(() => import('@/components/workspace/PPTView.vue'));
const AssistantView = defineAsyncComponent(() => import('@/components/workspace/AssistantView.vue'));

const router = useRouter();
const route = useRoute();
const store = useAppStore();
const ui = useWorkspaceUiStore();
const { t } = useI18n();
const workspaceActionHost = ref<HTMLElement | null>(null);

const currentMaterial = computed(() => store.currentMaterial);
const deleteOpen = ref(false);
const deleting = ref(false);

const relatedKbFileIds = computed(() => {
  const material = currentMaterial.value;
  if (!material) return [];

  const prefix = `gen:${KB_USER_ID}:${material.id}:`;
  const ids = store.kbFiles
    .filter((file) => {
      const fileId = file.id || '';
      const folderId = typeof file.folderId === 'number' ? file.folderId : 0;
      return folderId === 1 && fileId.startsWith(prefix);
    })
    .map((file) => file.id);

  return Array.from(new Set(ids));
});

const relatedKbCount = computed(() => relatedKbFileIds.value.length);

const selectedReferenceCount = computed(() => {
  const material = currentMaterial.value;
  const raw = Array.isArray(material?.kbFileIds) ? material!.kbFileIds : [];
  const ids = raw
    .map((x) => (typeof x === 'string' ? x.trim() : ''))
    .filter((x) => x && !x.startsWith('gen:'));
  return new Set(ids).size;
});

const outputKbFileCount = computed(() => {
  const material = currentMaterial.value;
  if (!material) return 0;

  const prefix = `gen:${KB_USER_ID}:${material.id}:`;
  const ids = (store.kbFiles || [])
    .filter((file) => (typeof file.folderId === 'number' ? file.folderId : 0) === 1)
    .filter((file) => file.sourceMaterialId === material.id || (file.id || '').startsWith(prefix))
    .map((file) => file.id);

  return new Set(ids).size;
});

const referencePanelOpen = computed(() => !ui.referencePanelCollapsed);
const outputPanelOpen = computed(() => !ui.outputPanelCollapsed);

type MaterialTab = 'outline' | 'lesson' | 'ppt' | 'assistant';

const normalizeParam = (value: unknown): string | null => {
  if (Array.isArray(value)) return value.length ? value[0] ?? null : null;
  return typeof value === 'string' ? value : null;
};

const activeTab = computed<MaterialTab>(() => {
  const tabRaw = normalizeParam(route.params.tab)?.toLowerCase();
  if (tabRaw === 'lesson' || tabRaw === 'ppt' || tabRaw === 'assistant') return tabRaw;
  return 'outline';
});

const goToTab = (tab: MaterialTab) => {
  const material = currentMaterial.value;
  if (!material) return;
  router.push({ name: 'material-tab', params: { materialId: material.id, tab } });
};

const persistMaterial = (updates: Partial<TeachingMaterial>) => {
  const material = currentMaterial.value;
  if (!material) return;
  store.patchMaterial(material.id, updates);
};

const tabConfig = computed(
  () =>
    [
      { id: 'outline', label: t('workspace.tab.outline'), icon: 'layout-list' },
      { id: 'lesson', label: t('workspace.tab.lesson'), icon: 'file-text' },
      { id: 'ppt', label: t('workspace.tab.ppt'), icon: 'presentation' },
      { id: 'assistant', label: t('workspace.tab.assistant'), icon: 'bot' },
    ] satisfies { id: MaterialTab; label: string; icon: IconName }[],
);

const goBack = () => {
  router.push({ name: 'workspace' });
};

const handleDeleteConfirm = async (payload: { deleteKbFiles: boolean }) => {
  const material = currentMaterial.value;
  if (!material) return;
  if (deleting.value) return;

  deleting.value = true;
  try {
    if (payload.deleteKbFiles) {
      const prefix = `gen:${KB_USER_ID}:${material.id}:`;
      let fileIds = relatedKbFileIds.value;
      if (!fileIds.length) {
        try {
          const serverFiles = await aiService.kbListFiles({ userId: KB_USER_ID });
          fileIds = serverFiles
            .filter((f) => (typeof f.folder_id === 'number' ? f.folder_id : 0) === 1 && (f.file_id || '').startsWith(prefix))
            .map((f) => f.file_id);
        } catch (e) {
          console.warn('知识库文件列表拉取失败（已忽略）', e);
          fileIds = [];
        }
      }
      if (fileIds.length) {
        const ids = new Set(fileIds);
        store.setKbFiles(store.kbFiles.filter((f) => !ids.has(f.id)));

        const results = await Promise.allSettled(
          fileIds.map((fileId) => aiService.kbDeleteFile({ userId: KB_USER_ID, fileId })),
        );
        const failed = results.filter((r) => r.status === 'rejected').length;
        if (failed > 0) {
          toast.error(t('material.delete.toast.kb_partial_failed', { count: failed }));
        } else {
          toast.success(t('material.delete.toast.kb_deleted', { count: fileIds.length }));
        }
      }
    }

    const removed = store.removeMaterial(material.id);
    if (!removed) {
      toast.error(t('material.delete.toast.failed'));
      return;
    }

    deleteOpen.value = false;
    toast.success(t('material.delete.toast.deleted'));
    await router.push({ name: 'workspace' });
  } catch (e) {
    console.error(e);
    toast.error(t('material.delete.toast.failed'));
  } finally {
    deleting.value = false;
  }
};
</script>

<template>
  <section
    v-if="currentMaterial"
    class="flex h-[calc(100vh-64px)] bg-slate-50 dark:bg-slate-950 overflow-hidden font-sans text-slate-900 dark:text-slate-100"
  >
    <WorkspaceLeftPanel :current-material="currentMaterial" />

    <main class="flex-1 flex flex-col relative bg-slate-50 dark:bg-slate-950 min-w-0">
      <div class="flex-1 flex flex-col relative min-h-0">
        <header class="px-6 md:px-8 py-3 bg-white/70 dark:bg-slate-900/70 backdrop-blur sticky top-0 z-10 border-b border-slate-200/60 dark:border-slate-800/60">
          <div class="flex items-center justify-between gap-4 mb-3">
            <div class="min-w-0">
              <h2 class="text-sm md:text-base font-black text-slate-900 dark:text-white truncate" :title="currentMaterial.title">
                {{ currentMaterial.title }}
              </h2>
              <span class="text-[10px] font-bold px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 uppercase tracking-widest mt-1 inline-block">
                {{ currentMaterial.subject }}
              </span>
            </div>

            <div class="flex items-center gap-2 shrink-0">
              <button
                type="button"
                class="w-11 h-11 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/60 text-slate-600 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 hover:text-red-600 dark:hover:text-red-300 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/50"
                :aria-label="t('material.delete.title')"
                :title="t('material.delete.title')"
                @click="deleteOpen = true"
              >
                <LucideIcon name="trash-2" class="w-5 h-5 mx-auto" />
              </button>
              <button
                type="button"
                class="w-11 h-11 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/60 text-slate-600 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 hover:text-indigo-600 dark:hover:text-indigo-300 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                :aria-label="t('workspace.back')"
                :title="t('workspace.back')"
                @click="goBack"
              >
                <LucideIcon name="arrow-left" class="w-5 h-5 mx-auto" />
              </button>
            </div>
          </div>

          <div class="flex flex-col xl:flex-row xl:items-center gap-3">
            <div class="toolbar-shell gap-1 w-fit max-w-full">
              <button
                v-for="tab in tabConfig"
                :key="tab.id"
                type="button"
                class="toolbar-item relative"
                :class="activeTab === tab.id ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-300 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-100'"
                @click="goToTab(tab.id)"
              >
                <LucideIcon :name="tab.icon" class="w-4 h-4" />
                <span>{{ tab.label }}</span>
              </button>
            </div>

            <div class="flex-1 min-w-0">
              <div class="toolbar-shell gap-1">
                <button
                  type="button"
                  class="toolbar-item px-3 md:hidden border transition-colors"
                  :class="referencePanelOpen
                    ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-200 hover:bg-indigo-100 dark:hover:bg-indigo-900/30'
                    : 'bg-white/80 dark:bg-slate-700 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600'"
                  :aria-label="t('workspace.references.title')"
                  :title="t('workspace.references.title')"
                  @click="ui.toggleReferencePanel()"
                >
                  <LucideIcon name="database" class="w-4 h-4" />
                  <span>{{ t('workspace.references.title') }}</span>
                  <span
                    v-if="selectedReferenceCount > 0"
                    class="ml-1 inline-flex items-center justify-center min-w-6 h-5 px-1.5 rounded-full bg-indigo-600 text-white text-[11px] font-black"
                  >
                    {{ selectedReferenceCount }}
                  </span>
                </button>

                <button
                  type="button"
                  class="toolbar-item px-3 md:hidden border transition-colors"
                  :class="outputPanelOpen
                    ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 hover:bg-emerald-100 dark:hover:bg-emerald-900/30'
                    : 'bg-white/80 dark:bg-slate-700 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600'"
                  :aria-label="t('workspace.outputs.title')"
                  :title="t('workspace.outputs.title')"
                  @click="ui.toggleOutputPanel()"
                >
                  <LucideIcon name="file" class="w-4 h-4" />
                  <span>{{ t('workspace.outputs.title') }}</span>
                  <span
                    v-if="outputKbFileCount > 0"
                    class="ml-1 inline-flex items-center justify-center min-w-6 h-5 px-1.5 rounded-full bg-emerald-600 text-white text-[11px] font-black"
                  >
                    {{ outputKbFileCount }}
                  </span>
                </button>
                <div ref="workspaceActionHost" class="flex-1 min-w-0 flex items-center h-full"></div>
              </div>
            </div>
          </div>
        </header>

        <div class="flex-1 overflow-hidden min-h-0">
          <div v-if="activeTab === 'outline'" class="h-full p-4 md:p-5">
            <div class="h-full max-w-6xl mx-auto min-h-0">
              <OutlineView
                v-if="currentMaterial"
                :current-material="currentMaterial"
                :header-action-host="workspaceActionHost"
                @update-material="persistMaterial"
              />
            </div>
          </div>

          <div v-else-if="activeTab === 'lesson'" class="h-full p-4 md:p-5">
            <div class="h-full max-w-6xl mx-auto min-h-0">
              <LessonPlanView
                v-if="currentMaterial"
                :current-material="currentMaterial"
                :header-action-host="workspaceActionHost"
                @update-material="persistMaterial"
                @navigate="(tab) => (tab === 'outline' ? goToTab('outline') : undefined)"
              />
            </div>
          </div>

          <div v-else-if="activeTab === 'ppt'" class="h-full p-4 md:p-5">
            <div class="h-full max-w-6xl mx-auto min-h-0">
              <PPTView
                v-if="currentMaterial"
                :current-material="currentMaterial"
                :header-action-host="workspaceActionHost"
                @update-material="persistMaterial"
              />
            </div>
          </div>

          <div v-else class="h-full p-4 md:p-5">
            <div class="h-full max-w-6xl mx-auto min-h-0">
              <AssistantView v-if="currentMaterial" :current-material="currentMaterial" variant="page" />
            </div>
          </div>
        </div>
      </div>
    </main>

    <WorkspaceOutputPanel :current-material="currentMaterial" />
  </section>

  <section v-else class="text-center py-20 space-y-4 text-slate-500 dark:text-slate-400">
    <p>{{ t('workspace.no_course') }}</p>
    <button type="button" class="px-4 py-2 rounded-lg bg-indigo-600 text-white" @click="goBack">{{ t('workspace.back') }}</button>
  </section>

  <TeachingMaterialDeleteDialog
    v-if="currentMaterial"
    :open="deleteOpen"
    :material="currentMaterial"
    :related-kb-count="relatedKbCount"
    :loading="deleting"
    @update:open="(v) => (deleteOpen = v)"
    @confirm="handleDeleteConfirm"
  />
</template>
