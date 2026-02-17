<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import type { CourseGroup, CourseUnit, Presentation, PPTTemplate } from '#root/types';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';
import type { AIPPTSlide } from '@/editor-runtime/types/AIPPT';
import type { ImgPoolItem } from '@/editor-runtime/aippt/aipptGenerator';
import { useWorkspaceUiStore } from '@/stores/workspaceUiStore';

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
const router = useRouter();
const ui = useWorkspaceUiStore();

const ThumbnailSlide = defineAsyncComponent(() => import('@editor/views/components/ThumbnailSlide/index.vue'));

const loading = ref(false);
const presentation = ref<Presentation | null>(null);
const currentSlideIndex = ref(0);
const templates = ref<PPTTemplate[]>([]);
const selectedTemplateId = ref('');
const viewState = ref<'SELECT_TEMPLATE' | 'PREVIEW'>('SELECT_TEMPLATE');

const hasOutline = computed(() => !!props.currentUnit?.outlineContent);
const selectedTemplate = computed(() => templates.value.find((item) => item.id === selectedTemplateId.value) || null);
const slides = computed(() => presentation.value?.slides ?? []);
const currentSlide = computed(() => slides.value[currentSlideIndex.value]);

const editorPreviewReady = ref(false);
const editorSlidesStoreLoaded = ref(false);
let editorSlidesStoreInstance: any | null = null;
let editorSlidesStoreLoading: Promise<any> | null = null;

const ensureEditorSlidesStore = async () => {
  if (editorSlidesStoreInstance) return editorSlidesStoreInstance;
  if (editorSlidesStoreLoading) return editorSlidesStoreLoading;

  editorSlidesStoreLoading = (async () => {
    const mod = await import('@editor/store');
    editorSlidesStoreInstance = mod.useSlidesStore();
    editorSlidesStoreLoaded.value = true;
    return editorSlidesStoreInstance;
  })();

  try {
    return await editorSlidesStoreLoading;
  } finally {
    editorSlidesStoreLoading = null;
  }
};

const editorDocument = computed(() => props.currentUnit?.editorDocument ?? null);
const editorSlides = computed<any[]>(() => (editorDocument.value?.slides ?? []) as any[]);
const hasEditorSlides = computed(() => editorSlides.value.length > 0);
const currentEditorSlide = computed<any | null>(() => editorSlides.value[currentSlideIndex.value] ?? null);

const previewCanvasRef = ref<HTMLElement | null>(null);
const previewCanvasWidth = ref(0);
const previewCanvasHeight = ref(0);
const thumbnailListRef = ref<HTMLElement | null>(null);
const thumbnailSize = ref(200);
let previewResizeObserver: ResizeObserver | null = null;
let thumbnailResizeObserver: ResizeObserver | null = null;

const mainSlideSize = computed(() => {
  const doc = editorDocument.value;
  const ratioRaw = Number(doc?.viewport?.ratio || (doc?.width && doc?.height ? doc.height / doc.width : 0.5625));
  const ratio = ratioRaw && Number.isFinite(ratioRaw) ? ratioRaw : 0.5625;

  const width = previewCanvasWidth.value || 960;
  const height = previewCanvasHeight.value || Math.round(width * ratio);

  // 预留像素，避免 1px 溢出导致横向滚动条
  const safePadding = 8;
  const maxByWidth = Math.max(0, Math.floor(width - safePadding));
  const maxByHeight = ratio ? Math.max(0, Math.floor(height / ratio - safePadding)) : maxByWidth;

  return Math.max(0, Math.floor(Math.min(1400, maxByWidth, maxByHeight)));
});

