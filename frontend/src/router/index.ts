import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import type { Pinia } from 'pinia';
import { useAppStore } from '@/stores/appStore';

const MainLayout = () => import('@/layouts/MainLayout.vue');
const TeachingMaterialSelectionView = () => import('@/views/TeachingMaterialSelectionView.vue');
const TeachingMaterialWorkspaceView = () => import('@/views/TeachingMaterialWorkspaceView.vue');
const PPTEditorView = () => import('@/views/PPTEditorView.vue');
const AboutView = () => import('@/views/AboutView.vue');
const SettingsView = () => import('@/views/SettingsView.vue');

declare module 'vue-router' {
  interface RouteMeta {
    requiresMaterial?: boolean;
  }
}

const MATERIAL_TABS = new Set(['outline', 'lesson', 'ppt', 'assistant'] as const);
type MaterialTab = 'outline' | 'lesson' | 'ppt' | 'assistant';

const normalizeParam = (value: unknown): string | null => {
  if (Array.isArray(value)) return value.length ? value[0] ?? null : null;
  return typeof value === 'string' ? value : null;
};

const routes: RouteRecordRaw[] = [
  {
    path: '/material/:materialId/ppt/editor',
    name: 'material-ppt-editor',
    component: PPTEditorView,
    meta: { requiresMaterial: true },
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'workspace',
        component: TeachingMaterialSelectionView,
      },
      {
        path: 'material/:materialId',
        name: 'material',
        component: TeachingMaterialWorkspaceView,
        meta: { requiresMaterial: true },
      },
      {
        path: 'material/:materialId/:tab',
        name: 'material-tab',
        component: TeachingMaterialWorkspaceView,
        meta: { requiresMaterial: true },
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

    if (to.name === 'workspace') {
      store.selectMaterial(null);
      return true;
    }

    if (!to.meta.requiresMaterial) return true;

    const materialId = normalizeParam(to.params.materialId);
    if (!materialId) return { name: 'workspace' };

    const materialExists = store.materials.some((m) => m.id === materialId);
    if (!materialExists) return { name: 'workspace' };

    if (store.currentMaterialId !== materialId) {
      store.selectMaterial(materialId);
    }

    if (to.name === 'material') {
      return { name: 'material-tab', params: { materialId, tab: 'outline' satisfies MaterialTab } };
    }

    if (to.name === 'material-tab') {
      const tabRaw = normalizeParam(to.params.tab)?.toLowerCase();
      const tab: MaterialTab = tabRaw && MATERIAL_TABS.has(tabRaw as MaterialTab) ? (tabRaw as MaterialTab) : 'outline';
      if (tabRaw !== tab) {
        return { name: 'material-tab', params: { materialId, tab } };
      }
    }

    return true;
  });

  return router;
};
