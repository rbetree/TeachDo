<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import type { TeachingMaterial } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useWorkspaceUiStore } from '@/stores/workspaceUiStore';
import { useAppStore } from '@/stores/appStore';
import PptAdvancedDialog from '@/components/workspace/ppt/PptAdvancedDialog.vue';
import PptPreviewPanel from '@/components/workspace/ppt/PptPreviewPanel.vue';
import PptTemplateSelector from '@/components/workspace/ppt/PptTemplateSelector.vue';
import { usePptGeneration } from '@/components/workspace/ppt/usePptGeneration';
import KbFilePickerDialog from '@/components/workspace/KbFilePickerDialog.vue';

interface Props {
  currentMaterial: TeachingMaterial;
}

interface Emits {
  (e: 'updateMaterial', updates: Partial<TeachingMaterial>): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();
const router = useRouter();
const ui = useWorkspaceUiStore();
const store = useAppStore();

const currentMaterialRef = toRef(props, 'currentMaterial');

const {
  loading,
  templates,
  selectedTemplateId,
  selectedTemplate,
  presentation,
  viewState,
  hasAdvancedOverrides,
  generateFromWebSearch,
  generateFromUploadedFile,
  selectedKbFileIds,
  readyKbFileCount,
  hasReadyKbFiles,
  handleGenerate,
} = usePptGeneration({
  currentMaterial: currentMaterialRef,
  t,
  emitUpdateMaterial: (updates) => emit('updateMaterial', updates),
});

const hasOutline = computed(() => !!props.currentMaterial?.outlineContent);

const currentSlideIndex = ref(0);

watch(
  () => props.currentMaterial?.id,
  () => {
    currentSlideIndex.value = 0;
  },
);

const advancedOpen = ref(false);
const lastFocusedEl = ref<HTMLElement | null>(null);

const kbPickerOpen = ref(false);
const kbPickerRestoreFocusEl = ref<HTMLElement | null>(null);

const setAdvancedOpen = (value: boolean) => {
  advancedOpen.value = value;
};

const setGenerateFromWebSearch = (value: boolean) => {
  generateFromWebSearch.value = value;
};

const setGenerateFromUploadedFile = (value: boolean) => {
  generateFromUploadedFile.value = value;
};

const openAdvanced = () => {
  lastFocusedEl.value = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  advancedOpen.value = true;
};

const openKbFilePicker = () => {
  kbPickerRestoreFocusEl.value = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  kbPickerOpen.value = true;
};

const handleKbFilePickerConfirm = (ids: string[]) => {
  selectedKbFileIds.value = ids;
};

const goToKnowledgeBase = () => {
  ui.setRightPanelTab('kb');
  advancedOpen.value = false;
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
  await handleGenerate({ reason: 'generate' });
};

const handleRegenerate = async () => {
  currentSlideIndex.value = 0;
  await handleGenerate({ reason: 'regenerate' });
};
</script>

<template>
  <div v-if="!hasOutline" class="flex-1 flex flex-col items-center justify-center text-slate-400 h-full p-8 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-3xl bg-slate-50/50 dark:bg-slate-900/30">
    <div class="w-16 h-16 bg-white dark:bg-slate-800 rounded-2xl shadow-sm flex items-center justify-center mb-4">
      <LucideIcon name="presentation" :size="32" class="opacity-60" />
    </div>
    <h3 class="text-lg font-bold text-slate-700 dark:text-slate-300">{{ t('ppt.need_outline.title') }}</h3>
    <p class="text-sm mt-2 mb-6 max-w-md text-center text-slate-500">{{ t('ppt.need_outline.desc') }}</p>
    <button
      type="button"
      class="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-base shadow-lg hover:shadow-indigo-500/30 transition-all transform hover:-translate-y-0.5 flex items-center gap-2"
      @click="goToOutline"
    >
      <LucideIcon name="layout-list" :size="18" />
      <span>{{ t('ppt.need_outline.cta') }}</span>
    </button>
  </div>

  <div v-else class="h-full flex flex-col gap-6 min-h-0">
    <PptTemplateSelector
      v-if="viewState === 'SELECT_TEMPLATE'"
      v-model:selected-template-id="selectedTemplateId"
      :templates="templates"
      :loading="loading"
      :has-advanced-overrides="hasAdvancedOverrides"
      @open-advanced="openAdvanced"
      @generate="handleGenerateFirst"
    />

    <PptPreviewPanel
      v-else
      v-model:slide-index="currentSlideIndex"
      :loading="loading"
      :has-advanced-overrides="hasAdvancedOverrides"
      :presentation="presentation"
      :selected-template="selectedTemplate"
      :editor-document="props.currentMaterial?.editorDocument ?? null"
      @open-advanced="openAdvanced"
      @go-to-editor="goToEditor"
      @change-template="goToTemplateSelect"
      @regenerate="handleRegenerate"
    />

    <PptAdvancedDialog
      :open="advancedOpen"
      :loading="loading"
      :has-ready-kb-files="hasReadyKbFiles"
      :ready-kb-file-count="readyKbFileCount"
      :selected-kb-file-count="selectedKbFileIds.length"
      :generate-from-web-search="generateFromWebSearch"
      :generate-from-uploaded-file="generateFromUploadedFile"
      :restore-focus-el="lastFocusedEl"
      @update:open="setAdvancedOpen"
      @update:generate-from-web-search="setGenerateFromWebSearch"
      @update:generate-from-uploaded-file="setGenerateFromUploadedFile"
      @open-kb-file-picker="openKbFilePicker"
      @go-to-knowledge-base="goToKnowledgeBase"
    />

    <KbFilePickerDialog
      :open="kbPickerOpen"
      :files="store.kbFiles"
      :selected-ids="selectedKbFileIds"
      :restore-focus-el="kbPickerRestoreFocusEl"
      @update:open="(v) => (kbPickerOpen = v)"
      @confirm="handleKbFilePickerConfirm"
    />
  </div>
</template>
