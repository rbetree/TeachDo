<script setup lang="ts">
import LucideIcon from '@/components/common/LucideIcon.vue';
import type { IconName } from '@/components/common/LucideIcon.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const highlights: { titleKey: string; descKey: string; icon: IconName }[] = [
  { titleKey: 'about.highlight.1.title', descKey: 'about.highlight.1.desc', icon: 'sparkles' },
  { titleKey: 'about.highlight.2.title', descKey: 'about.highlight.2.desc', icon: 'layers' },
  { titleKey: 'about.highlight.3.title', descKey: 'about.highlight.3.desc', icon: 'database' },
  { titleKey: 'about.highlight.4.title', descKey: 'about.highlight.4.desc', icon: 'code' },
];

const steps = [
  { titleKey: 'about.steps.1.title', itemKeys: ['about.steps.1.item1', 'about.steps.1.item2', 'about.steps.1.item3'] },
  { titleKey: 'about.steps.2.title', itemKeys: ['about.steps.2.item1', 'about.steps.2.item2', 'about.steps.2.item3'] },
  { titleKey: 'about.steps.3.title', itemKeys: ['about.steps.3.item1', 'about.steps.3.item2', 'about.steps.3.item3'] },
];

const experienceKeys = ['about.experience.1', 'about.experience.2', 'about.experience.3', 'about.experience.4'];
</script>

<template>
  <section class="min-h-[calc(100vh-4rem)] bg-slate-100 dark:bg-slate-950">
    <div class="mx-auto max-w-6xl px-6 md:px-10 py-8 md:py-10 space-y-10 animate-fade-in">
      <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <p class="text-sm uppercase tracking-widest text-indigo-500 font-bold">{{ t('about.title') }}</p>
          <h1 class="text-3xl md:text-4xl font-extrabold text-slate-900 dark:text-white mt-2 flex items-center gap-2">
            <LucideIcon name="layers" :size="28" class="text-indigo-600" />
            {{ t('about.title') }}
          </h1>
          <p class="text-slate-600 dark:text-slate-400 mt-2">
            {{ t('about.subtitle') }}
          </p>
        </div>
        <div class="flex gap-3">
          <div class="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-300 text-sm font-bold flex items-center gap-2">
            <LucideIcon name="globe" :size="16" /> {{ t('about.repo.placeholder') }}
          </div>
        </div>
      </header>

      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="item in highlights"
          :key="item.titleKey"
          class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm flex items-start gap-3"
        >
          <div class="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300">
            <LucideIcon :name="item.icon" :size="18" />
          </div>
          <div>
            <h3 class="text-lg font-bold text-slate-800 dark:text-white">{{ t(item.titleKey) }}</h3>
            <p class="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">{{ t(item.descKey) }}</p>
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-2">
          <LucideIcon name="book-open" :size="18" class="text-indigo-600" />
          <h2 class="text-xl font-bold text-slate-900 dark:text-white">{{ t('about.steps.title') }}</h2>
        </div>
        <div class="grid md:grid-cols-3 gap-4">
          <div
            v-for="step in steps"
            :key="step.titleKey"
            class="bg-slate-50 dark:bg-slate-800/60 rounded-xl p-4 border border-slate-200 dark:border-slate-700"
          >
            <h4 class="text-sm font-bold text-slate-800 dark:text-white mb-2">{{ t(step.titleKey) }}</h4>
            <ul class="text-sm text-slate-600 dark:text-slate-400 space-y-1.5">
              <li v-for="textKey in step.itemKeys" :key="textKey" class="flex items-start gap-2">
                <span class="mt-0.5 text-indigo-500">•</span>
                <span>{{ t(textKey) }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
        <div class="flex items-center gap-2 mb-4">
          <LucideIcon name="activity" :size="18" class="text-indigo-600" />
          <h3 class="text-lg font-bold text-slate-900 dark:text-white">{{ t('about.experience.title') }}</h3>
        </div>
        <ul class="grid md:grid-cols-2 gap-3 text-sm text-slate-600 dark:text-slate-400">
          <li v-for="key in experienceKeys" :key="key" class="flex items-start gap-2">
            <span class="mt-0.5 text-indigo-500">•</span>
            <span>{{ t(key) }}</span>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
