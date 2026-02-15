<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { CourseGroup, CourseUnit } from '#root/types';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';

interface Props {
  currentCourse: CourseGroup;
  currentUnit: CourseUnit | null;
}

interface Emits {
  (e: 'updateUnit', unitId: string, updates: Partial<CourseUnit>): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const loading = ref(false);
const outlineText = ref('');
const newOutlineText = ref('');
const mode = ref<'EDIT' | 'PREVIEW' | 'COMPARE'>('PREVIEW');

// Sync state if unit changes externally
watch(
  () => props.currentUnit,
  (unit) => {
    if (unit && unit.outlineContent !== outlineText.value && mode.value !== 'COMPARE' && mode.value !== 'EDIT') {
      outlineText.value = unit.outlineContent || '';
    }
    // Initial load setup
    if (unit?.id && unit.outlineContent && !outlineText.value) {
      outlineText.value = unit.outlineContent;
    }
  },
  { immediate: true }
);

const handleGenerateWrapper = async () => {
  if (!props.currentUnit) return;

  if (outlineText.value && outlineText.value.trim().length > 0) {
    // --- COMPARE MODE ---
    mode.value = 'COMPARE';
    newOutlineText.value = '';
    loading.value = true;
    try {
      await aiService.generateOutline(props.currentCourse, props.currentUnit, (text) => {
        newOutlineText.value = text;
      });
      toast.success(t('outline.toast.new'));
    } catch (e) {
      console.error(e);
      toast.error(t('outline.toast.error'));
      mode.value = 'PREVIEW'; // Revert
    } finally {
      loading.value = false;
    }
  } else {
    // --- DIRECT GENERATE MODE ---
    loading.value = true;
    mode.value = 'PREVIEW';
    try {
      const finalText = await aiService.generateOutline(props.currentCourse, props.currentUnit, (text) => {
        outlineText.value = text;
      });
      emit('updateUnit', props.currentUnit.id, { outlineContent: finalText });
      vectorizeOutlineToKb(finalText);
      toast.success(t('outline.toast.generated'));
    } catch (e) {
      console.error(e);
      toast.error(t('outline.toast.error'));
    } finally {
      loading.value = false;
    }
  }
};

const vectorizeOutlineToKb = (content: string) => {
  if (!props.currentUnit) return;
  const trimmed = content?.trim();
  if (!trimmed) return;

  void aiService
    .vectorizeTextToKb({
      userId: props.currentCourse.id,
      fileId: `gen:${props.currentCourse.id}:${props.currentUnit.id}:outline`,
      fileName: `大纲-${props.currentUnit.title}`,
      content: trimmed,
      fileType: 'md',
      folderId: 1,
    })
    .catch((e) => console.warn('大纲入库失败（已忽略）', e));
};

const handleConfirmChoice = (choice: 'OLD' | 'NEW') => {
  const finalText = choice === 'NEW' ? newOutlineText.value : outlineText.value;

  outlineText.value = finalText;
  newOutlineText.value = '';
  mode.value = 'PREVIEW';

  // Persist choice
  if (props.currentUnit) {
    emit('updateUnit', props.currentUnit.id, { outlineContent: finalText });
    vectorizeOutlineToKb(finalText);
  }
  toast.info(choice === 'NEW' ? t('outline.replace_new') : t('outline.keep_original'));
};

const handleSave = () => {
  if (props.currentUnit) {
    emit('updateUnit', props.currentUnit.id, { outlineContent: outlineText.value });
    vectorizeOutlineToKb(outlineText.value);
  }
  mode.value = 'PREVIEW';
  toast.success(t('outline.toast.saved'));
};

// Helper to render bold text within lines
const renderInlineStyles = (text: string) => {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return `<strong key="${i}" class="font-bold text-slate-900 dark:text-white bg-indigo-50 dark:bg-indigo-900/30 px-1 rounded mx-0.5">${part.slice(2, -2)}</strong>`;
    }
    return part;
  }).join('');
};

