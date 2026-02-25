<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { LessonPlan, LessonStyle, TeachingMaterial } from '#root/types';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';
import WorkspaceNeedOutlineState from '@/components/workspace/WorkspaceNeedOutlineState.vue';
import LessonStyleDialog from '@/components/workspace/lesson/LessonStyleDialog.vue';
import { aiService } from '@/services/aiService';
import { ApiError } from '@/services/apiClient';

interface Props {
  currentMaterial: TeachingMaterial;
  headerActionHost?: HTMLElement | null;
}

interface Emits {
  (e: 'updateMaterial', updates: Partial<TeachingMaterial>): void;
  (e: 'navigate', tab: 'outline'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t, locale } = useI18n();

const DEFAULT_LESSON_STYLE: LessonStyle = {
  fontZh: '微软雅黑',
  titleSizePt: 20,
  h1SizePt: 16,
  h2SizePt: 14,
  bodySizePt: 12,
  lineSpacing: 1.5,
  marginTopCm: 2.54,
  marginBottomCm: 2.54,
  marginLeftCm: 2.54,
  marginRightCm: 2.54,
};

const clampNumber = (v: unknown, fallback: number, min: number, max: number): number => {
  const n = typeof v === 'number' ? v : Number(v);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, n));
};

const normalizeLessonStyle = (input: Partial<LessonStyle> | null | undefined): LessonStyle => {
  const base = input || {};
  return {
    fontZh: typeof base.fontZh === 'string' && base.fontZh.trim() ? base.fontZh.trim() : DEFAULT_LESSON_STYLE.fontZh,
    titleSizePt: clampNumber(base.titleSizePt, DEFAULT_LESSON_STYLE.titleSizePt, 10, 72),
    h1SizePt: clampNumber(base.h1SizePt, DEFAULT_LESSON_STYLE.h1SizePt, 10, 60),
    h2SizePt: clampNumber(base.h2SizePt, DEFAULT_LESSON_STYLE.h2SizePt, 10, 48),
    bodySizePt: clampNumber(base.bodySizePt, DEFAULT_LESSON_STYLE.bodySizePt, 8, 32),
    lineSpacing: clampNumber(base.lineSpacing, DEFAULT_LESSON_STYLE.lineSpacing, 1, 3),
    marginTopCm: clampNumber(base.marginTopCm, DEFAULT_LESSON_STYLE.marginTopCm!, 0.5, 5),
    marginBottomCm: clampNumber(base.marginBottomCm, DEFAULT_LESSON_STYLE.marginBottomCm!, 0.5, 5),
    marginLeftCm: clampNumber(base.marginLeftCm, DEFAULT_LESSON_STYLE.marginLeftCm!, 0.5, 5),
    marginRightCm: clampNumber(base.marginRightCm, DEFAULT_LESSON_STYLE.marginRightCm!, 0.5, 5),
  };
};

const plan = ref<LessonPlan | null>(null);
const copied = ref(false);
const generating = ref(false);
const exporting = ref(false);
const controllerRef = ref<AbortController | null>(null);

const style = ref<LessonStyle>(normalizeLessonStyle(null));
const styleDialogOpen = ref(false);
const styleButtonRef = ref<HTMLButtonElement | null>(null);

const hasExternalToolbar = computed(() => !!props.headerActionHost);
const hasOutline = computed(() => !!props.currentMaterial?.outlineContent?.trim());

watch(
  () => props.currentMaterial,
  (material) => {
    plan.value = material?.lessonPlan ?? null;
    style.value = normalizeLessonStyle(material?.lessonStyle ?? null);
  },
  { immediate: true },
);

const ptToPx = (pt: number) => Math.round(((pt * 4) / 3) * 10) / 10;
const cmToPx = (cm: number) => Math.round(((cm * 96) / 2.54) * 10) / 10;

