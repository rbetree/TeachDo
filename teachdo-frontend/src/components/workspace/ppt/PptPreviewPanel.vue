<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { EditorDocument, Presentation, PPTTemplate } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';

interface Props {
  loading: boolean;
  hasAdvancedOverrides: boolean;
  presentation: Presentation | null;
  selectedTemplate: PPTTemplate | null;
  editorDocument: EditorDocument | null;
  slideIndex: number;
  externalToolbar?: boolean;
}

interface Emits {
  (e: 'update:slideIndex', value: number): void;
  (e: 'openAdvanced'): void;
  (e: 'goToEditor'): void;
  (e: 'changeTemplate'): void;
  (e: 'regenerate'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const ThumbnailSlide = defineAsyncComponent(() => import('@editor/views/components/ThumbnailSlide/index.vue'));

const slideIndexModel = computed({
  get: () => props.slideIndex,
  set: (v: number) => emit('update:slideIndex', v),
});

const slides = computed(() => props.presentation?.slides ?? []);
const currentSlide = computed(() => slides.value[slideIndexModel.value]);

const editorSlides = computed<any[]>(() => (props.editorDocument?.slides ?? []) as any[]);
const hasEditorSlides = computed(() => editorSlides.value.length > 0);
const currentEditorSlide = computed<any | null>(() => editorSlides.value[slideIndexModel.value] ?? null);

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

const previewCanvasRef = ref<HTMLElement | null>(null);
const previewCanvasWidth = ref(0);
const previewCanvasHeight = ref(0);
const thumbnailListRef = ref<HTMLElement | null>(null);
const thumbnailSize = ref(200);
let previewResizeObserver: ResizeObserver | null = null;
let thumbnailResizeObserver: ResizeObserver | null = null;

const mainSlideSize = computed(() => {
  const doc = props.editorDocument;
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

watch(
  previewSlideCount,
  (len) => {
    if (slideIndexModel.value >= len) {
      slideIndexModel.value = len ? len - 1 : 0;
    }
  },
  { immediate: true },
);

watch(
  () => props.editorDocument,
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
});
</script>

<template>
  <div class="h-full flex flex-col min-h-0" :class="props.externalToolbar ? 'gap-4' : 'gap-6'">
    <div v-if="!props.externalToolbar" class="flex justify-between items-center bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
      <div class="flex items-center gap-4">
        <div>
          <h3 class="text-sm font-black text-slate-800 dark:text-white leading-tight">{{ t('ppt.preview_title') }}</h3>
          <p class="text-[11px] text-slate-500 leading-tight mt-0.5">
            {{ t('ppt.slides_generated', { count: hasEditorSlides ? editorSlides.length : (props.presentation?.slides.length || 0) }) }}
          </p>
        </div>
      </div>
      <div class="flex gap-2 flex-wrap justify-end">
        <button
          type="button"
          class="px-3 py-2 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-lg font-bold text-xs hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-2"
          @click="emit('openAdvanced')"
        >
          <span class="relative inline-flex">
            <LucideIcon name="settings-2" :size="16" />
            <span v-if="props.hasAdvancedOverrides" class="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-indigo-500 ring-2 ring-white dark:ring-slate-900" aria-hidden="true" />
          </span>
          <span class="hidden lg:inline">{{ t('ppt.advanced.title') }}</span>
        </button>
        <button
          v-if="props.editorDocument"
          type="button"
          :disabled="props.loading"
          class="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-xs shadow-md transition-all flex items-center gap-2 disabled:bg-slate-300 disabled:text-slate-500"
          @click="emit('goToEditor')"
        >
          <LucideIcon name="edit-3" :size="16" />
          <span>{{ t('ppt.edit') }}</span>
        </button>
        <button
          type="button"
          class="px-3 py-2 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-lg font-bold text-xs hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          @click="emit('changeTemplate')"
        >
          {{ t('ppt.change_template') }}
        </button>
        <button
          type="button"
          :disabled="props.loading"
          class="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold text-xs shadow-md transition-all flex items-center gap-2 disabled:bg-slate-300 disabled:text-slate-500"
          @click="emit('regenerate')"
        >
          <LucideIcon :name="props.loading ? 'loader-2' : 'refresh-cw'" :size="16" :class="{ 'animate-spin': props.loading }" />
          <span>{{ props.loading ? t('ppt.generating') : t('ppt.regenerate') }}</span>
        </button>
      </div>
    </div>

    <div v-if="!hasEditorSlides && (!props.presentation || slides.length === 0)" class="flex-1 flex items-center justify-center bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl">
      <div class="text-center opacity-40">
        <LucideIcon name="loader-2" :size="48" class="animate-spin mx-auto mb-4" />
        <p class="font-bold">{{ t('ppt.generating_content') }}</p>
      </div>
    </div>

    <div v-else-if="hasEditorSlides" class="flex-1 min-h-0 flex gap-6 overflow-hidden">
      <div v-if="!editorPreviewReady || !editorSlidesStoreLoaded" class="flex-1 flex items-center justify-center bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl">
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
            :class="['w-full text-left group transition-all', slideIndexModel === i ? 'ring-2 ring-emerald-500 rounded-lg' : 'opacity-70 hover:opacity-100']"
            @click="slideIndexModel = i"
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

        <div class="flex-1 min-h-0 flex flex-col bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl p-6 overflow-hidden">
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
          :class="['w-full text-left group transition-all', slideIndexModel === i ? 'ring-2 ring-indigo-500 rounded-lg' : 'opacity-70 hover:opacity-100']"
          @click="slideIndexModel = i"
        >
          <div
            :class="[
              'aspect-video w-full rounded-lg mb-1 flex items-center justify-center text-[10px] p-2 border',
              slideIndexModel === i ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200' : 'bg-slate-100 dark:bg-slate-800 border-slate-200',
            ]"
          >
            <div class="text-center line-clamp-2 leading-tight font-bold text-slate-700 dark:text-slate-300">{{ slide.title || t('ppt.untitled') }}</div>
          </div>
          <div class="flex justify-between items-center px-1">
            <span class="text-[10px] font-bold text-slate-400">{{ t('ppt.slide_label', { index: i + 1 }) }}</span>
          </div>
        </button>
      </div>

      <div class="flex-1 min-h-0 flex flex-col bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl p-8 overflow-y-auto custom-scrollbar">
        <div v-if="currentSlide" class="w-full aspect-video bg-white dark:bg-slate-900 shadow-2xl rounded-xl p-12 flex flex-col relative overflow-hidden mb-6 flex-shrink-0 transition-all duration-300">
          <div v-if="props.selectedTemplate?.coverUrl" class="absolute inset-0 bg-center bg-cover opacity-5 pointer-events-none" :style="{ backgroundImage: `url(${props.selectedTemplate.coverUrl})` }" />
          <div v-else class="absolute top-0 right-0 w-64 h-64 rounded-full blur-3xl opacity-20 -mr-20 -mt-20" :class="props.selectedTemplate?.thumbnailColor || 'bg-slate-200'" />
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
              <div class="text-sm font-bold text-slate-400">{{ slideIndexModel + 1 }} / {{ slides.length }}</div>
            </div>
          </div>
        </div>
      </div>
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
