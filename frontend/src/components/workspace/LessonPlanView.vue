<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { LessonDocxTemplate, LessonPlan, LessonStyle, TeachingMaterial } from '#root/types';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';
import DocxPreview from '@/components/common/DocxPreview.vue';
import WorkspaceNeedOutlineState from '@/components/workspace/WorkspaceNeedOutlineState.vue';
import LessonStyleDialog from '@/components/workspace/lesson/LessonStyleDialog.vue';
import LessonTemplateSelector from '@/components/workspace/lesson/LessonTemplateSelector.vue';
import { aiService } from '@/services/aiService';
import { ApiError, checkBackend } from '@/services/apiClient';
import { KB_USER_ID, useAppStore } from '@/stores/appStore';

type LessonViewState = 'SELECT_TEMPLATE' | 'PREVIEW';

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
const store = useAppStore();

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

const wordPreviewBlob = ref<Blob | null>(null);
const wordPreviewing = ref(false);
const wordPreviewError = ref<string | null>(null);
const wordPreviewAbort = ref<AbortController | null>(null);
const wordPreviewDebounceTimer = ref<number | null>(null);

const style = ref<LessonStyle>(normalizeLessonStyle(null));
const styleDialogOpen = ref(false);
const styleButtonRef = ref<HTMLButtonElement | null>(null);

const templates = ref<LessonDocxTemplate[]>([]);
const templatesLoading = ref(false);
const selectedTemplateId = ref<string>('lesson_simple');
const viewState = ref<LessonViewState>('SELECT_TEMPLATE');

const hasExternalToolbar = computed(() => !!props.headerActionHost);
const hasOutline = computed(() => !!props.currentMaterial?.outlineContent?.trim());
const hasPlan = computed(() => !!plan.value);

watch(
  () => props.currentMaterial?.id,
  () => {
    // 切换教学资料时：停止生成，避免串流写入到新 material
    controllerRef.value?.abort();
    controllerRef.value = null;
    generating.value = false;
    exporting.value = false;
    copied.value = false;

    wordPreviewAbort.value?.abort();
    wordPreviewAbort.value = null;
    if (wordPreviewDebounceTimer.value) clearTimeout(wordPreviewDebounceTimer.value);
    wordPreviewDebounceTimer.value = null;
    wordPreviewBlob.value = null;
    wordPreviewError.value = null;
    wordPreviewing.value = false;

    viewState.value = props.currentMaterial?.lessonPlan ? 'PREVIEW' : 'SELECT_TEMPLATE';
  },
  { immediate: true },
);

watch(
  () => props.currentMaterial?.lessonPlan,
  (value) => {
    plan.value = value ?? null;
  },
  { immediate: true },
);

watch(
  () => props.currentMaterial?.lessonStyle,
  (value) => {
    style.value = normalizeLessonStyle(value ?? null);
  },
  { immediate: true },
);

watch(
  () => props.currentMaterial?.selectedLessonTemplateId,
  (value) => {
    selectedTemplateId.value = (value || 'lesson_simple').trim() || 'lesson_simple';
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  controllerRef.value?.abort();
  controllerRef.value = null;

  wordPreviewAbort.value?.abort();
  wordPreviewAbort.value = null;

  if (wordPreviewDebounceTimer.value) clearTimeout(wordPreviewDebounceTimer.value);
  wordPreviewDebounceTimer.value = null;
});

const normalizeSelectedTemplate = () => {
  const id = (selectedTemplateId.value || '').trim() || 'lesson_simple';
  if (!templates.value.length) {
    selectedTemplateId.value = id;
    return;
  }
  const exists = templates.value.some((t) => t.id === id);
  if (!exists) {
    selectedTemplateId.value = templates.value[0]!.id;
  }
};

onMounted(async () => {
  templatesLoading.value = true;
  try {
    templates.value = await aiService.getLessonTemplates();
  } catch (e) {
    // getLessonTemplates 内部已做兜底，这里再兜底一次避免 UI 崩溃
    console.warn('Failed to load lesson templates.', e);
    templates.value = [];
  } finally {
    templatesLoading.value = false;
    normalizeSelectedTemplate();
  }
});

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

const onTemplateUpdate = (id: string) => {
  selectedTemplateId.value = id;
};

const selectedTemplateName = computed(() => templates.value.find((t) => t.id === selectedTemplateId.value)?.name || '');

const wantEnglish = computed(() => String(locale.value || '').toLowerCase().startsWith('en'));

