<script setup lang="ts">
/* global setTimeout, clearTimeout */
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import BrandLogo from '@/components/common/BrandLogo.vue';
import Skeleton from '@/components/common/Skeleton.vue';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useAppStore } from '@/stores/appStore';
import type { CourseGroup } from '#root/types';

const router = useRouter();
const store = useAppStore();
  const { t } = useI18n();

const courses = computed(() => store.courses);
const isCreating = ref(false);
const isLoading = ref(true);
const newCourse = reactive({
  name: '',
  subject: '',
  description: '',
});

let loadingTimer: ReturnType<typeof setTimeout> | null = null;

onMounted(() => {
  loadingTimer = setTimeout(() => {
    isLoading.value = false;
  }, 800);
});

onBeforeUnmount(() => {
  if (loadingTimer) {
    clearTimeout(loadingTimer);
  }
});

const titlePrefix = computed(() => {
  const [prefix] = t('app.name').split('|');
  return prefix?.trim() || 'TeachDo ';
});

const creationDisabled = computed(() => !newCourse.name.trim() || !newCourse.subject.trim());

const handleCreateCourse = () => {
  if (creationDisabled.value) return;
  const course: CourseGroup = {
    id: `course-${Date.now()}`,
    name: newCourse.name.trim(),
    subject: newCourse.subject.trim(),
    description: newCourse.description.trim() || t('course.card.description_fallback'),
    createdAt: new Date(),
    units: [],
    kbFiles: [],
  };
  store.upsertCourse(course);
  Object.assign(newCourse, { name: '', subject: '', description: '' });
  isCreating.value = false;
};

const handleEnterWorkspace = (courseId: string) => {
  router.push({ name: 'course', params: { courseId } });
};
</script>

