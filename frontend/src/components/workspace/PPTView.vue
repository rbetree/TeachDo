<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import type { TeachingMaterial } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useWorkspaceUiStore } from '@/stores/workspaceUiStore';
import PptPreviewPanel from '@/components/workspace/ppt/PptPreviewPanel.vue';
import PptTemplateSelector from '@/components/workspace/ppt/PptTemplateSelector.vue';
import { usePptGeneration } from '@/components/workspace/ppt/usePptGeneration';

interface Props {
  currentMaterial: TeachingMaterial;
  headerActionHost?: HTMLElement | null;
}

interface Emits {
  (e: 'updateMaterial', updates: Partial<TeachingMaterial>): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();
const router = useRouter();
const ui = useWorkspaceUiStore();

const currentMaterialRef = toRef(props, 'currentMaterial');

const {
  loading,
  templates,
  selectedTemplateId,
  selectedTemplate,
  presentation,
  viewState,
  generateFromWebSearch,
  selectedKbFileIds,
  handleGenerate,
  cancelGenerate,
  generationCanceled,
  draftPreviewActive,
  discardDraftPreview,
} = usePptGeneration({
  currentMaterial: currentMaterialRef,
  t,
  emitUpdateMaterial: (updates) => emit('updateMaterial', updates),
});

const hasOutline = computed(() => !!props.currentMaterial?.outlineContent);
const hasExternalToolbar = computed(() => !!props.headerActionHost);
const previewSlideCount = computed(() => {
  if (draftPreviewActive.value) return presentation.value?.slides?.length || 0;
  const editorSlides = props.currentMaterial?.editorDocument?.slides;
  if (Array.isArray(editorSlides) && editorSlides.length > 0) return editorSlides.length;
  return presentation.value?.slides?.length || 0;
});

const showEditButton = computed(() => !!props.currentMaterial?.editorDocument && !draftPreviewActive.value);

const currentSlideIndex = ref(0);

watch(
  () => props.currentMaterial?.id,
  () => {
    currentSlideIndex.value = 0;
  },
);

const goToKnowledgeBase = () => {
  ui.setRightPanelTab('kb');
};

const goToOutline = () => {
  router.push({ name: 'material-tab', params: { materialId: props.currentMaterial.id, tab: 'outline' } });
};

const goToEditor = () => {
  router.push({
    name: 'material-ppt-editor',
    params: { materialId: props.currentMaterial.id },
  });
};

const goToTemplateSelect = () => {
  viewState.value = 'SELECT_TEMPLATE';
};

const handleGenerateFirst = async () => {
  currentSlideIndex.value = 0;
  await handleGenerate();
};

const handleRegenerate = async () => {
  currentSlideIndex.value = 0;
  await handleGenerate();
};
</script>

<template>
  <div v-if="!hasOutline" class="h-full flex flex-col min-h-0">
    <div class="workspace-card flex-1 min-h-0 p-4 md:p-6">
      <div class="h-full w-full flex flex-col items-center justify-center text-slate-400 p-8 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-3xl bg-slate-50/50 dark:bg-slate-900/30">
        <div class="w-16 h-16 bg-white dark:bg-slate-800 rounded-2xl shadow-sm flex items-center justify-center mb-4">
          <LucideIcon name="presentation" :size="32" class="opacity-60" />
        </div>
        <h3 class="text-lg font-bold text-slate-700 dark:text-slate-300">{{ t('ppt.need_outline.title') }}</h3>
        <p class="text-sm mt-2 mb-6 max-w-md text-center text-slate-500">{{ t('ppt.need_outline.desc') }}</p>
        <button
          type="button"
          class="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-base shadow-lg hover:shadow-indigo-500/30 transition-colors transition-shadow transition-transform transform hover:-translate-y-0.5 flex items-center gap-2"
          @click="goToOutline"
        >
          <LucideIcon name="layout-list" :size="18" />
          <span>{{ t('ppt.need_outline.cta') }}</span>
        </button>
      </div>
    </div>
  </div>

  <div v-else class="h-full flex flex-col min-h-0" :class="hasExternalToolbar ? 'gap-0' : 'gap-6'">
    <Teleport :to="props.headerActionHost || 'body'" :disabled="!hasExternalToolbar">
      <div
        class="flex items-center justify-between gap-2"
        :class="hasExternalToolbar
          ? 'w-full h-full'
          : 'bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm min-h-[44px]'"
      >
        <div class="flex items-center gap-2 min-w-0 overflow-x-auto no-scrollbar">
          <div class="toolbar-cluster shrink-0">
            <span class="toolbar-item text-slate-600 dark:text-slate-300">
              <LucideIcon :name="viewState === 'SELECT_TEMPLATE' ? 'layout-list' : 'presentation'" class="w-4 h-4" />
              <span>{{ viewState === 'SELECT_TEMPLATE' ? t('ppt.choose_template') : t('ppt.preview_title') }}</span>
            </span>
          </div>
          <span
            v-if="viewState !== 'SELECT_TEMPLATE'"
            class="toolbar-item text-slate-500 dark:text-slate-400"
          >
            {{ t('ppt.slides_generated', { count: previewSlideCount }) }}
          </span>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <button
            v-if="loading"
            type="button"
            class="toolbar-item bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-800/40 hover:bg-red-100 dark:hover:bg-red-900/30"
            @click="cancelGenerate"
          >
            <LucideIcon name="x" class="w-4 h-4" />
            <span>{{ t('common.cancel') }}</span>
          </button>
          <label
            class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 cursor-pointer select-none disabled:opacity-60"
            :class="loading ? 'opacity-60 cursor-not-allowed' : ''"
          >
            <input
              v-model="generateFromWebSearch"
              type="checkbox"
              class="h-4 w-4 accent-indigo-600 disabled:opacity-50"
              :disabled="loading"
            />
            <span>{{ t('ppt.advanced.web_search') }}</span>
          </label>

