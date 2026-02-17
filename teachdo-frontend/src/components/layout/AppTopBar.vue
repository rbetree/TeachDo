<script setup lang="ts">
/* eslint-env browser */
/* global window */
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import BrandLogo from '@/components/common/BrandLogo.vue';
import { useAppStore } from '@/stores/appStore';
import { fetchWithTimeout } from '@/utils/fetchUtils';

const router = useRouter();
const route = useRoute();
const store = useAppStore();
const { t } = useI18n();

const backendConnected = ref<boolean | null>(null);
const isChecking = ref(false);
const lastCheckAt = ref(0);

const healthUrl = '/api/healthz';

const currentMaterialTitle = computed(() => {
  const param = route.params.materialId;
  const materialId = Array.isArray(param) ? param[0] : param;
  if (!materialId) return '';
  const target = store.materials.find((material) => material.id === materialId);
  return target?.title ?? '';
});

const isHome = computed(() => ['workspace', 'material', 'material-tab'].includes((route.name as string) ?? ''));
const isAbout = computed(() => route.name === 'about');
const isSettings = computed(() => route.name === 'settings');

const toggleLanguage = () => {
  store.setLanguage(store.language === 'zh' ? 'en' : 'zh');
};

const checkStatus = async (force = false) => {
  if (isChecking.value) return;
  const now = Date.now();
  if (!force && backendConnected.value !== null && now - lastCheckAt.value < 5000) {
    return;
  }
  isChecking.value = true;
  lastCheckAt.value = now;
  try {
    const response = await fetchWithTimeout(healthUrl, { method: 'GET' }, 2000);
    backendConnected.value = response.ok;
  } catch {
    backendConnected.value = false;
  } finally {
    isChecking.value = false;
  }
};

const openTeachdoSite = () => {
  window.open('https://teachdo.com', '_blank', 'noopener,noreferrer');
};

onMounted(() => {
  checkStatus(true);
});
</script>

<template>
  <header class="h-16 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 fixed top-0 left-0 right-0 z-50 flex items-center">
    <div class="w-full px-4 md:px-6 flex items-center justify-between gap-4">
      <div class="flex items-center gap-4 md:gap-6">
        <button class="flex items-center gap-3 cursor-pointer group" type="button" @click="router.push({ name: 'workspace' })">
          <div class="w-10 h-10 rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700 flex items-center justify-center shadow">
            <BrandLogo class="w-6 h-6 text-indigo-600 dark:text-indigo-400 group-hover:scale-105 transition-transform duration-300" />
          </div>
          <span class="hidden md:inline text-xl font-bold text-slate-900 dark:text-white tracking-tight">TeachDo</span>
        </button>

        <div class="hidden md:flex items-center gap-2 text-sm">
          <span class="text-slate-300 dark:text-slate-600">/</span>
          <span class="font-medium text-slate-700 dark:text-slate-200 truncate max-w-[220px]">
            {{ currentMaterialTitle || t('nav.workspace') }}
          </span>
        </div>
      </div>

      <div class="flex items-center gap-2 md:gap-3">
        <button
          class="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold border transition-all active:scale-95"
          :class="[
            isChecking
              ? 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500'
              : backendConnected === true
                ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400'
                : backendConnected === false
                  ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-600 dark:text-red-400'
                  : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500',
          ]"
          type="button"
          @click="checkStatus(true)"
        >
          <LucideIcon
            v-if="isChecking"
            name="refresh-cw"
            class="w-3 h-3 animate-spin"
            aria-label="checking backend status"
          />
          <LucideIcon
            v-else
            :name="backendConnected ? 'wifi' : backendConnected === false ? 'wifi-off' : 'wifi'"
            class="w-3 h-3"
          />
          <span>
            {{
              isChecking
                ? 'Checking…'
                : backendConnected === null
                  ? 'System'
                  : backendConnected
                    ? 'Online'
                    : 'Offline'
            }}
          </span>
        </button>

        <div class="w-px h-5 bg-slate-200 dark:bg-slate-700 hidden md:block"></div>

        <button
          class="p-2 md:px-3 md:py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          :class="isHome ? 'bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'"
          type="button"
          @click="router.push({ name: 'workspace' })"
        >
          <LucideIcon name="layout-grid" class="w-4 h-4" />
          <span class="hidden lg:inline">{{ t('nav.workspace') }}</span>
        </button>

        <button
          class="p-2 md:px-3 md:py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          :class="isAbout ? 'bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'"
          type="button"
          @click="router.push({ name: 'about' })"
        >
          <LucideIcon name="info" class="w-4 h-4" />
          <span class="hidden lg:inline">{{ t('nav.about') }}</span>
        </button>

        <button
          class="p-2 md:px-3 md:py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          :class="isSettings ? 'bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'"
          type="button"
          @click="router.push({ name: 'settings' })"
        >
          <LucideIcon name="settings" class="w-4 h-4" />
          <span class="hidden lg:inline">{{ t('nav.settings') }}</span>
        </button>

        <button
          class="p-2 md:px-3 md:py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
          type="button"
          @click="openTeachdoSite"
        >
          <LucideIcon name="globe" class="w-4 h-4" />
          <span class="hidden lg:inline">{{ t('nav.website') }}</span>
        </button>

        <div class="w-px h-5 bg-slate-200 dark:bg-slate-700 hidden md:block"></div>

        <button
          class="p-2 rounded-full text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors font-bold text-xs flex items-center justify-center w-9 h-9 border border-transparent hover:border-slate-200 dark:hover:border-slate-700"
          type="button"
          @click="toggleLanguage"
        >
          {{ store.language.toUpperCase() }}
        </button>

        <button
          class="p-2 rounded-full text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          type="button"
          @click="store.toggleTheme()"
        >
          <LucideIcon v-if="store.isDarkMode" name="sun" class="w-5 h-5" />
          <LucideIcon v-else name="moon" class="w-5 h-5" />
        </button>
      </div>
    </div>
  </header>
</template>