// Enhanced Markdown Renderer
const renderMarkdown = (content: string) => {
  if (!content) return '';

  const lines = content.split('\n');
  return lines.map((line, idx) => {
    if (line.startsWith('# ')) {
      return `<h1 key="${idx}" class="text-2xl md:text-3xl font-bold text-slate-900 dark:text-white mt-8 mb-4 border-b pb-3 border-slate-200 dark:border-slate-700">${line.replace('# ', '')}</h1>`;
    }
    if (line.startsWith('## ')) {
      return `<h2 key="${idx}" class="text-lg md:text-xl font-bold text-indigo-600 dark:text-indigo-400 mt-6 mb-3">${line.replace('## ', '')}</h2>`;
    }
    if (line.startsWith('### ')) {
      return `<h3 key="${idx}" class="text-base md:text-lg font-bold text-slate-700 dark:text-slate-300 mt-4 mb-2">${line.replace('### ', '')}</h3>`;
    }

    if (line.startsWith('- ') || line.startsWith('* ')) {
      const text = line.replace(/^[-*] /, '');
      return `<li key="${idx}" class="ml-4 list-disc marker:text-indigo-400 pl-2">${renderInlineStyles(text)}</li>`;
    }

    if (line.trim() === '') {
      return `<br key="${idx}" />`;
    }

    return `<p key="${idx}" class="">${renderInlineStyles(line)}</p>`;
  }).join('');
};

const markdownHtml = computed(() => renderMarkdown(outlineText.value));
const newMarkdownHtml = computed(() => renderMarkdown(newOutlineText.value));
</script>