const goToTemplateSelect = () => {
  clearWordPreview();
  viewState.value = 'SELECT_TEMPLATE';
};

const onTemplatePrimary = () => {
  void generateLesson();
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

const buildLessonMarkdown = (input: { plan: LessonPlan; templateId: string; language: string }): string => {
  const wantEnglish = (input.language || 'zh').trim().toLowerCase() === 'en';
  const title = (input.plan.title || props.currentMaterial?.title || (wantEnglish ? 'Lesson Plan' : '教案')).trim();

  const lines: string[] = [`# ${title}`];
  lines.push(wantEnglish ? `- Audience: ${input.plan.targetAudience}` : `- 受众：${input.plan.targetAudience}`);
  lines.push(wantEnglish ? `- Duration: ${input.plan.duration}` : `- 时长：${input.plan.duration}`);

  lines.push('');
  lines.push(wantEnglish ? '## Objectives' : '## 教学目标');
  for (const item of input.plan.objectives || []) {
    const text = String(item || '').trim();
    if (!text) continue;
    lines.push(`- ${text}`);
  }

  lines.push('');
  lines.push(wantEnglish ? '## Materials' : '## 教学材料');
  for (const item of input.plan.materials || []) {
    const text = String(item || '').trim();
    if (!text) continue;
    lines.push(`- ${text}`);
  }

  lines.push('');
  lines.push(wantEnglish ? '## Procedure' : '## 教学流程');

  const tpl = (input.templateId || '').trim() || 'lesson_simple';
  const procedure = input.plan.procedure || [];
  if (tpl === 'lesson_table') {
    lines.push(wantEnglish ? '| Step | Duration | Activity |' : '| 环节 | 时长 | 活动 |');
    lines.push('| --- | --- | --- |');
    for (const step of procedure) {
      const s = String(step?.step || '').trim();
      const d = String(step?.duration || '').trim();
      const a = String(step?.activity || '').trim();
      if (!s && !a) continue;
      lines.push(`| ${s || '-'} | ${d || '-'} | ${a || '-'} |`);
    }
  } else {
    for (const step of procedure) {
      const s = String(step?.step || '').trim();
      const d = String(step?.duration || '').trim();
      const a = String(step?.activity || '').trim();
      if (!s && !a) continue;
      lines.push(`- **${s || (wantEnglish ? 'Step' : '步骤')}**${d ? `（${d}）` : ''}：${a}`);
    }
  }

  lines.push('');
  lines.push(wantEnglish ? '## Homework' : '## 课后作业');
  if (String(input.plan.homework || '').trim()) {
    lines.push(String(input.plan.homework || '').trim());
  }

  return lines.join('\n');
};

type WordPreviewRefreshReason = 'final' | 'plan' | 'style' | 'template' | 'locale' | 'view';

const clearWordPreview = () => {
  wordPreviewAbort.value?.abort();
  wordPreviewAbort.value = null;
  if (wordPreviewDebounceTimer.value) clearTimeout(wordPreviewDebounceTimer.value);
  wordPreviewDebounceTimer.value = null;
  wordPreviewBlob.value = null;
  wordPreviewError.value = null;
  wordPreviewing.value = false;
};

const refreshWordPreview = async (input: { reason: WordPreviewRefreshReason; force?: boolean }) => {
  const snapshotPlan = plan.value;
  if (!snapshotPlan) return;
  if (viewState.value !== 'PREVIEW') return;
  if (!input.force && generating.value) return;

  const backendOk = await checkBackend();
  if (!backendOk) {
    wordPreviewError.value = wantEnglish.value ? 'Backend is offline.' : '后端不可用。';
    wordPreviewBlob.value = null;
    wordPreviewing.value = false;
    return;
  }

  wordPreviewAbort.value?.abort();
  const controller = new AbortController();
  wordPreviewAbort.value = controller;
  wordPreviewing.value = true;
  wordPreviewError.value = null;

  try {
    const { blob } = await aiService.exportLessonDocx({
      lessonPlan: snapshotPlan,
      style: style.value,
      templateId: selectedTemplateId.value,
      language: locale.value,
      persist: false,
      signal: controller.signal,
    });
    if (controller.signal.aborted) return;
    wordPreviewBlob.value = blob;
    wordPreviewError.value = null;
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.kind === 'abort') return;
      const detail = (e.message || '').trim();
      wordPreviewError.value = detail || (wantEnglish.value ? 'Word preview failed.' : 'Word 预览生成失败。');
    } else {
      wordPreviewError.value = wantEnglish.value ? 'Word preview failed.' : 'Word 预览生成失败。';
    }
    wordPreviewBlob.value = null;
  } finally {
    if (wordPreviewAbort.value === controller) wordPreviewAbort.value = null;
    wordPreviewing.value = false;
  }
};

