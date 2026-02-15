import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import type { Pinia } from 'pinia';
import { useAppStore } from '@/stores/appStore';

const MainLayout = () => import('@/layouts/MainLayout.vue');
const CourseSelectionView = () => import('@/views/CourseSelectionView.vue');
const CourseWorkspaceView = () => import('@/views/CourseWorkspaceView.vue');
const AboutView = () => import('@/views/AboutView.vue');
const SettingsView = () => import('@/views/SettingsView.vue');

declare module 'vue-router' {
  interface RouteMeta {
    requiresCourse?: boolean;
    requiresUnit?: boolean;
  }
}

const UNIT_TABS = new Set(['outline', 'lesson', 'ppt'] as const);
const COURSE_TABS = new Set(['kb', 'assistant'] as const);

type UnitTab = 'outline' | 'lesson' | 'ppt';
type CourseTab = 'kb' | 'assistant';

const normalizeParam = (value: unknown): string | null => {
  if (Array.isArray(value)) return value.length ? value[0] ?? null : null;
  return typeof value === 'string' ? value : null;
};

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'workspace',
        component: CourseSelectionView,
      },
      {
        path: 'course/:courseId',
        name: 'course',
        component: CourseWorkspaceView,
        meta: { requiresCourse: true },
      },
      {
        path: 'course/:courseId/:tab',
        name: 'course-tab',
        component: CourseWorkspaceView,
        meta: { requiresCourse: true },
      },
      {
        path: 'course/:courseId/unit/:unitId/:tab',
        name: 'course-unit',
        component: CourseWorkspaceView,
        meta: { requiresCourse: true, requiresUnit: true },
      },
      {
        path: 'about',
        name: 'about',
        component: AboutView,
      },
      {
        path: 'settings',
        name: 'settings',
        component: SettingsView,
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
];

export const createAppRouter = (pinia: Pinia) => {
  const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes,
  });

  router.beforeEach((to) => {
    const store = useAppStore(pinia);

    if (!to.meta.requiresCourse) {
      store.selectCourse(null);
      return true;
    }

    const courseId = normalizeParam(to.params.courseId);
    if (!courseId) return { name: 'workspace' };

    const course = store.courses.find((item) => item.id === courseId);
    if (!course) return { name: 'workspace' };

    if (store.currentCourseId !== courseId) {
      store.selectCourse(courseId);
    } else if (store.currentUnitId && !course.units.some((u) => u.id === store.currentUnitId)) {
      store.selectUnit(course.units[0]?.id ?? null);
    }

    if (to.name === 'course') {
      if (course.units.length === 0) {
        return true;
      }
      const unitId = store.currentUnitId ?? course.units[0]?.id;
      if (!unitId) return true;
      return { name: 'course-unit', params: { courseId, unitId, tab: 'outline' satisfies UnitTab } };
    }

    if (to.name === 'course-tab') {
      const tabRaw = normalizeParam(to.params.tab)?.toLowerCase();
      if (!tabRaw || !COURSE_TABS.has(tabRaw as CourseTab)) {
        return { name: 'course', params: { courseId } };
      }
      return true;
    }

    if (to.name === 'course-unit') {
      const unitIdParam = normalizeParam(to.params.unitId);
      const tabRaw = normalizeParam(to.params.tab)?.toLowerCase();

      if (tabRaw && COURSE_TABS.has(tabRaw as CourseTab)) {
        return { name: 'course-tab', params: { courseId, tab: tabRaw } };
      }

      const unitId = unitIdParam && course.units.some((u) => u.id === unitIdParam) ? unitIdParam : course.units[0]?.id;
      if (!unitId) {
        return { name: 'course', params: { courseId } };
      }

      const tab: UnitTab = tabRaw && UNIT_TABS.has(tabRaw as UnitTab) ? (tabRaw as UnitTab) : 'outline';

      if (store.currentUnitId !== unitId) {
        store.selectUnit(unitId);
      }

      const needsRedirect = unitId !== unitIdParam || tab !== tabRaw;
      if (needsRedirect) {
        return { name: 'course-unit', params: { courseId, unitId, tab } };
      }
    }

    return true;
  });

  return router;
};
