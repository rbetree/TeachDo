import { computed, onMounted, ref, watch, type Ref } from 'vue';
import type { Presentation, PPTTemplate, TeachingMaterial } from '#root/types';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import type { ImgPoolItem } from '@/editor-runtime/aippt/aipptGenerator';
import { buildSlidesMarkdown, mapAipptSlideToPreview } from '@/components/workspace/ppt/pptGenerationUtils';
import { KB_USER_ID, useAppStore } from '@/stores/appStore';

export type PptViewState = 'SELECT_TEMPLATE' | 'PREVIEW';

export interface UsePptGenerationParams {
  currentMaterial: Ref<TeachingMaterial>;
  t: (key: string, params?: Record<string, unknown>) => string;
  emitUpdateMaterial: (updates: Partial<TeachingMaterial>) => void;
}

function sameStringArray(a: string[] | undefined, b: string[] | undefined): boolean {
  const left = Array.isArray(a) ? a : [];
  const right = Array.isArray(b) ? b : [];
  if (left.length !== right.length) return false;
  for (let i = 0; i < left.length; i += 1) {
    if (left[i] !== right[i]) return false;
  }
  return true;
}

export function usePptGeneration(params: UsePptGenerationParams) {
  const store = useAppStore();

  const loading = ref(false);
  const presentation = ref<Presentation | null>(null);
  const templates = ref<PPTTemplate[]>([]);
  const selectedTemplateId = ref('');
  const viewState = ref<PptViewState>('SELECT_TEMPLATE');

  const generateFromWebSearch = ref(true);
  const generateFromUploadedFile = ref(true);
  const selectedKbFileIds = ref<string[]>([]);

  const readyKbFiles = computed(() => (store.kbFiles || []).filter((f) => f.status === 'ready'));
  const readyKbFileCount = computed(() => readyKbFiles.value.length);
  const hasReadyKbFiles = computed(() => readyKbFileCount.value > 0);
  const readyKbIdSet = computed(() => new Set(readyKbFiles.value.map((f) => f.id)));

  const selectedReadyKbFileIds = computed(() =>
    (selectedKbFileIds.value || []).filter((id) => readyKbIdSet.value.has(id)),
  );

  const hasAdvancedOverrides = computed(() => {
    const material = params.currentMaterial.value;
    const kbOverride = !sameStringArray(selectedKbFileIds.value, material.kbFileIds || []);
    return !generateFromWebSearch.value || !generateFromUploadedFile.value || kbOverride;
  });

  watch(
    hasReadyKbFiles,
    (ok) => {
      if (!ok && generateFromUploadedFile.value) {
        generateFromUploadedFile.value = false;
      }
    },
    { immediate: true },
  );

  const selectedTemplate = computed(() => templates.value.find((item) => item.id === selectedTemplateId.value) || null);

  const ensureSelectedTemplate = (list: PPTTemplate[]) => {
    if (!list.length) return;
    const fallback = list[0];
    if (!fallback) return;

    const material = params.currentMaterial.value;
    if (material?.selectedTemplateId) {
      const exists = list.find((item) => item.id === material.selectedTemplateId);
      selectedTemplateId.value = exists ? exists.id : fallback.id;
      return;
    }
    if (!selectedTemplateId.value) {
      selectedTemplateId.value = fallback.id;
    }
  };

  const loadTemplates = async () => {
    const list = await aiService.getTemplates();
    templates.value = list;
    ensureSelectedTemplate(list);
  };

  const syncFromMaterial = (material: TeachingMaterial) => {
    presentation.value = material.presentation || null;
    const hasEditor =
      !!material.editorDocument &&
      Array.isArray(material.editorDocument.slides) &&
      material.editorDocument.slides.length > 0;
    viewState.value = hasEditor || material.presentation ? 'PREVIEW' : 'SELECT_TEMPLATE';
    if (material.selectedTemplateId) {
      selectedTemplateId.value = material.selectedTemplateId;
    }
    selectedKbFileIds.value = Array.isArray(material.kbFileIds) ? [...material.kbFileIds] : [];
  };

  watch(
    () => params.currentMaterial.value.id,
    () => {
      syncFromMaterial(params.currentMaterial.value);
      if (templates.value.length) {
        ensureSelectedTemplate(templates.value);
      }
    },
    { immediate: true },
  );

  const validateKbSelection = (): { ok: boolean; kbFileIds: string[] | null } => {
    if (!generateFromUploadedFile.value) return { ok: true, kbFileIds: null };

    const ids = selectedReadyKbFileIds.value;
    if (ids.length === 0) {
      generateFromUploadedFile.value = false;
      toast.info(params.t('ppt.toast.kb_disabled'));
      return { ok: true, kbFileIds: null };
    }
    return { ok: true, kbFileIds: ids };
  };

  const handleGenerate = async (options: { reason: 'generate' | 'regenerate' }) => {
    const material = params.currentMaterial.value;
    const template = selectedTemplate.value;
    if (!material || !material.outlineContent || !template) return;

    loading.value = true;
    presentation.value = { theme: template.id, slides: [] };
    viewState.value = 'PREVIEW';

    const { kbFileIds } = validateKbSelection();

    // 仅在“重新生成”时把对话框里选中的 KB 文件写回默认
    if (options.reason === 'regenerate') {
      params.emitUpdateMaterial({ kbFileIds: [...selectedKbFileIds.value] });
    }

    try {
      const { createAipptGenerator } = await import('@/editor-runtime/aippt/aipptGenerator');
      const templateData = await aiService.getTemplateFileData(template.id);
      const templateSlides = (templateData?.slides || []) as any[];
      const width = Number(templateData?.width || 960);
      const height = Number(templateData?.height || 540);
      const theme = templateData?.theme;

      const mapper = createAipptGenerator();
      mapper.reset();

      const editorSlides: any[] = [];

      await aiService.streamAipptSlides({
        content: material.outlineContent,
        sessionId: KB_USER_ID,
        language: 'zh',
        generateFromWebSearch: generateFromWebSearch.value,
        generateFromUploadedFile: generateFromUploadedFile.value,
        kbFileIds,
        onSlide: (slide) => {
          if (slide.images?.length) {
            const imgs: ImgPoolItem[] = slide.images.map((img: any) => ({
              id: String(img.id || Math.random().toString(36).slice(2)),
              src: String(img.src),
              width: Number(img.width || 1920),
              height: Number(img.height || 1080),
            }));
            mapper.presetImgPool(imgs);
          }

          const generated = mapper.generateSlides(templateSlides as any, [slide]);
          if (generated.length) editorSlides.push(...generated);

          const preview = mapAipptSlideToPreview(slide);
          if (preview) {
            presentation.value = {
              theme: template.id,
              slides: [...(presentation.value?.slides || []), preview],
            };
          }
        },
      });

      const result: Presentation = presentation.value || { theme: template.id, slides: [] };

      params.emitUpdateMaterial({
        presentation: result,
        selectedTemplateId: selectedTemplateId.value,
        editorDocument: {
          title: material.title,
          templateId: template.id,
          width,
          height,
          theme,
          slides: editorSlides,
          viewport: {
            size: width,
            ratio: width ? height / width : 0.5625,
          },
          updatedAt: Date.now(),
        },
      });

      // 产物入库（失败不阻断）
      const md = buildSlidesMarkdown(material.title, result.slides);
      void aiService
        .vectorizeTextToKb({
          userId: KB_USER_ID,
          fileId: `gen:${KB_USER_ID}:${material.id}:slides`,
          fileName: `幻灯片-${material.title}.md`,
          content: md,
          fileType: 'md',
          folderId: 1,
          createdAt: Date.now(),
          sourceType: 'material',
          sourceMaterialId: material.id,
          sourceMaterialTitle: material.title,
        })
        .catch((e) => console.warn('PPT 产物入库失败（已忽略）', e));

      toast.success(params.t('ppt.toast.generated'));
    } catch (error) {
      console.error(error);
      toast.error(params.t('ppt.toast.error'));
      viewState.value = material.presentation ? 'PREVIEW' : 'SELECT_TEMPLATE';
    } finally {
      loading.value = false;
    }
  };

  onMounted(() => {
    void loadTemplates();
  });

  return {
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
    loadTemplates,
    handleGenerate,
    syncFromMaterial,
  };
}