const scheduleRefreshWordPreview = (input: { reason: WordPreviewRefreshReason; delayMs?: number; force?: boolean }) => {
  const delayMs = typeof input.delayMs === 'number' ? input.delayMs : 600;
  if (wordPreviewDebounceTimer.value) clearTimeout(wordPreviewDebounceTimer.value);
  wordPreviewDebounceTimer.value = window.setTimeout(() => {
    wordPreviewDebounceTimer.value = null;
    void refreshWordPreview({ reason: input.reason, force: input.force });
  }, Math.max(0, delayMs));
};

watch(
  () => viewState.value,
  (next) => {
    if (next !== 'PREVIEW') {
      wordPreviewAbort.value?.abort();
      wordPreviewAbort.value = null;
      wordPreviewing.value = false;
      return;
    }
    if (plan.value && !generating.value) {
      scheduleRefreshWordPreview({ reason: 'view', delayMs: 0 });
    }
  },
);

watch(
  () => plan.value,
  (next, prev) => {
    if (!next) {
      clearWordPreview();
      return;
    }
    if (viewState.value !== 'PREVIEW') return;
    if (generating.value) return;
    if (!prev) {
      scheduleRefreshWordPreview({ reason: 'plan', delayMs: 0 });
    }
  },
);

watch(
  () => [selectedTemplateId.value, locale.value, style.value] as const,
  ([nextTemplateId, nextLocale], [prevTemplateId, prevLocale]) => {
    if (!plan.value) return;
    if (viewState.value !== 'PREVIEW') return;
    if (generating.value) return;

    const reason: WordPreviewRefreshReason =
      nextTemplateId !== prevTemplateId ? 'template' : nextLocale !== prevLocale ? 'locale' : 'style';
    scheduleRefreshWordPreview({ reason, delayMs: 600 });
  },
);