<template>
  <section class="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-slate-50 dark:bg-slate-900 transition-colors duration-300 font-sans">
    <div class="absolute inset-0 opacity-40 pointer-events-none bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] dark:bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:20px_20px]"></div>

    <div class="relative z-10 p-6 md:p-10 flex flex-col items-center gap-12">
      <header class="max-w-4xl w-full text-center space-y-6 mt-8 animate-fade-in">
        <div class="flex justify-center">
          <div class="w-24 h-24 rounded-[28px] bg-indigo-600 dark:bg-slate-800 flex items-center justify-center shadow-xl shadow-indigo-500/20 dark:shadow-none group transition-transform duration-500 hover:scale-105">
            <BrandLogo class="w-14 h-14 text-white dark:text-indigo-400 transition-transform duration-500 group-hover:scale-110" />
          </div>
        </div>
        <h1 class="text-5xl md:text-6xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          {{ titlePrefix }}
          <span class="text-indigo-600 dark:text-indigo-400">AI</span>
        </h1>
        <p class="text-xl text-slate-500 dark:text-slate-400 max-w-2xl mx-auto leading-relaxed">
          {{ t('course.my_courses') }}
        </p>
      </header>

      <div class="max-w-6xl w-full">
        <div v-if="isCreating" class="max-w-xl mx-auto bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-2xl p-8 space-y-6 animate-slide-in">
          <div class="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-white">
            <div class="w-9 h-9 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <LucideIcon name="plus" class="w-5 h-5" />
            </div>
            {{ t('course.create') }}
          </div>
          <div class="space-y-4">
            <label class="space-y-2 text-left">
              <span class="block text-xs font-bold uppercase tracking-widest text-slate-500">
                {{ t('course.form.name_label') }}
              </span>
              <input
                v-model="newCourse.name"
                type="text"
                class="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-4 py-3 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                :placeholder="t('course.form.name_placeholder')"
              />
            </label>
            <label class="space-y-2 text-left">
              <span class="block text-xs font-bold uppercase tracking-widest text-slate-500">
                {{ t('course.form.subject_label') }}
              </span>
              <input
                v-model="newCourse.subject"
                type="text"
                class="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-4 py-3 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                :placeholder="t('course.form.subject_placeholder')"
              />
            </label>
            <label class="space-y-2 text-left">
              <span class="block text-xs font-bold uppercase tracking-widest text-slate-500">
                {{ t('course.form.description_label') }}
              </span>
              <textarea
                v-model="newCourse.description"
                rows="4"
                class="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-4 py-3 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 custom-scrollbar"
                :placeholder="t('course.form.description_placeholder')"
              />
            </label>
          </div>
          <div class="flex gap-3 pt-2">
            <button
              type="button"
              class="flex-1 rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-3 text-sm font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              @click="isCreating = false"
            >
              {{ t('course.form.cancel') }}
            </button>
            <button
              type="button"
              class="flex-1 rounded-xl px-4 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-500/30 transition-all"
              :class="creationDisabled ? 'bg-slate-300 dark:bg-slate-700 cursor-not-allowed shadow-none' : 'bg-indigo-600 hover:bg-indigo-700 hover:scale-[1.01]'"
              :disabled="creationDisabled"
              @click="handleCreateCourse"
            >
              {{ t('course.form.start') }}
            </button>
          </div>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
          <template v-if="isLoading">
            <div
              v-for="skeleton in 3"
              :key="skeleton"
              class="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 p-7 h-56 flex flex-col gap-4"
            >
              <div class="flex items-start justify-between">
                <Skeleton class="w-16 h-6" />
                <Skeleton variant="circle" class="w-8 h-8" />
              </div>
              <Skeleton class="w-3/4 h-8" />
              <Skeleton class="w-full h-4" />
              <Skeleton class="w-2/3 h-4" />
              <div class="mt-auto pt-4 border-t border-slate-100 dark:border-slate-700/50">
                <Skeleton class="w-20 h-4" />
              </div>
            </div>
          </template>

          <template v-else>
            <article
              v-for="course in courses"
              :key="course.id"
              class="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 cursor-pointer flex flex-col h-56 overflow-hidden group"
              @click="handleEnterWorkspace(course.id)"
            >
              <div class="p-7 flex flex-col h-full gap-4">
                <div class="flex items-start justify-between">
                  <span class="text-[11px] font-bold uppercase tracking-widest px-2 py-1 rounded bg-slate-100 dark:bg-slate-700/40 text-slate-500 dark:text-slate-400">
                    {{ course.subject }}
                  </span>
                  <LucideIcon name="book-open" class="w-5 h-5 text-slate-300 dark:text-slate-600 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors" />
                </div>
                <h3 class="text-xl font-bold text-slate-900 dark:text-white line-clamp-2 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                  {{ course.name }}
                </h3>
                <p class="text-sm text-slate-500 dark:text-slate-400 line-clamp-2 flex-1">
                  {{ course.description || t('course.card.description_fallback') }}
                </p>
                <div class="pt-4 border-t border-slate-100 dark:border-slate-700/50 flex items-center justify-between text-xs">
                  <div class="flex items-center gap-1.5 text-slate-400">
                    <LucideIcon name="layers" class="w-3.5 h-3.5" />
                    <span class="font-semibold">{{ course.units.length }} {{ t('course.card.units_label') }}</span>
                  </div>
                  <div class="flex items-center gap-1 font-bold text-indigo-600 dark:text-indigo-400 opacity-0 group-hover:opacity-100 translate-x-2 group-hover:translate-x-0 transition-all">
                    {{ t('course.card.enter') }}
                    <LucideIcon name="arrow-right" class="w-3 h-3" />
                  </div>
                </div>
              </div>
            </article>

            <div
              v-if="!courses.length"
              class="col-span-full rounded-3xl border border-dashed border-slate-300 dark:border-slate-700 p-8 text-center space-y-4 text-slate-500 dark:text-slate-400"
            >
              <p>{{ t('course.no_courses') }}</p>
              <button
                type="button"
                class="px-5 py-3 rounded-2xl bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300 font-semibold hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-colors"
                @click="isCreating = true"
              >
                {{ t('course.create') }}
              </button>
            </div>
          </template>

          <button
            v-if="!isLoading"
            type="button"
            class="flex flex-col items-center justify-center p-8 h-56 rounded-3xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-800/40 hover:border-indigo-500 dark:hover:border-indigo-500 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/20 transition-all group"
            @click="isCreating = true"
          >
            <div class="w-16 h-16 rounded-full border border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 group-hover:scale-110 transition">
              <LucideIcon name="plus" class="w-8 h-8" />
            </div>
            <p class="mt-4 text-lg font-bold text-slate-600 dark:text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
              {{ t('course.create') }}
            </p>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