<template>
  <div class="h-full flex flex-col gap-6">
    <!-- Toolbar -->
    <div class="flex justify-between items-center bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm sticky top-0 z-10">
      <div class="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
        <button
          :disabled="mode === 'COMPARE'"
          :class="[
            'px-4 py-1.5 rounded-md text-xs font-bold transition-all flex items-center gap-2',
            mode === 'PREVIEW'
              ? 'bg-white dark:bg-slate-700 shadow-sm text-indigo-600 dark:text-white'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white disabled:opacity-50'
          ]"
          @click="mode = 'PREVIEW'"
        >
          <LucideIcon name="eye" :size="12" /> {{ t('outline.preview') }}
        </button>
        <button
          :disabled="mode === 'COMPARE'"
          :class="[
            'px-4 py-1.5 rounded-md text-xs font-bold transition-all flex items-center gap-2',
            mode === 'EDIT'
              ? 'bg-white dark:bg-slate-700 shadow-sm text-indigo-600 dark:text-white'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white disabled:opacity-50'
          ]"
          @click="mode = 'EDIT'"
        >
          <LucideIcon name="edit-3" :size="12" /> {{ t('outline.edit') }}
        </button>
      </div>

      <div class="flex gap-2">
        <div v-if="mode === 'COMPARE'" class="flex items-center gap-2 text-xs font-bold text-indigo-600 bg-indigo-50 dark:bg-indigo-900/30 px-3 py-1.5 rounded-lg animate-pulse">
          <LucideIcon name="arrow-left-right" :size="12" /> {{ t('outline.compare_banner') }}
        </div>
        <template v-else>
          <button
            v-if="outlineText"
            :disabled="loading"
            class="flex items-center gap-2 px-4 py-2 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-lg text-xs font-bold hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-colors"
            @click="handleGenerateWrapper"
          >
            <LucideIcon :name="loading ? 'loader-2' : 'refresh-cw'" :size="12" :class="{ 'animate-spin': loading }" />
            <span>{{ t('outline.regenerate') }}</span>
          </button>
          <button
            v-if="mode === 'EDIT' && currentUnit?.outlineContent !== outlineText"
            class="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg text-xs font-bold shadow-md transition-all"
            @click="handleSave"
          >
            <LucideIcon name="save" :size="12" /> {{ t('outline.save') }}
          </button>
        </template>
      </div>
    </div>

    <!-- Main Content Area -->
    <div :class="['flex-1 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 overflow-hidden relative', mode === 'COMPARE' ? 'bg-slate-100 dark:bg-slate-950' : '']">
      <!-- --- COMPARE MODE --- -->
      <div v-if="mode === 'COMPARE'" class="h-full grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-200 dark:divide-slate-800">
        <!-- Left: Original -->
        <div class="flex flex-col h-full bg-white dark:bg-slate-900">
          <div class="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex justify-between items-center sticky top-0 z-10">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <LucideIcon name="history" :size="16" /> {{ t('outline.current_version') }}
            </span>
          </div>
          <div class="flex-1 overflow-y-auto custom-scrollbar p-6">
            <article class="prose dark:prose-invert prose-sm max-w-none opacity-80">
              <div class="space-y-4 font-serif text-slate-800 dark:text-slate-200 leading-relaxed text-sm md:text-base" v-html="markdownHtml"></div>
            </article>
          </div>
          <div class="p-4 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 sticky bottom-0 z-20">
            <button
              class="w-full py-3 rounded-xl border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 font-bold text-sm hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center justify-center gap-2"
              @click="handleConfirmChoice('OLD')"
            >
              <LucideIcon name="x" :size="16" /> {{ t('outline.keep_original') }}
            </button>
          </div>
        </div>

        <!-- Right: New -->
        <div class="flex flex-col h-full bg-indigo-50/30 dark:bg-indigo-900/10 relative">
          <div class="p-4 border-b border-indigo-100 dark:border-indigo-900/50 bg-indigo-50/50 dark:bg-indigo-900/20 flex justify-between items-center sticky top-0 z-10">
            <span class="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider flex items-center gap-2">
              <LucideIcon :name="loading ? 'loader-2' : 'refresh-cw'" :size="16" :class="{ 'animate-spin': loading }" />
              {{ t('outline.new_version') }}
            </span>
          </div>
          <div class="flex-1 overflow-y-auto custom-scrollbar p-6">
            <article class="prose dark:prose-invert prose-indigo prose-sm max-w-none">
              <div v-if="newOutlineText" class="space-y-4 font-serif text-slate-800 dark:text-slate-200 leading-relaxed text-sm md:text-base" v-html="newMarkdownHtml"></div>
              <div v-else class="h-40 flex items-center justify-center text-indigo-400/50 italic">{{ t('outline.generating_new') }}</div>
            </article>
          </div>
          <div class="p-4 border-t border-indigo-100 dark:border-indigo-900/50 bg-indigo-50/30 dark:bg-indigo-900/20 sticky bottom-0 z-20">
            <button
              :disabled="loading"
              :class="[
                'w-full py-3 rounded-xl font-bold text-sm shadow-lg transition-all flex items-center justify-center gap-2',
                loading
                  ? 'bg-indigo-300 cursor-not-allowed text-white'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white hover:-translate-y-1'
              ]"
              @click="handleConfirmChoice('NEW')"
            >
              <LucideIcon :name="loading ? 'loader-2' : 'check'" :size="16" :class="{ 'animate-spin': loading }" />
              {{ t('outline.replace_new') }}
            </button>
          </div>
        </div>
      </div>

      <!-- --- LOADING SPINNER (For direct generate) --- -->
      <div v-if="mode !== 'COMPARE' && loading && !outlineText" class="absolute inset-0 z-20 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm flex items-center justify-center">
        <div class="flex flex-col items-center gap-3">
          <LucideIcon name="loader-2" :size="40" class="text-indigo-600 animate-spin" />
          <span class="text-sm font-bold text-indigo-600 dark:text-indigo-400">{{ t('outline.crafting') }}</span>
        </div>
      </div>

      <!-- --- PREVIEW MODE --- -->
      <div v-if="mode === 'PREVIEW'" class="h-full overflow-y-auto custom-scrollbar p-8 md:p-12 max-w-4xl mx-auto bg-white dark:bg-slate-900">
        <article class="prose dark:prose-invert prose-indigo max-w-none">
          <div class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-8 border-b border-slate-100 dark:border-slate-800 pb-4">
            {{ t('outline.course_outline_title', { title: currentUnit?.title }) }}
          </div>
          <div v-if="outlineText" class="space-y-4 font-serif text-slate-800 dark:text-slate-200 leading-relaxed text-sm md:text-base" v-html="markdownHtml"></div>
          <div v-else class="flex flex-col items-center justify-center h-96 text-center">
            <div class="w-20 h-20 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 rounded-full flex items-center justify-center mb-6 text-3xl">
              📑
            </div>
            <h3 class="text-xl font-bold text-slate-900 dark:text-white mb-2">{{ t('outline.empty.title') }}</h3>
            <p class="text-slate-500 dark:text-slate-400 max-w-md mb-8">
              {{ t('outline.empty.desc') }}
            </p>
            <button
              class="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-lg shadow-lg hover:shadow-indigo-500/30 transition-all transform hover:-translate-y-0.5"
              @click="handleGenerateWrapper"
            >
              ✨ {{ t('outline.generate_cta') }}
            </button>
          </div>
        </article>
      </div>

      <!-- --- EDIT MODE --- -->
      <textarea
        v-if="mode === 'EDIT'"
        v-model="outlineText"
        class="w-full h-full p-8 md:p-12 bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 font-mono text-sm leading-relaxed resize-none outline-none focus:ring-inset focus:ring-2 focus:ring-indigo-500/10"
        :placeholder="t('outline.placeholder')"
        spellcheck="false"
      />
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.5);
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(71, 85, 105, 0.5);
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(71, 85, 105, 0.7);
}
</style>