const exportDocx = async () => {
  if (!plan.value) return;
  if (exporting.value) return;
  exporting.value = true;
  try {
    const materialId = props.currentMaterial?.id;
    const { blob, filename, artifactId } = await aiService.exportLessonDocx({
      lessonPlan: plan.value,
      style: style.value,
      templateId: selectedTemplateId.value,
      language: locale.value,
      persist: Boolean(materialId),
      userId: KB_USER_ID,
      materialId,
    });
    const safeName = (filename || `${plan.value.title || 'lesson_plan'}.docx`).replace(/\s+/g, '_');
    downloadBlob(blob, safeName);
    toast.success(artifactId ? `${t('lesson.toast.downloaded')} ${t('lesson.toast.saved_to_outputs')}` : t('lesson.toast.downloaded'));
    if (artifactId && materialId && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('teachdo:artifacts-updated', { detail: { materialId } }));
    }
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

const generateLesson = async () => {
  if (generating.value) return;
  if (!hasOutline.value) return;

  const prevPlan = plan.value;
  const prevWordPreviewBlob = wordPreviewBlob.value;
  const prevWordPreviewError = wordPreviewError.value;
  const prevTemplateId = ((props.currentMaterial?.selectedLessonTemplateId || 'lesson_simple') as string).trim() || 'lesson_simple';

  clearWordPreview();
  controllerRef.value?.abort();
  const controller = new AbortController();
  controllerRef.value = controller;
  generating.value = true;
  viewState.value = 'PREVIEW';

  try {
    const final = await aiService.streamLessonPlan({
      material: props.currentMaterial,
      language: locale.value,
      templateId: selectedTemplateId.value,
      signal: controller.signal,
    });

    plan.value = final;
    emit('updateMaterial', { lessonPlan: final, selectedLessonTemplateId: selectedTemplateId.value, lessonStyle: style.value });
    toast.success(t('lesson.toast.success'));
    scheduleRefreshWordPreview({ reason: 'final', delayMs: 0, force: true });

    // 教案 Markdown 产物入库：用于右侧“课程产出”勾选全文注入（失败不阻断）
    const materialIdValue = props.currentMaterial?.id;
    if (materialIdValue) {
      const fileId = `gen:${KB_USER_ID}:${materialIdValue}:lesson`;
      const fileName = `教案-${props.currentMaterial.title || materialIdValue}.md`;
      const md = buildLessonMarkdown({ plan: final, templateId: selectedTemplateId.value, language: locale.value });
      void aiService
        .vectorizeTextToKb({
          userId: KB_USER_ID,
          fileId,
          fileName,
          content: md,
          fileType: 'md',
          folderId: 1,
          createdAt: Date.now(),
          sourceType: 'material',
          sourceMaterialId: materialIdValue,
          sourceMaterialTitle: props.currentMaterial.title,
        })
        .then(() => {
          const next = (store.kbFiles || []).filter((f) => f.id !== fileId);
          next.unshift({
            id: fileId,
            name: fileName,
            size: md.length,
            type: 'md',
            status: 'ready',
            uploadedAt: new Date(),
            folderId: 1,
            sourceType: 'material',
            sourceMaterialId: materialIdValue,
            sourceMaterialTitle: props.currentMaterial.title,
          });
          store.setKbFiles(next);
        })
        .catch((e) => console.warn('lesson markdown 产物入库失败（已忽略）', e));
    }
  } catch (e) {
    const aborted = e instanceof ApiError && e.kind === 'abort';
    if (aborted) toast.info(t('lesson.toast.cancelled'));
    else toast.error(t('lesson.toast.error'));
    // 生成失败：回滚到之前的版本，避免留下半成品
    plan.value = prevPlan ?? null;
    selectedTemplateId.value = prevTemplateId;
    wordPreviewBlob.value = prevWordPreviewBlob;
    wordPreviewError.value = prevWordPreviewError;
    if (!prevPlan) viewState.value = 'SELECT_TEMPLATE';
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
        :class="hasExternalToolbar
          ? 'w-full h-full'
          : 'bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm min-h-[44px]'"
      >
        <div class="flex items-center gap-2 min-w-0 overflow-x-auto no-scrollbar">
          <div class="toolbar-cluster shrink-0">
            <span class="toolbar-item text-slate-600 dark:text-slate-300">
              <LucideIcon :name="viewState === 'SELECT_TEMPLATE' ? 'layout-grid' : 'file-text'" class="w-4 h-4" />
              <span>{{ viewState === 'SELECT_TEMPLATE' ? t('lesson.choose_template') : t('lesson.preview_title') }}</span>
            </span>
          </div>
          <span
            v-if="viewState !== 'SELECT_TEMPLATE' && selectedTemplateName"
            class="toolbar-item text-slate-500 dark:text-slate-400"
          >
            {{ selectedTemplateName }}
          </span>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <button
            v-if="generating"
            type="button"
            class="toolbar-item bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-800/40 hover:bg-red-100 dark:hover:bg-red-900/30"
            @click="cancelGenerate"
          >
            <LucideIcon name="x" class="w-4 h-4" />
            <span>{{ t('common.cancel') }}</span>
          </button>

          <template v-else>
	            <button
	              ref="styleButtonRef"
	              type="button"
              class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 disabled:opacity-50"
              :disabled="exporting"
              @click="openStyleDialog"
            >
              <LucideIcon name="settings-2" class="w-4 h-4" /> {{ t('lesson.style.button') }}
	            </button>

	            <template v-if="viewState === 'SELECT_TEMPLATE'">
	              <button
	                type="button"
	                class="toolbar-item bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-300 disabled:text-slate-500"
	                :disabled="exporting || templatesLoading"
	                @click="generateLesson"
	              >
	                <LucideIcon
	                  :name="templatesLoading ? 'loader-2' : (plan ? 'refresh-cw' : 'sparkles')"
	                  class="w-4 h-4"
	                  :class="templatesLoading ? 'animate-spin' : ''"
	                />
	                <span>{{ templatesLoading ? t('common.loading') : (plan ? t('lesson.update') : t('lesson.generate')) }}</span>
	              </button>
	            </template>

            <template v-else>
              <button
                type="button"
                class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 disabled:opacity-60"
                :disabled="exporting"
                @click="goToTemplateSelect"
              >
                {{ t('lesson.change_template') }}
              </button>
              <button
                type="button"
                class="toolbar-item bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50"
                :disabled="exporting"
                @click="generateLesson"
              >
                <LucideIcon :name="plan ? 'refresh-cw' : 'sparkles'" class="w-4 h-4" />
                {{ plan ? t('lesson.update') : t('lesson.generate') }}
              </button>

              <button
                v-if="plan"
                type="button"
                class="toolbar-item text-slate-500 hover:text-slate-800 dark:text-slate-300 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 disabled:opacity-50"
                @click="copyToClipboard"
              >
                {{ copied ? t('lesson.copied') : t('lesson.copy') }}
              </button>

              <button
                v-if="plan"
                type="button"
                class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 disabled:opacity-50"
                :disabled="exporting"
                @click="exportDocx"
              >
                <LucideIcon :name="exporting ? 'loader-2' : 'download'" class="w-4 h-4" :class="exporting ? 'animate-spin' : ''" />
                {{ t('lesson.download') }}
              </button>
            </template>
          </template>
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
      <div class="flex-1 min-h-0 p-4 md:p-6 flex flex-col">
	        <LessonTemplateSelector
	          v-if="viewState === 'SELECT_TEMPLATE'"
	          class="flex-1 min-h-0"
	          :templates="templates"
	          :loading="templatesLoading || exporting"
	          :external-toolbar="hasExternalToolbar"
	          :has-plan="hasPlan"
	          :selected-template-id="selectedTemplateId"
	          @update:selected-template-id="onTemplateUpdate"
	          @primary="onTemplatePrimary"
	        />

	        <div v-else class="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
	          <div class="max-w-4xl mx-auto w-full">
	            <div v-if="generating" class="w-full min-h-[420px] flex items-center justify-center">
	              <div class="text-center">
	                <div
	                  class="w-16 h-16 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-center mx-auto mb-4"
	                >
	                  <LucideIcon name="loader-2" :size="28" class="animate-spin text-indigo-600 dark:text-indigo-300" />
	                </div>
	                <p class="font-bold text-slate-700 dark:text-slate-200">
	                  {{ wantEnglish ? 'Generating lesson plan...' : '正在生成教案…' }}
	                </p>
	                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
	                  {{ wantEnglish ? 'Word preview will appear when ready.' : '生成完成后将自动展示 Word 预览。' }}
	                </p>
	              </div>
	            </div>

	            <div v-else-if="!plan" class="w-full min-h-[420px] flex items-center justify-center text-slate-300">
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
	                <div v-if="wordPreviewing" class="flex items-center gap-2 text-xs font-bold text-indigo-700 dark:text-indigo-200">
	                  <LucideIcon name="loader-2" class="w-4 h-4 animate-spin" />
	                  <span>{{ wantEnglish ? 'Rendering Word preview...' : '正在生成 Word 预览...' }}</span>
	                </div>
	              </div>

	              <div v-if="wordPreviewBlob" class="overflow-x-auto">
	                <DocxPreview :docx="wordPreviewBlob" />
	              </div>

	              <div v-else class="w-full min-h-[420px] flex items-center justify-center">
	                <div class="text-center max-w-md">
	                  <div
	                    class="w-16 h-16 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-center mx-auto mb-4"
	                  >
	                    <LucideIcon
	                      :name="wordPreviewError ? 'alert-circle' : 'loader-2'"
	                      :size="28"
	                      :class="wordPreviewError ? 'text-amber-600 dark:text-amber-300' : 'animate-spin text-indigo-600 dark:text-indigo-300'"
	                    />
	                  </div>
	                  <p class="font-bold text-slate-700 dark:text-slate-200">
	                    {{
	                      wordPreviewError
	                        ? (wantEnglish ? 'Word preview failed.' : 'Word 预览生成失败。')
	                        : (wantEnglish ? 'Rendering Word preview...' : '正在生成 Word 预览...')
	                    }}
	                  </p>
	                  <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 break-words px-4">
	                    {{
	                      wordPreviewError
	                        ? wordPreviewError
	                        : (wantEnglish ? 'This may take a few seconds. Please wait.' : '通常需要几秒钟，请稍候。')
	                    }}
	                  </p>
	                  <div class="mt-4 flex items-center justify-center gap-2">
	                    <button
	                      type="button"
	                      class="td-btn-secondary"
	                      :disabled="wordPreviewing"
	                      @click="() => void refreshWordPreview({ reason: 'view', force: true })"
	                    >
	                      {{ wantEnglish ? 'Retry preview' : '重试预览' }}
	                    </button>
	                  </div>
	                </div>
	              </div>
	            </div>
	          </div>
	        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
