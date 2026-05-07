<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import type { TeachingMaterial } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import ToolbarMoreMenu from '@/components/common/ToolbarMoreMenu.vue';
import WorkspaceNeedOutlineState from '@/components/workspace/WorkspaceNeedOutlineState.vue';
import PptPreviewPanel from '@/components/workspace/ppt/PptPreviewPanel.vue';
import PptTemplateSelector from '@/components/workspace/ppt/PptTemplateSelector.vue';
import { usePptGeneration } from '@/components/workspace/ppt/usePptGeneration';
import { prefetchEditorRuntimePluginModules } from '@/utils/editorRuntime';

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

const currentMaterialRef = toRef(props, 'currentMaterial');

const {
  loading,
  templates,
  selectedTemplateId,
  selectedTemplate,
  presentation,
  viewState,
  generateFromWebSearch,
  generateWithImages,
  pexelsCapabilityLoading,
  pexelsKeyConfigured,
  handleGenerate,
  cancelGenerate,
  generationCanceled,
  draftPreviewActive,
  draftEditorDocument,
  discardDraftPreview,
} = usePptGeneration({
  currentMaterial: currentMaterialRef,
  t,
  emitUpdateMaterial: (updates) => emit('updateMaterial', updates),
});

const hasOutline = computed(() => !!props.currentMaterial?.outlineContent);
const hasExternalToolbar = computed(() => !!props.headerActionHost);
const imagesToggleBlocked = computed(() => pexelsCapabilityLoading.value || !pexelsKeyConfigured.value);
const imagesToggleDisabled = computed(() => loading.value || imagesToggleBlocked.value);
const imagesToggleTitle = computed(() => {
  if (pexelsCapabilityLoading.value) return t('ppt.advanced.images_checking');
  if (!pexelsKeyConfigured.value) return t('ppt.advanced.images_need_key');
  return t('ppt.advanced.images_desc');
});
const previewSlideCount = computed(() => {
  if (draftPreviewActive.value) {
    const slides = draftEditorDocument.value?.slides;
    if (Array.isArray(slides) && slides.length > 0) return slides.length;
    return presentation.value?.slides?.length || 0;
  }
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

const goToOutline = () => {
  router.push({ name: 'material-tab', params: { materialId: props.currentMaterial.id, tab: 'outline' } });
};

const goToEditor = () => {
  router.push({
    name: 'material-ppt-editor',
    params: { materialId: props.currentMaterial.id },
  });
};

const goToSettings = () => {
  router.push({ name: 'settings' });
};

let editorShellPrefetchPromise: Promise<unknown> | null = null;
let editorRuntimePrefetchPromise: Promise<unknown> | null = null;
let runtimePrefetchScheduled = false;

const scheduleRuntimePrefetch = () => {
  if (editorRuntimePrefetchPromise || runtimePrefetchScheduled) return;
  runtimePrefetchScheduled = true;

  const ric = (window as any).requestIdleCallback as undefined | ((cb: () => void, opts?: { timeout: number }) => number);
  if (typeof ric === 'function') {
    ric(
      () => {
        void prefetchEditorRuntimePluginModules();
        editorRuntimePrefetchPromise = import('@/views/pptEditor/PPTEditorRuntime.vue').catch(() => null);
      },
      { timeout: 1500 },
    );
    return;
  }

  window.setTimeout(() => {
    void prefetchEditorRuntimePluginModules();
    editorRuntimePrefetchPromise = import('@/views/pptEditor/PPTEditorRuntime.vue').catch(() => null);
  }, 800);
};

const prefetchPptEditor = (input: { eagerRuntime?: boolean } = {}) => {
  if (!editorShellPrefetchPromise) {
    // 预热路由壳：让“点击后跳转”更快发生（即使运行时仍需加载）。
    editorShellPrefetchPromise = import('@/views/PPTEditorView.vue').catch(() => null);
  }

  if (input.eagerRuntime) {
    if (!editorRuntimePrefetchPromise) {
      editorRuntimePrefetchPromise = import('@/views/pptEditor/PPTEditorRuntime.vue').catch(() => null);
    }
    void prefetchEditorRuntimePluginModules();
    return;
  }

  scheduleRuntimePrefetch();
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
    <WorkspaceNeedOutlineState
      icon="presentation"
      cta-icon="layout-list"
      :title="t('ppt.need_outline.title')"
      :description="t('ppt.need_outline.desc')"
      :cta-label="t('ppt.need_outline.cta')"
      @cta="goToOutline"
    />
  </div>

  <div v-else class="h-full flex flex-col min-h-0" :class="hasExternalToolbar ? 'gap-0' : 'gap-6'">
    <Teleport :to="props.headerActionHost || 'body'" :disabled="!hasExternalToolbar">
      <div
        class="flex min-w-0 items-center justify-between gap-2"
        :class="hasExternalToolbar
          ? 'w-full'
          : 'bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm min-h-[44px]'"
      >
        <div class="hidden 2xl:flex items-center gap-2 shrink-0">
          <div class="toolbar-cluster">
            <span class="toolbar-item text-slate-600 dark:text-slate-300">
              <LucideIcon :name="viewState === 'SELECT_TEMPLATE' ? 'layout-list' : 'presentation'" class="w-4 h-4" />
              <span>{{ viewState === 'SELECT_TEMPLATE' ? t('ppt.choose_template') : t('ppt.preview_title') }}</span>
            </span>
          </div>
        </div>

        <div class="flex min-w-0 shrink-0 items-center justify-end gap-2">
          <button
            v-if="loading"
            type="button"
            class="toolbar-item shrink-0 px-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-800/40 hover:bg-red-100 dark:hover:bg-red-900/30"
            @click="cancelGenerate"
          >
            <LucideIcon name="x" class="w-4 h-4" />
            <span>{{ t('common.cancel') }}</span>
          </button>

          <div class="flex min-w-0 items-center justify-end gap-2">
            <template v-if="viewState === 'SELECT_TEMPLATE'">
              <button
                type="button"
                :disabled="loading || !templates.length"
                class="toolbar-item shrink-0 px-3 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-300 disabled:text-slate-500"
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
                class="toolbar-item shrink-0 px-3 bg-emerald-600 hover:bg-emerald-700 text-white disabled:bg-slate-300 disabled:text-slate-500"
                @mouseenter="prefetchPptEditor()"
                @focus="prefetchPptEditor()"
                @touchstart.passive="prefetchPptEditor({ eagerRuntime: true })"
                @click="goToEditor"
              >
                <LucideIcon name="edit-3" class="w-4 h-4" />
                <span>{{ t('ppt.edit') }}</span>
              </button>
              <button
                type="button"
                :disabled="loading"
                class="toolbar-item shrink-0 px-3 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-300 disabled:text-slate-500"
                @click="handleRegenerate"
              >
                <LucideIcon :name="loading ? 'loader-2' : 'refresh-cw'" class="w-4 h-4" :class="loading ? 'animate-spin' : ''" />
                <span>{{ loading ? t('ppt.generating') : t('ppt.regenerate') }}</span>
              </button>
            </template>
          </div>

          <ToolbarMoreMenu :label="t('common.more')">
            <template #default="{ close }">
              <label
                class="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700/70"
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
              <label
                class="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700/70"
                :class="imagesToggleDisabled ? 'opacity-60 cursor-not-allowed' : ''"
                :title="imagesToggleTitle"
              >
                <input
                  v-model="generateWithImages"
                  type="checkbox"
                  class="h-4 w-4 accent-indigo-600 disabled:opacity-50"
                  :disabled="imagesToggleDisabled"
                />
                <span>{{ t('ppt.advanced.images') }}</span>
              </label>
              <button
                v-if="imagesToggleBlocked"
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-bold text-indigo-600 hover:bg-indigo-50 dark:text-indigo-300 dark:hover:bg-slate-700/70"
                @click="() => { close(); goToSettings(); }"
              >
                <LucideIcon name="settings" class="w-4 h-4" />
                <span>{{ t('ppt.advanced.images_setup') }}</span>
              </button>
              <button
                v-if="viewState !== 'SELECT_TEMPLATE'"
                type="button"
                :disabled="loading"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-bold text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700/70 disabled:opacity-50"
                @click="() => { close(); goToTemplateSelect(); }"
              >
                <LucideIcon name="layout-list" class="w-4 h-4" />
                <span>{{ t('ppt.change_template') }}</span>
              </button>
            </template>
          </ToolbarMoreMenu>
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
          :editor-document="draftPreviewActive ? draftEditorDocument : (props.currentMaterial?.editorDocument ?? null)"
          :external-toolbar="hasExternalToolbar"
          @go-to-editor="goToEditor"
          @change-template="goToTemplateSelect"
          @regenerate="handleRegenerate"
        />
      </div>
    </div>
  </div>
</template>