          <button
            type="button"
            class="toolbar-item border transition-colors"
            :class="selectedKbFileIds.length
              ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-200 hover:bg-indigo-100 dark:hover:bg-indigo-900/30'
              : 'bg-white dark:bg-slate-700 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600'"
            :title="t('ppt.advanced.manage_kb_files')"
            :aria-label="t('ppt.advanced.manage_kb_files')"
            @click="goToKnowledgeBase"
          >
            <LucideIcon name="database" class="w-4 h-4" />
            <span>{{ t('ppt.toolbar.kb_refs', { count: selectedKbFileIds.length }) }}</span>
          </button>

          <template v-if="viewState === 'SELECT_TEMPLATE'">
            <button
              type="button"
              :disabled="loading || !templates.length"
              class="toolbar-item bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-300 disabled:text-slate-500"
              @click="handleGenerateFirst"
            >
              <LucideIcon :name="loading ? 'loader-2' : 'sparkles'" class="w-4 h-4" :class="loading ? 'animate-spin' : ''" />
              <span>{{ loading ? t('ppt.generating') : t('ppt.generate') }}</span>
            </button>
          </template>

          <template v-else>
            <button
              v-if="showEditButton"
              type="button"
              :disabled="loading"
              class="toolbar-item bg-emerald-600 hover:bg-emerald-700 text-white disabled:bg-slate-300 disabled:text-slate-500"
              @click="goToEditor"
            >
              <LucideIcon name="edit-3" class="w-4 h-4" />
              <span>{{ t('ppt.edit') }}</span>
            </button>
            <button
              type="button"
              :disabled="loading"
              class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 disabled:opacity-60"
              @click="goToTemplateSelect"
            >
              {{ t('ppt.change_template') }}
            </button>
            <button
              type="button"
              :disabled="loading"
              class="toolbar-item bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-300 disabled:text-slate-500"
              @click="handleRegenerate"
            >
              <LucideIcon :name="loading ? 'loader-2' : 'refresh-cw'" class="w-4 h-4" :class="loading ? 'animate-spin' : ''" />
              <span>{{ loading ? t('ppt.generating') : t('ppt.regenerate') }}</span>
            </button>
          </template>
        </div>
      </div>
    </Teleport>

    <div :class="['workspace-card flex-1 min-h-0 flex flex-col', hasExternalToolbar ? 'mt-4' : '']">
      <div class="flex-1 min-h-0 p-4 md:p-6 flex flex-col">
        <div
          v-if="generationCanceled && draftPreviewActive && viewState !== 'SELECT_TEMPLATE' && previewSlideCount > 0"
          class="mb-4 rounded-2xl border border-amber-200 dark:border-amber-800/40 bg-amber-50/70 dark:bg-amber-900/10 p-4 flex flex-col md:flex-row md:items-center justify-between gap-3"
          role="status"
          aria-live="polite"
        >
          <div class="min-w-0">
            <div class="text-sm font-bold text-amber-900 dark:text-amber-100">
              {{ t('ppt.banner.canceled.title') }}
            </div>
            <div class="text-xs text-amber-800/80 dark:text-amber-200/90 mt-0.5">
              {{ t('ppt.banner.canceled.desc', { count: previewSlideCount }) }}
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button
              type="button"
              class="px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs transition-colors"
              @click="handleRegenerate"
            >
              {{ t('ppt.regenerate') }}
            </button>
            <button
              v-if="props.currentMaterial?.editorDocument"
              type="button"
              class="px-3 py-2 rounded-xl border border-amber-200 dark:border-amber-800/40 bg-white/70 dark:bg-slate-900/30 text-amber-900 dark:text-amber-100 font-bold text-xs hover:bg-white dark:hover:bg-slate-900 transition-colors"
              @click="discardDraftPreview"
            >
              {{ t('ppt.banner.canceled.back_to_saved') }}
            </button>
          </div>
        </div>

        <PptTemplateSelector
          v-if="viewState === 'SELECT_TEMPLATE'"
          v-model:selected-template-id="selectedTemplateId"
          class="flex-1 min-h-0"
          :templates="templates"
          :loading="loading"
          :external-toolbar="hasExternalToolbar"
          @generate="handleGenerateFirst"
        />

        <PptPreviewPanel
          v-else
          v-model:slide-index="currentSlideIndex"
          class="flex-1 min-h-0"
          :loading="loading"
          :presentation="presentation"
          :selected-template="selectedTemplate"
          :editor-document="draftPreviewActive ? null : (props.currentMaterial?.editorDocument ?? null)"
          :external-toolbar="hasExternalToolbar"
          @go-to-editor="goToEditor"
          @change-template="goToTemplateSelect"
          @regenerate="handleRegenerate"
        />
      </div>
    </div>
  </div>
</template>
