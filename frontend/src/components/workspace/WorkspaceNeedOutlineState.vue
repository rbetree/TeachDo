<script setup lang="ts">
import LucideIcon from '@/components/common/LucideIcon.vue';
import type { IconName } from '@/components/common/LucideIcon.vue';

interface Props {
  icon: IconName;
  title: string;
  description: string;
  ctaLabel: string;
  ctaIcon?: IconName;
}

interface Emits {
  (e: 'cta'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
</script>

<template>
  <div class="workspace-card flex-1 min-h-0 p-4 md:p-6">
    <div
      class="h-full w-full flex flex-col items-center justify-center text-slate-400 p-8 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-3xl bg-slate-50/50 dark:bg-slate-950/35"
    >
      <div class="w-16 h-16 bg-white dark:bg-slate-800 rounded-2xl shadow-sm flex items-center justify-center mb-4">
        <LucideIcon :name="props.icon" :size="32" class="opacity-60" />
      </div>
      <h3 class="text-lg font-bold text-slate-700 dark:text-slate-300">{{ props.title }}</h3>
      <p class="text-sm mt-2 mb-6 max-w-md text-center text-slate-500">
        {{ props.description }}
      </p>
      <button
        type="button"
        class="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-base shadow-lg hover:shadow-indigo-500/30 transition-colors transition-shadow transition-transform transform hover:-translate-y-0.5 flex items-center gap-2"
        @click="emit('cta')"
      >
        <LucideIcon v-if="props.ctaIcon" :name="props.ctaIcon" :size="18" />
        <span>{{ props.ctaLabel }}</span>
      </button>
    </div>
  </div>
</template>

