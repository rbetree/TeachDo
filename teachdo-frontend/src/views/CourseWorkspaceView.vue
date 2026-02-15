<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import UnitSidebar from '@/components/workspace/UnitSidebar.vue';
import OutlineView from '@/components/workspace/OutlineView.vue';
import LessonPlanView from '@/components/workspace/LessonPlanView.vue';
import PPTView from '@/components/workspace/PPTView.vue';
import AssistantView from '@/components/workspace/AssistantView.vue';
import KnowledgeBaseView from '@/components/workspace/KnowledgeBaseView.vue';
import { useAppStore } from '@/stores/appStore';
import type { CourseGroup, CourseUnit } from '#root/types';
import { ViewState } from '#root/types';
import type { IconName } from '@/components/common/LucideIcon.vue';

const router = useRouter();
const route = useRoute();
const store = useAppStore();
const { t } = useI18n();

const course = computed(() => store.currentCourse);
const activeUnit = computed<CourseUnit | null>(() => store.currentUnit);
const units = computed(() => course.value?.units ?? []);

type UnitTab = 'outline' | 'lesson' | 'ppt';
type WorkspaceTab = UnitTab | 'kb' | 'assistant';

const normalizeParam = (value: unknown): string | null => {
  if (Array.isArray(value)) return value.length ? value[0] ?? null : null;
  return typeof value === 'string' ? value : null;
};

const routeTab = computed<WorkspaceTab>(() => {
  const tabRaw = normalizeParam(route.params.tab)?.toLowerCase();
  if (tabRaw === 'kb' || tabRaw === 'assistant' || tabRaw === 'outline' || tabRaw === 'lesson' || tabRaw === 'ppt') {
    return tabRaw;
  }
  return 'outline';
});

const globalMode = computed<'UNIT_VIEW' | ViewState.KNOWLEDGE_BASE | ViewState.ASSISTANT>(() => {
  if (routeTab.value === 'kb') return ViewState.KNOWLEDGE_BASE;
  if (routeTab.value === 'assistant') return ViewState.ASSISTANT;
  return 'UNIT_VIEW';
});

const activeUnitTab = computed<UnitTab>(() => {
  if (routeTab.value === 'lesson' || routeTab.value === 'ppt') return routeTab.value;
  return 'outline';
});
const isSidebarCollapsed = ref(false);
const isMobileSidebarOpen = ref(false);

const unitIndex = computed(() => {
  if (!course.value || !activeUnit.value) return -1;
  return course.value.units.findIndex((unit) => unit.id === activeUnit.value?.id);
});

watch(
  course,
  (next) => {
    if (!next) return;
    if (next.units.length === 0) {
      store.selectUnit(null);
      return;
    }
    const exists = next.units.some((unit) => unit.id === activeUnit.value?.id);
    if (!exists) {
      store.selectUnit(next.units[0]?.id ?? null);
    }
  },
  { immediate: true },
);

const goToUnitTab = (unitId: string, tab: UnitTab) => {
  if (!course.value) return;
  router.push({ name: 'course-unit', params: { courseId: course.value.id, unitId, tab } });
};

const goToCourseTab = (tab: 'kb' | 'assistant') => {
  if (!course.value) return;
  router.push({ name: 'course-tab', params: { courseId: course.value.id, tab } });
};

const handleAddUnit = (title: string) => {
  if (!course.value) return;
  const newUnit: CourseUnit = {
    id: `unit-${Date.now()}`,
    title,
    objectives: '',
    outlineContent: '',
  };
  store.updateCourseUnits(course.value.id, (list) => [...list, newUnit]);
  store.selectUnit(newUnit.id);
  goToUnitTab(newUnit.id, activeUnitTab.value);
};

const handleSelectUnit = (unitId: string) => {
  store.selectUnit(unitId);
  goToUnitTab(unitId, activeUnitTab.value);
};

const handleSelectGlobal = (view: ViewState) => {
  if (view === ViewState.KNOWLEDGE_BASE || view === ViewState.ASSISTANT) {
    goToCourseTab(view === ViewState.KNOWLEDGE_BASE ? 'kb' : 'assistant');
  }
};

const handleTabChange = (tab: UnitTab) => {
  if (!activeUnit.value) return;
  goToUnitTab(activeUnit.value.id, tab);
};

const goBack = () => {
  router.push({ name: 'workspace' });
};

const tabConfig = computed(
  () =>
    [
      { id: 'outline', label: t('workspace.tab.outline'), icon: 'layout-list' },
      { id: 'lesson', label: t('workspace.tab.lesson'), icon: 'file-text' },
      { id: 'ppt', label: t('workspace.tab.ppt'), icon: 'presentation' },
    ] satisfies { id: UnitTab; label: string; icon: IconName }[],
);

const persistActiveUnit = (unitId: string, updates: Partial<CourseUnit>) => {
  if (!course.value) return;
  const courseId = course.value.id;
  store.updateCourseUnits(courseId, (units) =>
    units.map((unit) => (unit.id === unitId ? { ...unit, ...updates } : unit)),
  );
};

const persistCourse = (updates: Partial<CourseGroup>) => {
  if (!course.value) return;
  const updated = { ...course.value, ...updates };
  store.upsertCourse(updated);
};
</script>

