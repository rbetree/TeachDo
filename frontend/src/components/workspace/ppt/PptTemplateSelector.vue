<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import type { PPTTemplate } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';

interface Props {
  templates: PPTTemplate[];
  selectedTemplateId: string;
  loading: boolean;
  externalToolbar?: boolean;
}

interface Emits {
  (e: 'update:selectedTemplateId', value: string): void;
  (e: 'generate'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const selectTemplate = (id: string) => {
  emit('update:selectedTemplateId', id);
};
</script>

<template>
  <div class="flex-1 flex flex-col min-h-0">
    <div v-if="!props.externalToolbar" class="mb-6">
      <div class="min-w-0">
        <h2 class="text-2xl font-bold text-slate-900 dark:text-white">{{ t('ppt.choose_template') }}</h2>
        <p class="text-slate-500 dark:text-slate-400">{{ t('ppt.select_hint') }}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" :class="props.externalToolbar ? 'mb-0' : 'mb-8'">
      <button
        v-for="template in props.templates"
        :key="template.id"
        type="button"
        :disabled="props.loading"
	        :aria-pressed="props.selectedTemplateId === template.id"
	        :class="[
	          'group relative rounded-xl overflow-hidden border-2 transition-colors transition-transform duration-200 text-left disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 focus-visible:outline-offset-2',
	          props.selectedTemplateId === template.id ? 'border-indigo-500 ring-4 ring-indigo-500/20 scale-105' : 'border-slate-200 dark:border-slate-800 hover:border-indigo-300',
	        ]"
	        @click="selectTemplate(template.id)"
	      >
	        <div v-if="template.coverUrl" class="h-32 w-full bg-slate-100 overflow-hidden">
	          <img
	            :src="template.coverUrl"
	            width="640"
	            height="256"
	            loading="lazy"
	            decoding="async"
	            class="h-full w-full object-cover group-hover:scale-110 transition-transform duration-500"
	            :alt="template.name"
	          />
	        </div>
        <div v-else :class="['h-32 w-full flex items-center justify-center', template.thumbnailColor]">
          <span class="text-white font-bold opacity-80 text-lg">Aa</span>
        </div>
        <div class="p-4 bg-white dark:bg-slate-900">
          <h3 class="font-bold text-slate-800 dark:text-white">{{ template.name }}</h3>
          <p class="text-xs text-slate-500 mt-1">{{ template.styleDescription }}</p>
        </div>
        <div v-if="props.selectedTemplateId === template.id" class="absolute top-2 right-2 bg-indigo-500 text-white rounded-full p-1 shadow-lg">
          <LucideIcon name="check" :size="16" />
        </div>
      </button>
    </div>

	    <div v-if="!props.externalToolbar" class="flex justify-center">
	      <button
	        :disabled="props.loading || !props.templates.length"
	        class="px-10 py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:text-slate-500 text-white rounded-2xl font-bold text-lg shadow-xl shadow-indigo-500/30 transition-colors flex items-center gap-3"
	        @click="emit('generate')"
	      >
        <LucideIcon :name="props.loading ? 'loader-2' : 'sparkles'" :size="20" :class="props.loading ? 'animate-spin' : ''" />
        <span>{{ props.loading ? t('ppt.generating') : t('ppt.generate') }}</span>
      </button>
    </div>
  </div>
</template>
