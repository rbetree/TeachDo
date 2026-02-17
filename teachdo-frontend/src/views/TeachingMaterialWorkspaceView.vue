<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import WorkspaceRightPanel from '@/components/workspace/WorkspaceRightPanel.vue';
import { useAppStore } from '@/stores/appStore';
import type { TeachingMaterial } from '#root/types';
import type { IconName } from '@/components/common/LucideIcon.vue';

const OutlineView = defineAsyncComponent(() => import('@/components/workspace/OutlineView.vue'));
const LessonPlanView = defineAsyncComponent(() => import('@/components/workspace/LessonPlanView.vue'));
const PPTView = defineAsyncComponent(() => import('@/components/workspace/PPTView.vue'));

const router = useRouter();
const route = useRoute();
const store = useAppStore();
const { t } = useI18n();

const currentMaterial = computed(() => store.currentMaterial);

type MaterialTab = 'outline' | 'lesson' | 'ppt';

const normalizeParam = (value: unknown): string | null => {
  if (Array.isArray(value)) return value.length ? value[0] ?? null : null;
  return typeof value === 'string' ? value : null;
};

const activeTab = computed<MaterialTab>(() => {
  const tabRaw = normalizeParam(route.params.tab)?.toLowerCase();
  if (tabRaw === 'lesson' || tabRaw === 'ppt') return tabRaw;
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
    ] satisfies { id: MaterialTab; label: string; icon: IconName }[],
);

const goBack = () => {
  router.push({ name: 'workspace' });
};
</script>

<template>
  <section
    v-if="currentMaterial"
    class="flex h-[calc(100vh-64px)] bg-slate-50 dark:bg-slate-950 overflow-hidden font-sans text-slate-900 dark:text-slate-100"
  >
    <WorkspaceRightPanel :current-material="currentMaterial" />

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

            <button
              type="button"
              class="shrink-0 w-11 h-11 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/60 text-slate-600 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 hover:text-indigo-600 dark:hover:text-indigo-300 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              :aria-label="t('workspace.back')"
              :title="t('workspace.back')"
              @click="goBack"
            >
              <LucideIcon name="arrow-left" class="w-5 h-5 mx-auto" />
            </button>
          </div>

          <div class="flex p-1 bg-slate-200/40 dark:bg-slate-800 rounded-xl overflow-x-auto no-scrollbar gap-1 w-fit">
            <button
              v-for="tab in tabConfig"
              :key="tab.id"
              type="button"
              class="relative px-4 md:px-5 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2 whitespace-nowrap"
              :class="activeTab === tab.id ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-300 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-100'"
              @click="goToTab(tab.id)"
            >
              <LucideIcon :name="tab.icon" class="w-4 h-4" />
              <span>{{ tab.label }}</span>
            </button>
          </div>
        </header>

        <div class="flex-1 overflow-hidden min-h-0">
          <div v-if="activeTab === 'outline'" class="h-full p-6 md:p-8">
            <div class="h-full max-w-6xl mx-auto min-h-0">
              <OutlineView
                v-if="currentMaterial"
                :current-material="currentMaterial"
                @update-material="persistMaterial"
              />
            </div>
          </div>

          <div v-else-if="activeTab === 'lesson'" class="h-full p-6 md:p-8">
            <div class="h-full max-w-6xl mx-auto min-h-0">
              <LessonPlanView
                v-if="currentMaterial"
                :current-material="currentMaterial"
                @update-material="persistMaterial"
                @navigate="(tab) => (tab === 'outline' ? goToTab('outline') : undefined)"
              />
            </div>
          </div>

          <div v-else class="h-full p-6 md:p-8">
            <div class="h-full max-w-6xl mx-auto min-h-0">
              <PPTView
                v-if="currentMaterial"
                :current-material="currentMaterial"
                @update-material="persistMaterial"
              />
            </div>
          </div>
        </div>
      </div>
    </main>
  </section>

  <section v-else class="text-center py-20 space-y-4 text-slate-500 dark:text-slate-400">
    <p>{{ t('workspace.no_course') }}</p>
    <button type="button" class="px-4 py-2 rounded-lg bg-indigo-600 text-white" @click="goBack">{{ t('workspace.back') }}</button>
  </section>
</template>
