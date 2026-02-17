import { computed, onMounted, ref, watch, type Ref } from 'vue';
import type { CourseGroup, CourseUnit, Presentation, PPTTemplate } from '#root/types';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import type { ImgPoolItem } from '@/editor-runtime/aippt/aipptGenerator';
import { buildSlidesMarkdown, mapAipptSlideToPreview } from '@/components/workspace/ppt/pptGenerationUtils';

export type PptViewState = 'SELECT_TEMPLATE' | 'PREVIEW';

export interface UsePptGenerationParams {
  currentCourse: Ref<CourseGroup>;
  currentUnit: Ref<CourseUnit | null>;
  t: (key: string, params?: Record<string, unknown>) => string;
  emitUpdateUnit: (unitId: string, updates: Partial<CourseUnit>) => void;
}

export function usePptGeneration(params: UsePptGenerationParams) {
  const loading = ref(false);
  const presentation = ref<Presentation | null>(null);
  const templates = ref<PPTTemplate[]>([]);
  const selectedTemplateId = ref('');
  const viewState = ref<PptViewState>('SELECT_TEMPLATE');

  const generateFromWebSearch = ref(true);
  const generateFromUploadedFile = ref(true);
  const includeGeneratedKb = ref(false);

  const hasAdvancedOverrides = computed(
    () => !generateFromWebSearch.value || !generateFromUploadedFile.value || includeGeneratedKb.value,
  );

  const kbFolderIds = computed<number[]>(() => (includeGeneratedKb.value ? [0, 1] : [0]));
  const readyKbFileCount = computed(() => {
    const allowed = new Set(kbFolderIds.value);
    const list = params.currentCourse.value.kbFiles || [];
    return list.filter((f) => f.status === 'ready' && allowed.has(typeof f.folderId === 'number' ? f.folderId : 0)).length;
  });
  const hasReadyKbFiles = computed(() => readyKbFileCount.value > 0);

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

    const unit = params.currentUnit.value;
    if (unit?.selectedTemplateId) {
      const exists = list.find((item) => item.id === unit.selectedTemplateId);
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

  const syncFromUnit = (unit: CourseUnit | null) => {
    presentation.value = unit?.presentation || null;
    const hasEditor = !!unit?.editorDocument && Array.isArray(unit.editorDocument.slides) && unit.editorDocument.slides.length > 0;
    viewState.value = hasEditor || unit?.presentation ? 'PREVIEW' : 'SELECT_TEMPLATE';
    if (unit?.selectedTemplateId) {
      selectedTemplateId.value = unit.selectedTemplateId;
    }
  };

  watch(
    () => params.currentUnit.value,
    (unit) => {
      syncFromUnit(unit);
      if (templates.value.length) {
        ensureSelectedTemplate(templates.value);
      }
    },
    { immediate: true },
  );

  const handleGenerate = async () => {
    const unit = params.currentUnit.value;
    const template = selectedTemplate.value;
    if (!unit || !unit.outlineContent || !template) return;

    loading.value = true;
    presentation.value = { theme: template.id, slides: [] };
    viewState.value = 'PREVIEW';

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
        content: unit.outlineContent,
        sessionId: params.currentCourse.value.id,
        language: 'zh',
        generateFromWebSearch: generateFromWebSearch.value,
        generateFromUploadedFile: generateFromUploadedFile.value,
        kbFolderIds: generateFromUploadedFile.value ? kbFolderIds.value : null,
        onSlide: (slide) => {
          // 后端可能返回图片池（用于模板图片槽位填充）
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

      params.emitUpdateUnit(unit.id, {
        presentation: result,
        selectedTemplateId: selectedTemplateId.value,
        editorDocument: {
          title: unit.title,
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
      const md = buildSlidesMarkdown(unit.title, result.slides);
      void aiService
        .vectorizeTextToKb({
          userId: params.currentCourse.value.id,
          fileId: `gen:${params.currentCourse.value.id}:${unit.id}:slides`,
          fileName: `幻灯片-${unit.title}.md`,
          content: md,
          fileType: 'md',
          folderId: 1,
        })
        .catch((e) => console.warn('PPT 产物入库失败（已忽略）', e));

      toast.success(params.t('ppt.toast.generated'));
    } catch (error) {
      console.error(error);
      toast.error(params.t('ppt.toast.error'));
      viewState.value = unit.presentation ? 'PREVIEW' : 'SELECT_TEMPLATE';
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
    includeGeneratedKb,
    kbFolderIds,
    readyKbFileCount,
    hasReadyKbFiles,
    loadTemplates,
    handleGenerate,
    syncFromUnit,
  };
}
