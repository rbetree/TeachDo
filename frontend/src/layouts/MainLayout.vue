<script setup lang="ts">
import { RouterView } from 'vue-router';
import { useI18n } from 'vue-i18n';
import AppTopBar from '@/components/layout/AppTopBar.vue';

const { t } = useI18n();
</script>

<template>
  <div class="min-h-screen bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans">
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60] focus:px-4 focus:py-2 focus:rounded-xl focus:bg-white focus:text-slate-900 focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:bg-slate-900 dark:focus:text-slate-100"
    >
      {{ t('a11y.skip_to_main') }}
    </a>
    <AppTopBar />
    <main id="main-content" class="pt-16" tabindex="-1">
      <RouterView />
    </main>
  </div>
</template>
