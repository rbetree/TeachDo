import { computed, onMounted, ref, watch, type Ref } from 'vue';
import type { Presentation, PPTTemplate, TeachingMaterial } from '#root/types';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import type { ImgPoolItem } from '@/editor-runtime/aippt/aipptGenerator';
import { buildSlidesMarkdown, mapAipptSlideToPreview } from '@/components/workspace/ppt/pptGenerationUtils';
import { KB_USER_ID } from '@/stores/appStore';

export type PptViewState = 'SELECT_TEMPLATE' | 'PREVIEW';

export interface UsePptGenerationParams {
  currentMaterial: Ref<TeachingMaterial>;
  t: (key: string, params?: Record<string, unknown>) => string;
  emitUpdateMaterial: (updates: Partial<TeachingMaterial>) => void;
}

export function usePptGeneration(params: UsePptGenerationParams) {
  const loading = ref(false);
  const presentation = ref<Presentation | null>(null);
  const templates = ref<PPTTemplate[]>([]);
  const selectedTemplateId = ref('');
  const viewState = ref<PptViewState>('SELECT_TEMPLATE');

  const generateFromWebSearch = ref(true);
  const selectedKbFileIds = ref<string[]>([]);

  const kbFileIdsForRequest = computed(() => {
    const ids = Array.isArray(selectedKbFileIds.value) ? selectedKbFileIds.value : [];
    const normalized = ids.map((id) => id.trim()).filter(Boolean);
    return Array.from(new Set(normalized));
  });

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

  watch(
    () => params.currentMaterial.value.kbFileIds,
    (ids) => {
      selectedKbFileIds.value = Array.isArray(ids) ? [...ids] : [];
    },
    { immediate: true },
  );

  const handleGenerate = async () => {
    const material = params.currentMaterial.value;
    const template = selectedTemplate.value;
    if (!material || !material.outlineContent || !template) return;

    loading.value = true;
    presentation.value = { theme: template.id, slides: [] };
    viewState.value = 'PREVIEW';

    const kbFileIds = kbFileIdsForRequest.value;
    const useKb = kbFileIds.length > 0;

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
        generateFromUploadedFile: useKb,
        kbFileIds: useKb ? kbFileIds : null,
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
    generateFromWebSearch,
    selectedKbFileIds,
    loadTemplates,
    handleGenerate,
    syncFromMaterial,
  };
}