<template>
  <section v-if="course" class="flex h-[calc(100vh-64px)] bg-slate-50 dark:bg-slate-950 overflow-hidden font-sans text-slate-900 dark:text-slate-100">
    <UnitSidebar
      :course="course"
      :active-unit-id="activeUnit?.id ?? null"
      :current-view="globalMode"
      :collapsed="isSidebarCollapsed"
      :mobile-open="isMobileSidebarOpen"
      @select-unit="handleSelectUnit"
      @add-unit="handleAddUnit"
      @select-global="handleSelectGlobal"
      @toggle-collapse="isSidebarCollapsed = !isSidebarCollapsed"
      @close-mobile="isMobileSidebarOpen = false"
    />

    <main class="flex-1 flex flex-col relative bg-slate-50 dark:bg-slate-950 min-w-0">
      <div class="md:hidden absolute top-4 left-4 z-30">
        <button
          type="button"
          class="p-2 bg-white dark:bg-slate-800 rounded-lg shadow border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-200"
          @click="isMobileSidebarOpen = true"
        >
          <LucideIcon name="menu" class="w-5 h-5" />
        </button>
      </div>

      <div v-if="globalMode === ViewState.KNOWLEDGE_BASE" class="h-full w-full overflow-y-auto custom-scrollbar p-6 md:p-10 pt-16 md:pt-10">
        <div class="max-w-6xl mx-auto h-full animate-fade-in">
          <KnowledgeBaseView v-if="course" :current-course="course" @update-course="persistCourse" />
        </div>
      </div>

      <div v-else-if="globalMode === ViewState.ASSISTANT" class="h-full w-full overflow-hidden p-6 md:p-10 pt-16 md:pt-10">
        <div class="max-w-6xl mx-auto h-full animate-fade-in">
          <AssistantView
            v-if="course"
            :current-course="course"
            :current-unit="activeUnit"
            @update-course="persistCourse"
          />
        </div>
      </div>

      <div v-else class="flex-1 flex flex-col relative">
        <template v-if="activeUnit">
          <header class="px-6 md:px-8 py-5 pl-16 md:pl-8 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/70 dark:bg-slate-900/70 backdrop-blur sticky top-0 z-10 border-b border-slate-200/60 dark:border-slate-800/60">
            <div class="min-w-0">
              <div class="flex items-center text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 gap-2">
                <span>{{ t('workspace.unit.prefix') }} {{ unitIndex >= 0 ? (unitIndex + 1).toString().padStart(2, '0') : '--' }}</span>
                <span class="text-slate-300">•</span>
                <span :class="activeUnit.outlineContent ? 'text-emerald-500' : 'text-amber-500'">
                  {{ activeUnit.outlineContent ? t('workspace.unit.inprogress') : t('workspace.unit.draft') }}
                </span>
              </div>
              <h2 class="text-2xl font-black text-slate-800 dark:text-white truncate">
                {{ activeUnit.title }}
              </h2>
            </div>
            <div class="flex p-1 bg-slate-200/40 dark:bg-slate-800 rounded-xl overflow-x-auto no-scrollbar gap-1">
              <button
                v-for="tab in tabConfig"
                :key="tab.id"
                type="button"
                class="relative px-4 md:px-5 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2 whitespace-nowrap"
                :class="activeUnitTab === tab.id ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-300 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-100'"
                @click="handleTabChange(tab.id)"
              >
                <LucideIcon :name="tab.icon" class="w-4 h-4" />
                <span>{{ tab.label }}</span>
              </button>
            </div>
          </header>

            <div class="flex-1 overflow-hidden">
            <div v-if="activeUnitTab === 'outline'" class="h-full p-6 md:p-10">
              <div class="h-full max-w-6xl mx-auto">
                <OutlineView
                  v-if="course && activeUnit"
                  :current-course="course"
                  :current-unit="activeUnit"
                  @update-unit="persistActiveUnit"
                />
              </div>
            </div>

            <div v-else-if="activeUnitTab === 'lesson'" class="h-full p-6 md:p-10">
              <div class="h-full max-w-6xl mx-auto">
                <LessonPlanView
                  v-if="course && activeUnit"
                  :current-course="course"
                  :current-unit="activeUnit"
                  @update-unit="persistActiveUnit"
                  @navigate="(view) => (view === ViewState.OUTLINE ? handleTabChange('outline') : undefined)"
                />
              </div>
            </div>

            <div v-else class="h-full p-6 md:p-10">
              <div class="h-full max-w-6xl mx-auto">
                <PPTView
                  v-if="course && activeUnit"
                  :current-course="course"
                  :current-unit="activeUnit"
                  @update-unit="persistActiveUnit"
                />
              </div>
            </div>
          </div>
        </template>

        <div v-else class="flex-1 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400 gap-4">
          <div class="w-20 h-20 rounded-3xl bg-white dark:bg-slate-800 shadow flex items-center justify-center text-4xl animate-pulse">
            👋
          </div>
          <p class="text-lg font-semibold text-slate-700 dark:text-slate-200">
            {{ units.length ? t('workspace.empty') : t('course.list.empty') }}
          </p>
        </div>
      </div>
    </main>
  </section>

  <section v-else class="text-center py-20 space-y-4 text-slate-500 dark:text-slate-400">
    <p>{{ t('workspace.no_course') }}</p>
    <button type="button" class="px-4 py-2 rounded-lg bg-indigo-600 text-white" @click="goBack">{{ t('workspace.back') }}</button>
  </section>
</template>
