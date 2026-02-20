<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import BrandLogo from '@/components/common/BrandLogo.vue';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useAppStore } from '@/stores/appStore';
import type { TeachingMaterial } from '#root/types';
import TeachingMaterialCreateDialog from '@/components/workspace/TeachingMaterialCreateDialog.vue';

const store = useAppStore();
const { t } = useI18n();
const router = useRouter();

const materials = computed(() => store.materials);
const createOpen = ref(false);
const query = ref('');

type SortMode = 'recent' | 'title' | 'subject';
const sortMode = ref<SortMode>('recent');

const normalizedQuery = computed(() => query.value.trim().toLowerCase());

const filteredMaterials = computed(() => {
  const q = normalizedQuery.value;
  if (!q) return [...materials.value];
  return materials.value.filter((material) => {
    const haystack = `${material.title} ${material.subject} ${material.description} ${material.objectives}`.toLowerCase();
    return haystack.includes(q);
  });
});

const sortedMaterials = computed(() => {
  const list = [...filteredMaterials.value];
  if (sortMode.value === 'title') {
    list.sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: 'base' }));
    return list;
  }
  if (sortMode.value === 'subject') {
    list.sort((a, b) => {
      const subjectCompare = a.subject.localeCompare(b.subject, undefined, { sensitivity: 'base' });
      if (subjectCompare !== 0) return subjectCompare;
      return a.title.localeCompare(b.title, undefined, { sensitivity: 'base' });
    });
    return list;
  }
  list.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  return list;
});

const locale = computed(() => (store.language === 'zh' ? 'zh-CN' : 'en'));
const dateFormatter = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }),
);

const formatDate = (value: unknown): string => {
  try {
    const date = value instanceof Date ? value : new Date(value as any);
    if (Number.isNaN(date.getTime())) return '';
    return dateFormatter.value.format(date);
  } catch {
    return '';
  }
};

const getProgress = (material: TeachingMaterial): { done: number; outline: boolean; lesson: boolean; ppt: boolean } => {
  const outline = !!material.outlineContent && material.outlineContent.trim().length > 0;
  const lesson = !!material.lessonPlan;
  const ppt =
    !!material.presentation ||
    (!!material.editorDocument && Array.isArray(material.editorDocument.slides) && material.editorDocument.slides.length > 0);
  const done = [outline, lesson, ppt].filter(Boolean).length;
  return { done, outline, lesson, ppt };
};

const clearSearch = () => {
  query.value = '';
};

const handleCreate = (material: TeachingMaterial) => {
  store.upsertMaterial(material);
  createOpen.value = false;
  router.push({ name: 'material', params: { materialId: material.id } });
};
</script>

