import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue';
import type { EditorDocument, Presentation, PPTTemplate, TeachingMaterial } from '#root/types';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import type { ImgPoolItem } from '@/editor-runtime/aippt/aipptGenerator';
import { buildSlidesMarkdown, mapAipptSlideToPreview } from '@/components/workspace/ppt/pptGenerationUtils';
import { KB_USER_ID, useAppStore } from '@/stores/appStore';
import { ApiError } from '@/services/apiClient';
import { isFullTextKbFileId } from '@/utils/kbFileId';
import { buildGenOutputFileId, formatVersionLabel, sanitizeFilenameSegment } from '@/utils/genOutputFileId';
import { buildSimpleTextPptxBlob, PPTX_MIME } from '@/utils/simplePptxExport';

export type PptViewState = 'SELECT_TEMPLATE' | 'PREVIEW';

export interface UsePptGenerationParams {
  currentMaterial: Ref<TeachingMaterial>;
  t: (key: string, params?: Record<string, unknown>) => string;
  emitUpdateMaterial: (updates: Partial<TeachingMaterial>) => void;
}

export function usePptGeneration(params: UsePptGenerationParams) {
  const store = useAppStore();
  const loading = ref(false);
  const presentation = ref<Presentation | null>(null);
  const templates = ref<PPTTemplate[]>([]);
  const selectedTemplateId = ref('');
  const viewState = ref<PptViewState>('SELECT_TEMPLATE');
  const pendingController = ref<AbortController | null>(null);
  const generationCanceled = ref(false);
  const draftPreviewActive = ref(false);
  const draftEditorDocument = ref<EditorDocument | null>(null);

  const generateFromWebSearch = ref(true);
  const generateWithImages = ref(false);
  const pexelsCapabilityLoading = ref(true);
  const pexelsKeyConfigured = ref(false);
  const selectedKbFileIds = ref<string[]>([]);

  const kbFileIdsForRequest = computed(() => {
    const ids = Array.isArray(selectedKbFileIds.value) ? selectedKbFileIds.value : [];
    const normalized = ids.map((id) => id.trim()).filter(Boolean);
    const unique = Array.from(new Set(normalized));
    // 大纲本身已通过 outlineContent 传入生成请求；若再勾选 gen:*:outline 会造成上下文重复注入。
    const outlineFileId = `gen:${KB_USER_ID}:${params.currentMaterial.value.id}:outline`;
    return unique.filter((id) => id !== outlineFileId);
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

  const loadPptCapabilities = async () => {
    pexelsCapabilityLoading.value = true;
    try {
      const caps = await aiService.getPptCapabilities();
      pexelsKeyConfigured.value = Boolean(caps?.pexelsKeyConfigured);
    } catch {
      pexelsKeyConfigured.value = false;
    } finally {
      pexelsCapabilityLoading.value = false;
    }

    // 不支持联网配图时强制关闭，避免“隐藏开关但仍发送 generateWithImages=true”。
    if (!pexelsKeyConfigured.value) {
      generateWithImages.value = false;
    }
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
      pendingController.value?.abort();
      pendingController.value = null;
      loading.value = false;
      generationCanceled.value = false;
      draftPreviewActive.value = false;
      draftEditorDocument.value = null;
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

    generationCanceled.value = false;
    draftPreviewActive.value = true;
    draftEditorDocument.value = null;
    pendingController.value?.abort();
    const controller = new AbortController();
    pendingController.value = controller;

    loading.value = true;
    presentation.value = { theme: template.id, slides: [] };
    viewState.value = 'PREVIEW';

    const kbFileIds = kbFileIdsForRequest.value;
    const ragKbFileIds = kbFileIds.filter((id) => !isFullTextKbFileId(id));
    const useKb = ragKbFileIds.length > 0;

    let width = 960;
    let height = 540;
    let theme: any = undefined;

    try {
      const { createAipptGenerator } = await import('@/editor-runtime/aippt/aipptGenerator');
      const templateData = await aiService.getTemplateFileData(template.id);
      const templateSlides = (templateData?.slides || []) as any[];
      width = Number(templateData?.width || 960);
      height = Number(templateData?.height || 540);
      theme = templateData?.theme;

      draftEditorDocument.value = {
        title: material.title,
        templateId: template.id,
        width,
        height,
        theme,
        slides: [],
        viewport: {
          size: width,
          ratio: width ? height / width : 0.5625,
        },
        updatedAt: Date.now(),
      };

      const mapper = createAipptGenerator();
      mapper.reset();

      await aiService.streamPptSlides({
        content: material.outlineContent,
        sessionId: KB_USER_ID,
        language: 'zh',
        generateFromWebSearch: generateFromWebSearch.value,
        generateFromUploadedFile: useKb,
        generateWithImages: generateWithImages.value,
        kbFileIds: kbFileIds.length > 0 ? kbFileIds : null,
        signal: controller.signal,
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
          if (generated.length && draftEditorDocument.value) {
            draftEditorDocument.value.slides.push(...generated);
            draftEditorDocument.value.updatedAt = Date.now();
          }

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
      const editorDocSlides = (draftEditorDocument.value?.slides || []) as any[];

      params.emitUpdateMaterial({
        presentation: result,
        selectedTemplateId: selectedTemplateId.value,
        editorDocument: {
          title: material.title,
          templateId: template.id,
          width,
          height,
          theme,
          slides: editorDocSlides,
          viewport: {
            size: width,
            ratio: width ? height / width : 0.5625,
          },
          updatedAt: Date.now(),
        },
      });

      // 产物入库（失败不阻断）
      const nowMs = Date.now();
      const fileId = buildGenOutputFileId({ userId: KB_USER_ID, materialId: material.id, kind: 'slides', nowMs });
      const titleBase = sanitizeFilenameSegment(material.title || material.id) || material.id;
      const version = formatVersionLabel(nowMs) || String(nowMs);
      const fileName = `幻灯片-${titleBase}-${version}.md`;
      const md = buildSlidesMarkdown(material.title, result.slides);

      // 自动生成并入库 PPTX 源文件（文本简化版，失败不阻断）
      void (async () => {
        try {
          const blob = await buildSimpleTextPptxBlob({ title: material.title || material.id, slides: result.slides || [] });
          const pptxFileName = `幻灯片-${titleBase}-${version}.pptx`;
          const file = new File([blob], pptxFileName, { type: PPTX_MIME });
          await aiService.uploadArtifact({ userId: KB_USER_ID, materialId: material.id, kind: 'pptx', file });
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('teachdo:artifacts-updated', { detail: { materialId: material.id } }));
          }
        } catch (e) {
          console.warn('PPTX 源文件入库失败（已忽略）', e);
        }
      })();

      void aiService
        .vectorizeTextToKb({
          userId: KB_USER_ID,
          fileId,
          fileName,
          content: md,
          fileType: 'md',
          folderId: 1,
          createdAt: nowMs,
          sourceType: 'material',
          sourceMaterialId: material.id,
          sourceMaterialTitle: material.title,
        })
        .then(() => {
          const next = (store.kbFiles || []).filter((f) => f.id !== fileId);
          next.unshift({
            id: fileId,
            name: fileName,
            size: md.length,
            type: 'md',
            status: 'ready',
            uploadedAt: new Date(nowMs),
            folderId: 1,
            sourceType: 'material',
            sourceMaterialId: material.id,
            sourceMaterialTitle: material.title,
          });
          store.setKbFiles(next);
        })
        .catch((e) => console.warn('PPT 产物入库失败（已忽略）', e));

      toast.success(params.t('ppt.toast.generated'));
      draftPreviewActive.value = false;
      draftEditorDocument.value = null;
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'abort') {
        generationCanceled.value = true;

        const result: Presentation = presentation.value || { theme: template.id, slides: [] };
        const hasAnySlides = (draftEditorDocument.value?.slides?.length || 0) > 0 || (result.slides || []).length > 0;

        if (hasAnySlides) {
          toast.info(params.t('ppt.toast.canceled'));
        } else {
          draftPreviewActive.value = false;
          draftEditorDocument.value = null;
          presentation.value = material.presentation || null;
          viewState.value = material.presentation ? 'PREVIEW' : 'SELECT_TEMPLATE';
          toast.info(params.t('ppt.toast.canceled_empty'));
        }
        return;
      }

      console.error(error);
      toast.error(params.t('ppt.toast.error'));
      draftPreviewActive.value = false;
      draftEditorDocument.value = null;
      presentation.value = material.presentation || null;
      viewState.value = material.presentation ? 'PREVIEW' : 'SELECT_TEMPLATE';
    } finally {
      loading.value = false;
      pendingController.value = null;
    }
  };

  const cancelGenerate = () => pendingController.value?.abort();

  const discardDraftPreview = () => {
    generationCanceled.value = false;
    draftPreviewActive.value = false;
    draftEditorDocument.value = null;
    // 恢复为已持久化的结果（如存在），否则回到模板选择
    syncFromMaterial(params.currentMaterial.value);
  };

  onMounted(() => {
    void loadTemplates();
    void loadPptCapabilities();
  });

  onBeforeUnmount(() => {
    pendingController.value?.abort();
  });

  return {
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
    selectedKbFileIds,
    loadTemplates,
    handleGenerate,
    cancelGenerate,
    generationCanceled,
    draftPreviewActive,
    draftEditorDocument,
    discardDraftPreview,
    syncFromMaterial,
  };
}
