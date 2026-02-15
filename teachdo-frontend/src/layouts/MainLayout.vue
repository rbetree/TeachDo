<script setup lang="ts">
import { RouterView } from 'vue-router';
import AppTopBar from '@/components/layout/AppTopBar.vue';
</script>

<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-sans">
    <AppTopBar />
    <main class="pt-16">
      <RouterView />
    </main>
  </div>
</template>
