<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import UnitSidebar from '@/components/workspace/UnitSidebar.vue';
import WorkspaceRightPanel from '@/components/workspace/WorkspaceRightPanel.vue';
import { useAppStore } from '@/stores/appStore';
import type { CourseGroup, CourseUnit } from '#root/types';
import { ViewState } from '#root/types';
import type { IconName } from '@/components/common/LucideIcon.vue';
import { useWorkspaceUiStore } from '@/stores/workspaceUiStore';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';

const OutlineView = defineAsyncComponent(() => import('@/components/workspace/OutlineView.vue'));
const LessonPlanView = defineAsyncComponent(() => import('@/components/workspace/LessonPlanView.vue'));
const PPTView = defineAsyncComponent(() => import('@/components/workspace/PPTView.vue'));

const router = useRouter();
const route = useRoute();
const store = useAppStore();
const { t } = useI18n();
const ui = useWorkspaceUiStore();

const course = computed(() => store.currentCourse);
const activeUnit = computed<CourseUnit | null>(() => store.currentUnit);
const units = computed(() => course.value?.units ?? []);

type UnitTab = 'outline' | 'lesson' | 'ppt';

const normalizeParam = (value: unknown): string | null => {
  if (Array.isArray(value)) return value.length ? value[0] ?? null : null;
  return typeof value === 'string' ? value : null;
};

const activeUnitTab = computed<UnitTab>(() => {
  const tabRaw = normalizeParam(route.params.tab)?.toLowerCase();
  if (tabRaw === 'lesson' || tabRaw === 'ppt') return tabRaw;
  return 'outline';
});
const isSidebarCollapsed = ref(false);
const isMobileSidebarOpen = ref(false);

watch(
  () => normalizeParam(route.params.tab)?.toLowerCase(),
  (tabRaw) => {
    if (tabRaw === 'kb' || tabRaw === 'assistant') {
      ui.setRightPanelTab(tabRaw);
    }
  },
  { immediate: true },
);

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

const handleAddUnit = async (payload: { title: string; objectives: string }) => {
  if (!course.value) return;
  const currentCourse = course.value;

  const newUnit: CourseUnit = {
    id: `unit-${Date.now()}`,
    title: payload.title,
    objectives: payload.objectives,
    outlineContent: '',
  };
  store.updateCourseUnits(currentCourse.id, (list) => [...list, newUnit]);
  store.selectUnit(newUnit.id);
  goToUnitTab(newUnit.id, 'outline');

  // 创建单元后立即生成大纲（大纲不属于 PPT/教案步骤）
  toast.info(t('outline.crafting'));
  try {
    const outline = await aiService.generateOutline(currentCourse, newUnit);
    persistActiveUnit(newUnit.id, { outlineContent: outline });

    // 产物入库（失败不阻断）
    void aiService
      .vectorizeTextToKb({
        userId: currentCourse.id,
        fileId: `gen:${currentCourse.id}:${newUnit.id}:outline`,
        fileName: `大纲-${newUnit.title}`,
        content: outline.trim(),
        fileType: 'md',
        folderId: 1,
      })
      .catch((e) => console.warn('大纲入库失败（已忽略）', e));

    toast.success(t('outline.toast.generated'));
  } catch (e) {
    console.error(e);
    toast.error(t('outline.toast.error'));
  }
};

const handleSelectUnit = (unitId: string) => {
  store.selectUnit(unitId);
  goToUnitTab(unitId, activeUnitTab.value);
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
      :collapsed="isSidebarCollapsed"
      :mobile-open="isMobileSidebarOpen"
      @select-unit="handleSelectUnit"
      @add-unit="handleAddUnit"
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
	
	      <div class="flex-1 flex flex-col relative min-h-0">
	        <template v-if="activeUnit">
	          <header class="px-6 md:px-8 py-3 pl-16 md:pl-8 bg-white/70 dark:bg-slate-900/70 backdrop-blur sticky top-0 z-10 border-b border-slate-200/60 dark:border-slate-800/60">
	            <h2 class="sr-only">{{ activeUnit.title }}</h2>
	            <!-- Tab -->
	            <div class="flex p-1 bg-slate-200/40 dark:bg-slate-800 rounded-xl overflow-x-auto no-scrollbar gap-1 w-fit">
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
	
	          <div class="flex-1 overflow-hidden min-h-0">
	            <div v-if="activeUnitTab === 'outline'" class="h-full p-6 md:p-8">
	              <div class="h-full max-w-6xl mx-auto min-h-0">
	                <OutlineView
	                  v-if="course && activeUnit"
	                  :current-course="course"
	                  :current-unit="activeUnit"
                  @update-unit="persistActiveUnit"
	                />
	              </div>
	            </div>
	
	            <div v-else-if="activeUnitTab === 'lesson'" class="h-full p-6 md:p-8">
	              <div class="h-full max-w-6xl mx-auto min-h-0">
	                <LessonPlanView
	                  v-if="course && activeUnit"
	                  :current-course="course"
	                  :current-unit="activeUnit"
                  @update-unit="persistActiveUnit"
                  @navigate="(view) => (view === ViewState.OUTLINE ? handleTabChange('outline') : undefined)"
	                />
	              </div>
	            </div>
	
	            <div v-else class="h-full p-6 md:p-8">
	              <div class="h-full max-w-6xl mx-auto min-h-0">
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

    <WorkspaceRightPanel
      :current-course="course"
      :current-unit="activeUnit"
      @update-course="persistCourse"
    />
  </section>

  <section v-else class="text-center py-20 space-y-4 text-slate-500 dark:text-slate-400">
    <p>{{ t('workspace.no_course') }}</p>
    <button type="button" class="px-4 py-2 rounded-lg bg-indigo-600 text-white" @click="goBack">{{ t('workspace.back') }}</button>
  </section>
</template>
