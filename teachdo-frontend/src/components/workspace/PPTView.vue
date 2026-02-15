<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import type { CourseGroup, CourseUnit, Presentation, PPTTemplate } from '#root/types';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';
import type { AIPPTSlide } from '@/editor-runtime/types/AIPPT';
import { createAipptGenerator, type ImgPoolItem } from '@/editor-runtime/aippt/aipptGenerator';

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

const advancedOpen = ref(false);
const generateFromWebSearch = ref(true);
const generateFromUploadedFile = ref(true);
const includeGeneratedKb = ref(false);

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
  router.push({ name: 'course-tab', params: { courseId: props.currentCourse.id, tab: 'kb' } });
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
  viewState.value = unit?.presentation ? 'PREVIEW' : 'SELECT_TEMPLATE';
  if (unit?.selectedTemplateId) {
    selectedTemplateId.value = unit.selectedTemplateId;
  }
};

onMounted(loadTemplates);

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
  slides,
  (list) => {
    if (currentSlideIndex.value >= list.length) {
      currentSlideIndex.value = list.length ? list.length - 1 : 0;
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
    <h3 class="text-lg font-bold text-slate-700 dark:text-slate-300">{{ t('lesson.need_outline.title') }}</h3>
    <p class="text-sm mt-2 mb-6 max-w-md text-center text-slate-500">{{ t('ppt.empty_outline') }}</p>
  </div>

  <div v-else class="h-full flex flex-col gap-6">
    <div class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
      <button
        type="button"
        class="w-full flex items-center justify-between gap-3 px-4 py-3 text-left"
        @click="advancedOpen = !advancedOpen"
      >
        <div class="flex items-center gap-2">
          <LucideIcon name="settings-2" :size="18" class="text-slate-500" />
          <div class="font-bold text-slate-700 dark:text-slate-200">{{ t('ppt.advanced.title') }}</div>
        </div>
        <LucideIcon
          name="chevron-down"
          :size="18"
          class="text-slate-400 transition-transform"
          :class="advancedOpen ? 'rotate-180' : ''"
        />
      </button>

      <div v-if="advancedOpen" class="px-4 pb-4 space-y-3">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label class="flex items-start gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30">
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
            class="flex items-start gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30"
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

        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30">
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
    </div>

    <div v-if="viewState === 'SELECT_TEMPLATE'" class="flex-1 flex flex-col">
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-slate-900 dark:text-white">{{ t('ppt.choose_template') }}</h2>
        <p class="text-slate-500 dark:text-slate-400">{{ t('ppt.select_hint') }}</p>
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

    <div v-else class="h-full flex flex-col gap-6">
      <div class="flex justify-between items-center bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div class="flex items-center gap-4">
          <div>
            <h3 class="font-bold text-slate-800 dark:text-white">{{ t('ppt.preview_title') }}</h3>
            <p class="text-xs text-slate-500">{{ t('ppt.slides_generated', { count: presentation?.slides.length || 0 }) }}</p>
          </div>
        </div>
        <div class="flex gap-2 flex-wrap justify-end">
          <button
            type="button"
            class="px-4 py-2 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-lg font-bold text-sm hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            @click="viewState = 'SELECT_TEMPLATE'"
          >
            {{ t('ppt.change_template') }}
          </button>
          <button
            type="button"
            :disabled="loading"
            class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold text-sm shadow-md transition-all flex items-center gap-2 disabled:bg-slate-300 disabled:text-slate-500"
            @click="handleGenerate"
          >
            <LucideIcon :name="loading ? 'loader-2' : 'refresh-cw'" :size="16" :class="{ 'animate-spin': loading }" />
            <span>{{ loading ? t('ppt.generating') : t('ppt.regenerate') }}</span>
          </button>
        </div>
      </div>

      <div v-if="!presentation || slides.length === 0" class="flex-1 flex items-center justify-center bg-slate-100 dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
        <div class="text-center opacity-40">
          <LucideIcon name="loader-2" :size="48" class="animate-spin mx-auto mb-4" />
          <p class="font-bold">{{ t('ppt.generating_content') }}</p>
        </div>
      </div>

      <div v-else class="flex-1 flex gap-6 overflow-hidden">
        <div class="w-48 flex-shrink-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-y-auto custom-scrollbar p-3 space-y-3">
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

          <div class="flex-1 flex flex-col bg-slate-100 dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-slate-800 p-8 overflow-y-auto">
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
                <div class="text-sm font-bold text-slate-400 uppercase tracking-widest">TeachDo x AI2PPT</div>
                <div class="text-sm font-bold text-slate-400">{{ currentSlideIndex + 1 }} / {{ slides.length }}</div>
              </div>
            </div>
            </div>

            <div class="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 flex-shrink-0">
              <h4 class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">{{ t('ppt.speaker_notes') }}</h4>
              <p class="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">
                {{ currentSlide?.notes || t('ppt.no_notes') }}
              </p>
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