const extractTextFromHtml = (html: string): string => {
  try {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return (doc.body.textContent || '').replace(/\s+/g, ' ').trim();
  } catch {
    return String(html || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
  }
};

const getEditorSlideTitle = (slide: any): string => {
  if (!slide || !Array.isArray(slide.elements)) return t('ppt.untitled');

  const candidates: { priority: number; text: string }[] = [];
  for (const el of slide.elements) {
    if (el?.type === 'text' && typeof el?.content === 'string') {
      const text = extractTextFromHtml(el.content);
      if (!text) continue;
      const priority = el.textType === 'title' ? 0 : el.textType === 'subtitle' ? 1 : 2;
      candidates.push({ priority, text });
      continue;
    }
    if (el?.type === 'shape' && typeof el?.text?.content === 'string') {
      const text = extractTextFromHtml(el.text.content);
      if (!text) continue;
      const priority = el.text.type === 'title' ? 0 : el.text.type === 'subtitle' ? 1 : 2;
      candidates.push({ priority, text });
    }
  }

  if (!candidates.length) return t('ppt.untitled');
  candidates.sort((a, b) => a.priority - b.priority);
  return candidates[0]!.text;
};

const editorSlideTitles = computed(() => editorSlides.value.map((s) => getEditorSlideTitle(s)));

const previewSlideCount = computed(() => (hasEditorSlides.value ? editorSlides.value.length : slides.value.length));

const advancedOpen = ref(false);
const generateFromWebSearch = ref(true);
const generateFromUploadedFile = ref(true);
const includeGeneratedKb = ref(false);
const advancedDialogRef = ref<HTMLElement | null>(null);
const lastFocusedEl = ref<HTMLElement | null>(null);

const hasAdvancedOverrides = computed(
  () => !generateFromWebSearch.value || !generateFromUploadedFile.value || includeGeneratedKb.value,
);

watch(
  editorDocument,
  async (doc) => {
    editorPreviewReady.value = false;
    if (!doc) return;
    const width = Number(doc.width || doc.viewport?.size || 960);
    const ratio = Number(doc.viewport?.ratio || (doc.width && doc.height ? doc.height / doc.width : 0.5625));
    const store = await ensureEditorSlidesStore();
    if (width) store.setViewportSize(width);
    if (ratio) store.setViewportRatio(ratio);
    if (doc.theme) store.setTheme(doc.theme as any);
    editorPreviewReady.value = true;
  },
  { immediate: true },
);

const kbFolderIds = computed<number[]>(() => (includeGeneratedKb.value ? [0, 1] : [0]));
const readyKbFileCount = computed(() => {
  const allowed = new Set(kbFolderIds.value);
  const list = props.currentCourse.kbFiles || [];
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

const goToKnowledgeBase = () => {
  ui.setRightPanelTab('kb');
  advancedOpen.value = false;
};

const goToOutline = () => {
  const unit = props.currentUnit;
  if (!unit) return;
  router.push({ name: 'course-unit', params: { courseId: props.currentCourse.id, unitId: unit.id, tab: 'outline' } });
};

const openAdvanced = () => {
  lastFocusedEl.value = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  advancedOpen.value = true;
};

const closeAdvanced = () => {
  advancedOpen.value = false;
};

const handleAdvancedEsc = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && advancedOpen.value) {
    closeAdvanced();
  }
};

watch(
  advancedOpen,
  async (open) => {
    if (open) {
      document.body.style.overflow = 'hidden';
      await nextTick();
      advancedDialogRef.value?.focus();
      return;
    }

    document.body.style.overflow = '';
    await nextTick();
    const el = lastFocusedEl.value;
    if (el && document.contains(el)) el.focus();
  },
  { flush: 'post' },
);

const goToEditor = () => {
  const unit = props.currentUnit;
  if (!unit) return;
  router.push({
    name: 'course-unit-ppt-editor',
    params: { courseId: props.currentCourse.id, unitId: unit.id },
  });
};

const mapAipptSlideToPreview = (slide: AIPPTSlide): Presentation['slides'][number] | null => {
  if (!slide) return null;

  if (slide.type === 'cover') {
    return {
      title: slide.data.title || '封面',
      content: slide.data.text ? [slide.data.text] : [],
      notes: '',
    };
  }

  if (slide.type === 'contents') {
    return {
      title: '目录',
      content: slide.data.items || [],
      notes: '',
    };
  }

  if (slide.type === 'transition') {
    const lines = [slide.data.text].filter(Boolean) as string[];
    return {
      title: slide.data.title || '章节',
      content: lines,
      notes: '',
    };
  }

  if (slide.type === 'content') {
    const contentLines = (slide.data.items || []).map((it: any) => {
      if (it?.kind === 'chart') return `图表：${it.title || it.chartType || 'chart'}`;
      if (it?.kind === 'image') return `图片：${it.title || ''} ${it.text || ''}`.trim();
      if (it?.kind === 'text') return `${it.title || ''}：${it.text || ''}`.replace(/^：/, '');
      // legacy {title,text}
      if (typeof it?.title === 'string' && typeof it?.text === 'string') return `${it.title}：${it.text}`;
      return String(it ?? '');
    });
    return {
      title: slide.data.title || '内容',
      content: contentLines.filter((x) => x && x.trim().length > 0),
      notes: '',
    };
  }

  if (slide.type === 'reference') {
    const refs = slide.data.references || [];
    return {
      title: slide.data.title || '参考资料',
      content: refs.map((r: any) => r?.text).filter(Boolean),
      notes: '',
    };
  }

  if (slide.type === 'end') {
    return {
      title: '结束',
      content: [],
      notes: '',
    };
  }

  return null;
};

const buildSlidesMarkdown = (unitTitle: string, slidesList: Presentation['slides']): string => {
  const chunks: string[] = [`# ${unitTitle}`];

  slidesList.forEach((slide, index) => {
    chunks.push(`## Slide ${index + 1}: ${slide.title}`);
    if (slide.content?.length) {
      chunks.push(slide.content.map((c) => `- ${c}`).join('\n'));
    }
    if (slide.notes?.trim()) {
      chunks.push(`**Speaker Notes:**\n${slide.notes.trim()}`);
    }
    chunks.push('---');
  });

  return chunks.join('\n\n');
};

const ensureSelectedTemplate = (list: PPTTemplate[]) => {
  if (!list.length) return;
  const fallback = list[0];
  if (!fallback) return;
  if (props.currentUnit?.selectedTemplateId) {
    const exists = list.find((item) => item.id === props.currentUnit?.selectedTemplateId);
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

onMounted(() => {
  void loadTemplates();
  document.addEventListener('keydown', handleAdvancedEsc);
});

watch(
  previewCanvasRef,
  (el) => {
    if (previewResizeObserver) {
      previewResizeObserver.disconnect();
      previewResizeObserver = null;
    }
    if (!el || typeof ResizeObserver === 'undefined') return;
    previewResizeObserver = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      previewCanvasWidth.value = rect.width;
      previewCanvasHeight.value = rect.height;
    });
    previewResizeObserver.observe(el);
  },
  { immediate: true },
);

watch(
  thumbnailListRef,
  (el) => {
    if (thumbnailResizeObserver) {
      thumbnailResizeObserver.disconnect();
      thumbnailResizeObserver = null;
    }
    if (!el || typeof ResizeObserver === 'undefined') return;

    const update = () => {
      const styles = window.getComputedStyle(el);
      const paddingLeft = Number.parseFloat(styles.paddingLeft || '0') || 0;
      const paddingRight = Number.parseFloat(styles.paddingRight || '0') || 0;
      const inner = el.clientWidth - paddingLeft - paddingRight;
      thumbnailSize.value = Math.max(120, Math.floor(inner - 2));
    };

    update();
    thumbnailResizeObserver = new ResizeObserver(() => update());
    thumbnailResizeObserver.observe(el);
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  if (previewResizeObserver) {
    previewResizeObserver.disconnect();
    previewResizeObserver = null;
  }
  if (thumbnailResizeObserver) {
    thumbnailResizeObserver.disconnect();
    thumbnailResizeObserver = null;
  }
  document.removeEventListener('keydown', handleAdvancedEsc);
  document.body.style.overflow = '';
});

watch(
  () => props.currentUnit,
  (unit) => {
    syncFromUnit(unit);
    if (templates.value.length) {
      ensureSelectedTemplate(templates.value);
    }
  },
  { immediate: true },
);

watch(
  previewSlideCount,
  (len) => {
    if (currentSlideIndex.value >= len) {
      currentSlideIndex.value = len ? len - 1 : 0;
    }
  },
  { immediate: true },
);

const handleGenerate = async () => {
  const unit = props.currentUnit;
  const template = selectedTemplate.value;
  if (!unit || !unit.outlineContent || !template) return;

  loading.value = true;
  currentSlideIndex.value = 0;
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
      sessionId: props.currentCourse.id,
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

    emit('updateUnit', unit.id, {
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
        userId: props.currentCourse.id,
        fileId: `gen:${props.currentCourse.id}:${unit.id}:slides`,
        fileName: `幻灯片-${unit.title}`,
        content: md,
        fileType: 'md',
        folderId: 1,
      })
      .catch((e) => console.warn('PPT 产物入库失败（已忽略）', e));

    toast.success(t('ppt.toast.generated'));
  } catch (error) {
    console.error(error);
    toast.error(t('ppt.toast.error'));
    viewState.value = unit.presentation ? 'PREVIEW' : 'SELECT_TEMPLATE';
  } finally {
    loading.value = false;
  }
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
    <div v-if="viewState === 'SELECT_TEMPLATE'" class="flex-1 flex flex-col min-h-0">
      <div class="mb-6 flex items-start justify-between gap-4">
        <div class="min-w-0">
          <h2 class="text-2xl font-bold text-slate-900 dark:text-white">{{ t('ppt.choose_template') }}</h2>
          <p class="text-slate-500 dark:text-slate-400">{{ t('ppt.select_hint') }}</p>
        </div>

        <button
          type="button"
          class="shrink-0 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-2 font-bold text-sm"
          @click="openAdvanced"
        >
          <span class="relative inline-flex">
            <LucideIcon name="settings-2" :size="16" />
            <span v-if="hasAdvancedOverrides" class="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-indigo-500 ring-2 ring-white dark:ring-slate-900" aria-hidden="true" />
          </span>
          <span class="hidden sm:inline">{{ t('ppt.advanced.title') }}</span>
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div
          v-for="template in templates"
          :key="template.id"
          :class="[
            'cursor-pointer group relative rounded-xl overflow-hidden border-2 transition-all',
            selectedTemplateId === template.id ? 'border-indigo-500 ring-4 ring-indigo-500/20 scale-105' : 'border-slate-200 dark:border-slate-800 hover:border-indigo-300',
          ]"
          @click="selectedTemplateId = template.id"
        >
          <div v-if="template.coverUrl" class="h-32 w-full bg-slate-100 overflow-hidden">
            <img :src="template.coverUrl" class="h-full w-full object-cover group-hover:scale-110 transition-transform duration-500" :alt="template.name" />
          </div>
          <div v-else :class="['h-32 w-full flex items-center justify-center', template.thumbnailColor]">
            <span class="text-white font-bold opacity-80 text-lg">Aa</span>
          </div>
          <div class="p-4 bg-white dark:bg-slate-900">
            <h3 class="font-bold text-slate-800 dark:text-white">{{ template.name }}</h3>
            <p class="text-xs text-slate-500 mt-1">{{ template.styleDescription }}</p>
          </div>
          <div v-if="selectedTemplateId === template.id" class="absolute top-2 right-2 bg-indigo-500 text-white rounded-full p-1 shadow-lg">
            <LucideIcon name="check" :size="16" />
          </div>
        </div>
      </div>

      <div class="flex justify-center">
        <button
          :disabled="loading || !templates.length"
          class="px-10 py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:text-slate-500 text-white rounded-2xl font-bold text-lg shadow-xl shadow-indigo-500/30 transition-all flex items-center gap-3"
          @click="handleGenerate"
        >
          <LucideIcon v-if="loading" name="loader-2" :size="20" class="animate-spin" />
          <span v-else>✨ {{ t('ppt.generate') }}</span>
          <span v-if="loading">{{ t('ppt.generating') }}</span>
        </button>
      </div>
    </div>

		    <div v-else class="h-full flex flex-col gap-6 min-h-0">
		      <div class="flex justify-between items-center bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
			        <div class="flex items-center gap-4">
			          <div>
		            <h3 class="text-sm font-black text-slate-800 dark:text-white leading-tight">{{ t('ppt.preview_title') }}</h3>
		            <p class="text-[11px] text-slate-500 leading-tight mt-0.5">
		              {{ t('ppt.slides_generated', { count: hasEditorSlides ? editorSlides.length : (presentation?.slides.length || 0) }) }}
		            </p>
		          </div>
			        </div>
			        <div class="flex gap-2 flex-wrap justify-end">
		          <button
		            type="button"
		            class="px-3 py-2 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-lg font-bold text-xs hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-2"
		            @click="openAdvanced"
		          >
		            <span class="relative inline-flex">
		              <LucideIcon name="settings-2" :size="16" />
	              <span v-if="hasAdvancedOverrides" class="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-indigo-500 ring-2 ring-white dark:ring-slate-900" aria-hidden="true" />
	            </span>
	            <span class="hidden lg:inline">{{ t('ppt.advanced.title') }}</span>
	          </button>
		          <button
		            v-if="props.currentUnit?.editorDocument"
		            type="button"
	            :disabled="loading"
	            class="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-xs shadow-md transition-all flex items-center gap-2 disabled:bg-slate-300 disabled:text-slate-500"
	            @click="goToEditor"
	          >
	            <LucideIcon name="edit-3" :size="16" />
	            <span>{{ t('ppt.edit') }}</span>
	          </button>
	          <button
	            type="button"
	            class="px-3 py-2 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-lg font-bold text-xs hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
	            @click="viewState = 'SELECT_TEMPLATE'"
	          >
	            {{ t('ppt.change_template') }}
	          </button>
	          <button
	            type="button"
	            :disabled="loading"
	            class="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold text-xs shadow-md transition-all flex items-center gap-2 disabled:bg-slate-300 disabled:text-slate-500"
	            @click="handleGenerate"
	          >
	            <LucideIcon :name="loading ? 'loader-2' : 'refresh-cw'" :size="16" :class="{ 'animate-spin': loading }" />
	            <span>{{ loading ? t('ppt.generating') : t('ppt.regenerate') }}</span>
          </button>
        </div>
	      </div>
	
	      <div v-if="!hasEditorSlides && (!presentation || slides.length === 0)" class="flex-1 flex items-center justify-center bg-slate-100 dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
	        <div class="text-center opacity-40">
	          <LucideIcon name="loader-2" :size="48" class="animate-spin mx-auto mb-4" />
	          <p class="font-bold">{{ t('ppt.generating_content') }}</p>
	        </div>
	      </div>
	
		      <div v-else-if="hasEditorSlides" class="flex-1 min-h-0 flex gap-6 overflow-hidden">
		        <div v-if="!editorPreviewReady || !editorSlidesStoreLoaded" class="flex-1 flex items-center justify-center bg-slate-100 dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
		          <div class="text-center opacity-40">
		            <LucideIcon name="loader-2" :size="48" class="animate-spin mx-auto mb-4" />
		            <p class="font-bold">{{ t('common.loading') }}</p>
		          </div>
		        </div>
		        <template v-else>
		        <div ref="thumbnailListRef" class="w-60 min-h-0 flex-shrink-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-y-auto custom-scrollbar p-3 space-y-3">
		          <button
		            v-for="(slide, i) in editorSlides"
		            :key="slide?.id || i"
		            :class="['w-full text-left group transition-all', currentSlideIndex === i ? 'ring-2 ring-emerald-500 rounded-lg' : 'opacity-70 hover:opacity-100']"
		            @click="currentSlideIndex = i"
		          >
		            <div class="w-full rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
		              <ThumbnailSlide :slide="slide" :size="thumbnailSize" />
		            </div>
		            <div class="flex justify-between items-center px-1 mt-1 gap-2">
		              <span class="text-[10px] font-bold text-slate-400 shrink-0">{{ t('ppt.slide_label', { index: i + 1 }) }}</span>
		              <span class="text-[10px] text-slate-500 line-clamp-1 min-w-0">{{ editorSlideTitles[i] }}</span>
		            </div>
		          </button>
		        </div>
	
		        <div class="flex-1 min-h-0 flex flex-col bg-slate-100 dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 overflow-hidden">
		          <div ref="previewCanvasRef" class="flex-1 min-h-0 overflow-hidden">
		            <div class="h-full w-full flex items-center justify-center">
		              <div v-if="currentEditorSlide" class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl ring-1 ring-slate-200/60 dark:ring-slate-800/60 overflow-hidden">
		                <ThumbnailSlide :slide="currentEditorSlide" :size="mainSlideSize" />
		              </div>
		            </div>
		          </div>
		        </div>
		      </template>
		      </div>

	      <div v-else class="flex-1 min-h-0 flex gap-6 overflow-hidden">
	        <div class="w-48 min-h-0 flex-shrink-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-y-auto custom-scrollbar p-3 space-y-3">
	          <button
	            v-for="(slide, i) in slides"
	            :key="i"
	            :class="['w-full text-left group transition-all', currentSlideIndex === i ? 'ring-2 ring-indigo-500 rounded-lg' : 'opacity-70 hover:opacity-100']"
	            @click="currentSlideIndex = i"
	          >
	            <div
	              :class="[
	                'aspect-video w-full rounded-lg mb-1 flex items-center justify-center text-[10px] p-2 border',
	                currentSlideIndex === i ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200' : 'bg-slate-100 dark:bg-slate-800 border-slate-200',
	              ]"
	            >
	              <div class="text-center line-clamp-2 leading-tight font-bold text-slate-700 dark:text-slate-300">{{ slide.title || t('ppt.untitled') }}</div>
	            </div>
	            <div class="flex justify-between items-center px-1">
	              <span class="text-[10px] font-bold text-slate-400">{{ t('ppt.slide_label', { index: i + 1 }) }}</span>
	            </div>
	          </button>
	        </div>

		        <div class="flex-1 min-h-0 flex flex-col bg-slate-100 dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-slate-800 p-8 overflow-y-auto">
		          <div v-if="currentSlide" class="w-full aspect-video bg-white dark:bg-slate-900 shadow-2xl rounded-xl p-12 flex flex-col relative overflow-hidden mb-6 flex-shrink-0 transition-all duration-300">
		            <div v-if="selectedTemplate?.coverUrl" class="absolute inset-0 bg-center bg-cover opacity-5 pointer-events-none" :style="{ backgroundImage: `url(${selectedTemplate.coverUrl})` }" />
		            <div v-else class="absolute top-0 right-0 w-64 h-64 rounded-full blur-3xl opacity-20 -mr-20 -mt-20" :class="selectedTemplate?.thumbnailColor || 'bg-slate-200'" />
		            <div class="relative z-10 flex flex-col h-full">
	              <h1 class="text-4xl font-black text-slate-900 dark:text-white mb-8 leading-tight">
	                {{ currentSlide?.title }}
	              </h1>
	              <div class="flex-1">
	                <ul class="space-y-4">
	                  <li v-for="(c, idx) in currentSlide?.content || []" :key="idx" class="flex items-start text-xl text-slate-700 dark:text-slate-300">
	                    <span class="mr-4 text-indigo-500 mt-1.5">•</span>
	                    <span>{{ c }}</span>
	                  </li>
	                </ul>
	              </div>
	              <div class="mt-auto flex justify-between items-end border-t border-slate-100 dark:border-slate-800 pt-6">
	                <div class="text-sm font-bold text-slate-400 uppercase tracking-widest">TeachDo</div>
	                <div class="text-sm font-bold text-slate-400">{{ currentSlideIndex + 1 }} / {{ slides.length }}</div>
		              </div>
		            </div>
		          </div>
		        </div>
		      </div>
    </div>

    <Teleport to="body">
      <Transition name="td-modal">
        <div v-if="advancedOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" @click="closeAdvanced" />

          <div
            ref="advancedDialogRef"
            class="relative w-full max-w-2xl rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl outline-none td-modal-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="ppt-advanced-title"
            tabindex="-1"
            @click.stop
          >
            <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200/60 dark:border-slate-800/60">
              <div class="flex items-center gap-2">
                <LucideIcon name="settings-2" :size="18" class="text-slate-500" />
                <h3 id="ppt-advanced-title" class="text-sm font-black text-slate-900 dark:text-white">
                  {{ t('ppt.advanced.title') }}
                </h3>
              </div>
              <button
                type="button"
                class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                :aria-label="t('common.close')"
                @click="closeAdvanced"
              >
                <LucideIcon name="x" :size="18" />
              </button>
            </div>

            <div class="px-5 py-4 space-y-3 max-h-[min(70vh,640px)] overflow-y-auto custom-scrollbar">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label class="flex items-start gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30">
                  <input
                    v-model="generateFromWebSearch"
                    :disabled="loading"
                    type="checkbox"
                    class="mt-1 h-4 w-4 accent-indigo-600 disabled:opacity-50"
                  />
                  <div class="min-w-0">
                    <div class="text-sm font-bold text-slate-700 dark:text-slate-200">{{ t('ppt.advanced.web_search') }}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{{ t('ppt.advanced.web_search_desc') }}</div>
                  </div>
                </label>

                <label
                  class="flex items-start gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30"
                  :class="!hasReadyKbFiles ? 'opacity-60' : ''"
                >
                  <input
                    v-model="generateFromUploadedFile"
                    :disabled="loading || !hasReadyKbFiles"
                    type="checkbox"
                    class="mt-1 h-4 w-4 accent-indigo-600 disabled:opacity-50"
                  />
                  <div class="min-w-0">
                    <div class="text-sm font-bold text-slate-700 dark:text-slate-200">{{ t('ppt.advanced.kb') }}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{{ t('ppt.advanced.kb_desc') }}</div>
                  </div>
                </label>
              </div>

              <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30">
                <div class="min-w-0">
                  <div class="text-sm font-bold text-slate-700 dark:text-slate-200">{{ t('ppt.advanced.kb_scope') }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{{ t('ppt.advanced.kb_scope_desc') }}</div>
                </div>
                <label class="flex items-center gap-2 text-xs font-bold text-slate-600 dark:text-slate-300">
                  <input
                    v-model="includeGeneratedKb"
                    :disabled="loading"
                    type="checkbox"
                    class="h-4 w-4 accent-indigo-600 disabled:opacity-50"
                  />
                  <span>{{ t('ppt.advanced.kb_include_generated') }}</span>
                </label>
              </div>

              <div class="flex items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
                <div>{{ t('ppt.advanced.kb_ready', { count: readyKbFileCount }) }}</div>
                <button
                  v-if="!hasReadyKbFiles"
                  type="button"
                  class="text-indigo-600 dark:text-indigo-300 font-bold hover:underline"
                  @click="goToKnowledgeBase"
                >
                  {{ t('ppt.advanced.goto_kb') }}
                </button>
              </div>
            </div>

            <div class="px-5 py-4 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center justify-end gap-2 bg-slate-50/40 dark:bg-slate-950/20">
              <button
                type="button"
                class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md transition-colors"
                @click="closeAdvanced"
              >
                {{ t('common.close') }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
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

.td-modal-enter-active,
.td-modal-leave-active {
  transition: opacity 150ms ease;
}

.td-modal-enter-from,
.td-modal-leave-to {
  opacity: 0;
}

.td-modal-enter-active .td-modal-panel,
.td-modal-leave-active .td-modal-panel {
  transition: transform 150ms ease, opacity 150ms ease;
}

.td-modal-enter-from .td-modal-panel,
.td-modal-leave-to .td-modal-panel {
  opacity: 0;
  transform: translateY(6px) scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .td-modal-enter-active,
  .td-modal-leave-active,
  .td-modal-enter-active .td-modal-panel,
  .td-modal-leave-active .td-modal-panel {
    transition: none;
  }
}
</style>