const paperStyle = computed(() => {
  const m = style.value;
  const padTop = cmToPx(m.marginTopCm ?? DEFAULT_LESSON_STYLE.marginTopCm!);
  const padRight = cmToPx(m.marginRightCm ?? DEFAULT_LESSON_STYLE.marginRightCm!);
  const padBottom = cmToPx(m.marginBottomCm ?? DEFAULT_LESSON_STYLE.marginBottomCm!);
  const padLeft = cmToPx(m.marginLeftCm ?? DEFAULT_LESSON_STYLE.marginLeftCm!);
  return {
    fontFamily: m.fontZh,
    fontSize: `${ptToPx(m.bodySizePt)}px`,
    lineHeight: String(m.lineSpacing),
    padding: `${padTop}px ${padRight}px ${padBottom}px ${padLeft}px`,
  } as Record<string, string>;
});

const titleTextStyle = computed(() => ({ fontSize: `${ptToPx(style.value.titleSizePt)}px` }));
const h1TextStyle = computed(() => ({ fontSize: `${ptToPx(style.value.h1SizePt)}px` }));

const setStyleDialogOpen = (value: boolean) => {
  styleDialogOpen.value = value;
};

const onStyleUpdate = (value: LessonStyle) => {
  style.value = normalizeLessonStyle(value);
  emit('updateMaterial', { lessonStyle: style.value });
};

const openStyleDialog = () => {
  styleDialogOpen.value = true;
};

const copyToClipboard = async () => {
  if (!plan.value) return;
  const text = `
Title: ${plan.value.title}
Audience: ${plan.value.targetAudience}
Duration: ${plan.value.duration}

Objectives:
${plan.value.objectives.map((o, i) => `${i + 1}. ${o}`).join('\n')}

Procedures:
${plan.value.procedure.map((p) => `- ${p.step} (${p.duration})\n  ${p.activity}`).join('\n\n')}

Homework:
${plan.value.homework}
  `.trim();
  try {
    await navigator.clipboard.writeText(text);
    copied.value = true;
    toast.info(t('lesson.toast.copied'));
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    toast.error(t('toast.error'));
  }
};

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const exportDocx = async () => {
  if (!plan.value) return;
  if (exporting.value) return;
  exporting.value = true;
  try {
    const { blob, filename } = await aiService.exportLessonDocx({
      lessonPlan: plan.value,
      style: style.value,
      language: locale.value,
    });
    const safeName = (filename || `${plan.value.title || 'lesson_plan'}.docx`).replace(/\s+/g, '_');
    downloadBlob(blob, safeName);
    toast.success(t('lesson.toast.downloaded'));
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.kind === 'abort') return;
      const detail = (e.message || '').trim();
      if (detail) {
        toast.error(`${t('lesson.toast.export_failed')}：${detail}`);
        return;
      }
    }
    toast.error(t('lesson.toast.export_failed'));
  } finally {
    exporting.value = false;
  }
};

const cancelGenerate = () => {
  controllerRef.value?.abort();
};

const ensureDraftPlan = (): LessonPlan => {
  const title = props.currentMaterial?.title?.trim() || t('lesson.title');
  return {
    title,
    targetAudience: plan.value?.targetAudience || '',
    duration: plan.value?.duration || '',
    objectives: plan.value?.objectives || [],
    materials: plan.value?.materials || [],
    procedure: plan.value?.procedure || [],
    homework: plan.value?.homework || '',
  };
};

const generateLesson = async () => {
  if (generating.value) return;
  if (!hasOutline.value) return;

  controllerRef.value?.abort();
  const controller = new AbortController();
  controllerRef.value = controller;
  generating.value = true;

  // 生成开始时，先放一个可渲染的草稿，便于预览承载“流式填充”
  plan.value = {
    ...ensureDraftPlan(),
    objectives: [],
    materials: [],
    procedure: [],
    homework: '',
  };
  emit('updateMaterial', { lessonPlan: plan.value, lessonStyle: style.value });

  try {
    const final = await aiService.streamLessonPlan({
      material: props.currentMaterial,
      language: locale.value,
      signal: controller.signal,
      onEvent: (evt) => {
        if (evt.type === 'section') {
          const draft = ensureDraftPlan();
          let next: LessonPlan | null = null;
          if (evt.section === 'objectives') next = { ...draft, objectives: evt.data };
          if (evt.section === 'materials') next = { ...draft, materials: evt.data };
          if (evt.section === 'procedure') next = { ...draft, procedure: evt.data };
          if (evt.section === 'homework') next = { ...draft, homework: evt.data };
          if (next) {
            plan.value = next;
            emit('updateMaterial', { lessonPlan: next });
          }
        }
        if (evt.type === 'final') {
          plan.value = evt.data;
          emit('updateMaterial', { lessonPlan: evt.data });
        }
      },
    });

    plan.value = final;
    emit('updateMaterial', { lessonPlan: final });
    toast.success(t('lesson.toast.success'));
  } catch (e) {
    if (e instanceof ApiError && e.kind === 'abort') {
      toast.info(t('lesson.toast.cancelled'));
      return;
    }
    toast.error(t('lesson.toast.error'));
  } finally {
    generating.value = false;
    controllerRef.value = null;
  }
};