<template>
  <section class="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-slate-50 dark:bg-slate-900 transition-colors duration-300 font-sans">
    <div class="absolute inset-0 opacity-40 pointer-events-none bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] dark:bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:20px_20px]"></div>

    <div class="relative z-10 mx-auto max-w-6xl px-6 md:px-10 py-8 md:py-10">
      <header class="flex items-center">
        <div class="flex items-center gap-4 min-w-0">
          <div class="w-12 h-12 rounded-2xl bg-indigo-600 dark:bg-slate-800 flex items-center justify-center shadow-lg shadow-indigo-500/20 dark:shadow-none">
            <BrandLogo class="w-7 h-7 text-white dark:text-indigo-400" />
          </div>
          <div class="min-w-0">
            <h1 class="text-4xl md:text-5xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Teach<span class="text-indigo-600 dark:text-indigo-400">Do</span>
            </h1>
          </div>
        </div>
      </header>

      <div class="mt-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div class="relative w-full md:max-w-md">
          <LucideIcon name="search" class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 dark:text-slate-500" />
          <input
            v-model="query"
            type="text"
            :placeholder="t('material.list.search_placeholder')"
            class="w-full pl-11 pr-11 py-3 rounded-2xl bg-white/80 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            :aria-label="t('material.list.search_placeholder')"
          />
          <button
            v-if="normalizedQuery"
            type="button"
            class="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-200 hover:bg-slate-100/70 dark:hover:bg-slate-700/40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            :aria-label="t('material.list.clear_search')"
            @click="clearSearch"
          >
            <LucideIcon name="x" class="w-4 h-4" />
          </button>
        </div>

        <div class="flex items-center gap-2">
          <div class="flex p-1 rounded-xl bg-slate-200/60 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 shadow-sm">
            <button
              type="button"
              class="px-3 py-2 rounded-lg text-sm font-bold transition-colors"
              :class="sortMode === 'recent' ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-300' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-100'"
              @click="sortMode = 'recent'"
            >
              {{ t('material.list.sort.recent') }}
            </button>
            <button
              type="button"
              class="px-3 py-2 rounded-lg text-sm font-bold transition-colors"
              :class="sortMode === 'title' ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-300' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-100'"
              @click="sortMode = 'title'"
            >
              {{ t('material.list.sort.title') }}
            </button>
            <button
              type="button"
              class="px-3 py-2 rounded-lg text-sm font-bold transition-colors"
              :class="sortMode === 'subject' ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-300' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-100'"
              @click="sortMode = 'subject'"
            >
              {{ t('material.list.sort.subject') }}
            </button>
          </div>
        </div>
      </div>

      <div class="mt-4 flex items-center justify-between text-sm text-slate-500 dark:text-slate-400">
        <span>{{ t('material.list.count', { count: sortedMaterials.length }) }}</span>
      </div>

      <div class="mt-4">
        <div v-if="sortedMaterials.length" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
	          <RouterLink
	            v-for="material in sortedMaterials"
	            :key="material.id"
	            :to="{ name: 'material', params: { materialId: material.id } }"
	            class="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-2xl hover:-translate-y-1 transition-colors transition-transform transition-shadow duration-300 flex flex-col h-60 overflow-hidden group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 dark:focus-visible:ring-offset-slate-900"
	          >
            <div class="p-7 flex flex-col h-full gap-4">
              <div class="flex items-start justify-between gap-4">
                <span class="text-[11px] font-bold uppercase tracking-widest px-2 py-1 rounded bg-slate-100 dark:bg-slate-700/40 text-slate-500 dark:text-slate-400">
                  {{ material.subject }}
                </span>
                <span class="text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap">
                  {{ t('material.card.created_at', { date: formatDate(material.createdAt) }) }}
                </span>
              </div>

              <div class="flex items-start justify-between gap-4">
                <h3 class="text-xl font-bold text-slate-900 dark:text-white line-clamp-2 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                  {{ material.title }}
                </h3>
                <LucideIcon
                  name="book-open"
                  class="w-5 h-5 text-slate-300 dark:text-slate-600 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors shrink-0 mt-1"
                />
              </div>

              <p class="text-sm text-slate-500 dark:text-slate-400 line-clamp-2 flex-1">
                {{ material.description || t('material.card.description_fallback') }}
              </p>

              <div class="pt-4 border-t border-slate-100 dark:border-slate-700/50 flex items-center justify-between text-xs">
                <div class="flex items-center gap-2 text-slate-400 dark:text-slate-500">
                  <div class="flex items-center gap-1.5">
                    <LucideIcon name="layout-list" class="w-4 h-4" :class="getProgress(material).outline ? 'text-indigo-600 dark:text-indigo-300' : ''" />
                    <LucideIcon name="file-text" class="w-4 h-4" :class="getProgress(material).lesson ? 'text-indigo-600 dark:text-indigo-300' : ''" />
                    <LucideIcon name="presentation" class="w-4 h-4" :class="getProgress(material).ppt ? 'text-indigo-600 dark:text-indigo-300' : ''" />
                  </div>
                  <span class="font-semibold">
                    {{ t('material.card.progress', { done: getProgress(material).done }) }}
                  </span>
                </div>
	                <div class="flex items-center gap-1 font-bold text-indigo-600 dark:text-indigo-400 opacity-0 group-hover:opacity-100 translate-x-2 group-hover:translate-x-0 transition-opacity transition-transform duration-200">
	                  {{ t('material.card.open') }}
	                  <LucideIcon name="arrow-right" class="w-3 h-3" />
	                </div>
              </div>
            </div>
          </RouterLink>

	          <button
	            type="button"
	            class="flex flex-col items-center justify-center p-8 h-60 rounded-3xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-800/40 hover:border-indigo-500 dark:hover:border-indigo-500 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/20 transition-colors group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 dark:focus-visible:ring-offset-slate-900"
	            @click="createOpen = true"
	          >
            <div class="w-16 h-16 rounded-full border border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 group-hover:scale-110 transition">
              <LucideIcon name="plus" class="w-8 h-8" />
            </div>
            <p class="mt-4 text-lg font-bold text-slate-600 dark:text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
              {{ t('material.list.create') }}
            </p>
          </button>
        </div>

        <div
          v-else
          class="rounded-3xl border border-dashed border-slate-300 dark:border-slate-700 p-10 text-center space-y-4 text-slate-500 dark:text-slate-400 bg-white/40 dark:bg-slate-800/30"
        >
          <p>{{ normalizedQuery ? t('material.list.empty_search') : t('material.list.empty') }}</p>
          <div class="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              v-if="normalizedQuery"
              type="button"
              class="px-5 py-3 rounded-2xl bg-white/80 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 font-semibold hover:bg-white dark:hover:bg-slate-800 transition-colors"
              @click="clearSearch"
            >
              {{ t('material.list.clear_search') }}
            </button>
            <button
              type="button"
              class="px-5 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold transition-colors"
              @click="createOpen = true"
            >
              {{ t('material.list.create') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>

  <TeachingMaterialCreateDialog
    :open="createOpen"
    @update:open="(v) => (createOpen = v)"
    @create="handleCreate"
  />
</template>
