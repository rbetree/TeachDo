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
  }
}

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
        name: 'course-workspace',
        component: CourseWorkspaceView,
        meta: { requiresCourse: true },
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

    if (to.meta.requiresCourse) {
      const courseIdParam = to.params.courseId;
      const courseId = Array.isArray(courseIdParam) ? courseIdParam[0] : courseIdParam;
      if (!courseId || typeof courseId !== 'string') {
        return { name: 'workspace' };
      }
      const exists = store.courses.some((course) => course.id === courseId);
      if (!exists) {
        return { name: 'workspace' };
      }
      store.selectCourse(courseId);
    }

    if (!to.meta.requiresCourse && to.name !== 'course-workspace') {
      store.selectCourse(null);
    }

    return true;
  });

  return router;
};