const goToOutline = () => {
  emit('navigate', 'outline');
};
</script>

<template>
  <div v-if="!hasOutline" class="h-full flex flex-col min-h-0">
    <WorkspaceNeedOutlineState
      icon="file-text"
      cta-icon="layout-list"
      :title="t('lesson.need_outline.title')"
      :description="t('lesson.need_outline.desc')"
      :cta-label="t('lesson.go_outline')"
      @cta="goToOutline"
    />
  </div>

  <div v-else class="h-full flex flex-col min-h-0" :class="hasExternalToolbar ? 'gap-0' : 'gap-6'">
    <Teleport :to="props.headerActionHost || 'body'" :disabled="!hasExternalToolbar">
      <div
        class="flex items-center justify-between gap-2"
        :class="
          hasExternalToolbar
            ? 'w-full h-full'
            : 'bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm min-h-[44px]'
        "
      >
        <div class="flex items-center gap-2 min-w-0 overflow-x-auto no-scrollbar">
          <div class="toolbar-cluster shrink-0">
            <span class="toolbar-item text-slate-600 dark:text-slate-300">
              <LucideIcon name="file-text" class="w-4 h-4" />
              <span>{{ t('workspace.tab.lesson') }}</span>
            </span>
          </div>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <button
            ref="styleButtonRef"
            type="button"
            class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 disabled:opacity-50"
            :disabled="generating || exporting"
            @click="openStyleDialog"
          >
            <LucideIcon name="settings-2" class="w-4 h-4" /> {{ t('lesson.style.button') }}
          </button>

          <button
            v-if="!generating"
            type="button"
            class="toolbar-item bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50"
            :disabled="exporting"
            @click="generateLesson"
          >
            <LucideIcon :name="plan ? 'refresh-cw' : 'sparkles'" class="w-4 h-4" />
            {{ plan ? t('lesson.update') : t('lesson.generate') }}
          </button>
          <button
            v-else
            type="button"
            class="toolbar-item bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-800/40 hover:bg-red-100 dark:hover:bg-red-900/30"
            @click="cancelGenerate"
          >
            <LucideIcon name="x" class="w-4 h-4" />
            <span>{{ t('common.cancel') }}</span>
          </button>

          <button
            v-if="plan"
            type="button"
            class="toolbar-item text-slate-500 hover:text-slate-800 dark:text-slate-300 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 disabled:opacity-50"
            :disabled="generating"
            @click="copyToClipboard"
          >
            {{ copied ? t('lesson.copied') : t('lesson.copy') }}
          </button>

          <button
            v-if="plan"
            type="button"
            class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 disabled:opacity-50"
            :disabled="generating || exporting"
            @click="exportDocx"
          >
            <LucideIcon :name="exporting ? 'loader-2' : 'download'" class="w-4 h-4" :class="exporting ? 'animate-spin' : ''" />
            {{ t('lesson.download') }}
          </button>
        </div>
      </div>
    </Teleport>

    <LessonStyleDialog
      :open="styleDialogOpen"
      :loading="generating || exporting"
      :style="style"
      :restore-focus-el="styleButtonRef"
      @update:open="setStyleDialogOpen"
      @update:style="onStyleUpdate"
    />

    <div :class="['workspace-card flex-1 min-h-0 flex flex-col', hasExternalToolbar ? 'mt-4' : '']">
      <div class="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-4 md:p-6">
        <div class="max-w-4xl mx-auto w-full">
          <div
            v-if="!plan"
            class="w-full min-h-[420px] flex items-center justify-center text-slate-300"
          >
            <div class="text-center">
              <div
                class="w-16 h-16 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-center mx-auto mb-4 opacity-60"
              >
                <LucideIcon name="file-text" :size="28" />
              </div>
              <p class="font-bold text-slate-500 dark:text-slate-400">{{ t('lesson.ready') }}</p>
              <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">{{ t('lesson.subtitle') }}</p>
            </div>
          </div>

          <div v-else class="animate-fade-in-up">
            <div class="flex items-center justify-between gap-3 mb-3 text-xs text-slate-500 dark:text-slate-400">
              <div class="truncate">
                <span class="font-bold">{{ style.fontZh }}</span>
                <span> · {{ style.bodySizePt }}pt · {{ t('lesson.style.line_spacing') }} {{ style.lineSpacing }}</span>
              </div>
              <div v-if="generating" class="flex items-center gap-2 text-xs font-bold text-indigo-700 dark:text-indigo-200">
                <LucideIcon name="loader-2" class="w-4 h-4 animate-spin" />
                <span>{{ t('common.loading') }}</span>
              </div>
            </div>

            <div class="overflow-x-auto">
              <div class="mx-auto max-w-[920px]" :style="paperStyle">
                <h1 class="font-black text-slate-900 dark:text-white mb-4 leading-tight" :style="titleTextStyle">
                  {{ plan.title }}
                </h1>

                <div class="flex flex-wrap gap-x-6 gap-y-2 text-slate-600 dark:text-slate-300 mb-6">
                  <div>
                    <span class="font-bold">{{ t('lesson.labels.audience') }}：</span>
                    {{ plan.targetAudience || '—' }}
                  </div>
                  <div>
                    <span class="font-bold">{{ t('lesson.labels.duration') }}：</span>
                    {{ plan.duration || '—' }}
                  </div>
                </div>

                <section class="mb-6">
                  <h2 class="font-black text-slate-900 dark:text-white mb-2" :style="h1TextStyle">
                    {{ t('lesson.section.objectives') }}
                  </h2>
                  <ul class="list-disc pl-5 space-y-1 text-slate-800 dark:text-slate-200">
                    <li v-for="(o, i) in plan.objectives" :key="i">{{ o }}</li>
                  </ul>
                </section>

                <section class="mb-6">
                  <h2 class="font-black text-slate-900 dark:text-white mb-2" :style="h1TextStyle">
                    {{ t('lesson.section.materials') }}
                  </h2>
                  <ul class="list-disc pl-5 space-y-1 text-slate-800 dark:text-slate-200">
                    <li v-for="(m, i) in plan.materials" :key="i">{{ m }}</li>
                  </ul>
                </section>

                <section class="mb-6">
                  <h2 class="font-black text-slate-900 dark:text-white mb-3" :style="h1TextStyle">
                    {{ t('lesson.section.procedure') }}
                  </h2>
                  <ol class="list-decimal pl-5 space-y-3 text-slate-800 dark:text-slate-200">
                    <li v-for="(p, i) in plan.procedure" :key="i">
                      <div class="font-black">
                        {{ p.step }}
                        <span class="font-bold text-slate-500 dark:text-slate-400">（{{ p.duration }}）</span>
                      </div>
                      <div class="text-slate-700 dark:text-slate-300 mt-0.5">{{ p.activity }}</div>
                    </li>
                  </ol>
                </section>

                <section class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-950/30 p-4">
                  <h2 class="font-black text-slate-900 dark:text-white mb-2" :style="h1TextStyle">
                    {{ t('lesson.section.homework') }}
                  </h2>
                  <p class="text-slate-800 dark:text-slate-200">{{ plan.homework }}</p>
                </section>
              </div>
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

@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fade-in-up 0.5s ease-out;
}
</style>
