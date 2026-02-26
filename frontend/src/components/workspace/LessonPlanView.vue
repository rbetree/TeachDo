<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { LessonDocxTemplate, LessonPlan, LessonStyle, TeachingMaterial } from '#root/types';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';
import WorkspaceNeedOutlineState from '@/components/workspace/WorkspaceNeedOutlineState.vue';
import LessonStyleDialog from '@/components/workspace/lesson/LessonStyleDialog.vue';
import LessonTemplateSelector from '@/components/workspace/lesson/LessonTemplateSelector.vue';
import { aiService } from '@/services/aiService';
import { ApiError } from '@/services/apiClient';
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

const onTemplateUpdate = (id: string) => {
  selectedTemplateId.value = id;
};

const selectedTemplateName = computed(() => templates.value.find((t) => t.id === selectedTemplateId.value)?.name || '');

const wantEnglish = computed(() => String(locale.value || '').toLowerCase().startsWith('en'));
const dashPlaceholder = computed(() => (wantEnglish.value ? 'N/A' : '—'));

const formLabels = computed(() => {
  if (wantEnglish.value) {
    return {
      topic: 'Teaching Topic (chapter/theme):',
      lessonType: 'Lesson Type',
      lessonTime: 'Lesson Time',
      datePlaceholder: 'YYYY  MM  DD',
      periodPlaceholder: 'Week __  Day __  Period __',
      content: 'Teaching Content (basics / key / difficult points):',
      methods: 'Teaching Tools and Methods:',
      homework: 'Questions / Discussion / Homework:',
      references: 'References (books, papers, etc.):',
      basics: 'Basics:',
      key: 'Key Points:',
      diff: 'Difficult Points:',
      tools: 'Tools:',
      method: 'Methods:',
    };
  }
  return {
    topic: '授课题目（教学章节或主题）：',
    lessonType: '授课类型',
    lessonTime: '授课时间',
    datePlaceholder: '年   月   日',
    periodPlaceholder: '第   周星期     第   节',
    content: '教学内容（包括基本内容、重点、难点三部分）：',
    methods: '教学手段与方法：',
    homework: '思考题、讨论题或作业：',
    references: '参考资料（包括辅助教材、参考书、文献等）：',
    basics: '基本内容：',
    key: '重点：',
    diff: '难点：',
    tools: '教学手段：',
    method: '教学方法：',
  };
});

const objectiveSplit = computed(() => {
  const list = Array.isArray(plan.value?.objectives) ? plan.value!.objectives : [];
  const cleaned = list.map((x) => String(x || '').trim()).filter(Boolean);
  if (!cleaned.length) {
    return { key: [dashPlaceholder.value], difficult: dashPlaceholder.value };
  }

  const last = cleaned[cleaned.length - 1] || '';
  const isDifficulty = wantEnglish.value ? /^difficulty\s*[:：]/i.test(last) : /^难点\s*[:：]/.test(last);
  if (isDifficulty) {
    const key = cleaned.slice(0, -1);
    const difficult = wantEnglish.value
      ? last.replace(/^difficulty\s*[:：]\s*/i, '').trim()
      : last.replace(/^难点\s*[:：]\s*/, '').trim();
    return { key: key.length ? key : [dashPlaceholder.value], difficult: difficult || dashPlaceholder.value };
  }

  if (cleaned.length >= 2) {
    return { key: cleaned.slice(0, -1), difficult: last };
  }
  return { key: cleaned, difficult: dashPlaceholder.value };
});

const basicContentLines = computed(() => {
  const items = Array.isArray(plan.value?.procedure) ? plan.value!.procedure : [];
  if (!items.length) return [dashPlaceholder.value];

  return items
    .map((item, idx) => {
      const step = String((item as any)?.step || '').trim();
      const duration = String((item as any)?.duration || '').trim();
      const activity = String((item as any)?.activity || '').trim();
      const prefix = `${idx + 1}. ${step || (wantEnglish.value ? 'Step' : '步骤')}`;
      const durPart = duration ? (wantEnglish.value ? ` (${duration})` : `（${duration}）`) : '';
      const actPart = activity ? (wantEnglish.value ? ` ${activity}` : `${activity}`) : '';
      return `${prefix}${durPart}${actPart}`.trim();
    })
    .filter(Boolean);
});

const toolsText = computed(() => {
  const items = Array.isArray(plan.value?.materials) ? plan.value!.materials : [];
  const cleaned = items.map((x) => String(x || '').trim()).filter(Boolean);
  if (!cleaned.length) return dashPlaceholder.value;
  return wantEnglish.value ? cleaned.join(', ') : cleaned.join('、');
});

const inferredMethodsText = computed(() => {
  const items = Array.isArray(plan.value?.procedure) ? plan.value!.procedure : [];
  const haystack = items
    .map((p: any) => `${String(p?.step || '')} ${String(p?.activity || '')}`.trim())
    .join(' ')
    .toLowerCase();

  const methods: string[] = [];
  if (wantEnglish.value) {
    methods.push('Lecture');
    if (haystack.includes('discussion') || haystack.includes('讨论')) methods.push('Discussion');
    if (haystack.includes('demo') || haystack.includes('demonstr') || haystack.includes('示范')) methods.push('Demonstration');
    if (haystack.includes('exercise') || haystack.includes('practice') || haystack.includes('练习') || haystack.includes('训练')) methods.push('Practice');
    if (haystack.includes('group') || haystack.includes('合作') || haystack.includes('小组')) methods.push('Group work');
    if (haystack.includes('q&a') || haystack.includes('question') || haystack.includes('提问') || haystack.includes('问答')) methods.push('Q&A');
  } else {
    methods.push('讲授');
    if (haystack.includes('讨论')) methods.push('讨论');
    if (haystack.includes('示范')) methods.push('示范');
    if (haystack.includes('练习') || haystack.includes('训练')) methods.push('练习');
    if (haystack.includes('合作') || haystack.includes('小组')) methods.push('小组合作');
    if (haystack.includes('提问') || haystack.includes('问答')) methods.push('提问');
  }

  const uniq: string[] = [];
  for (const m of methods) {
    if (!uniq.includes(m)) uniq.push(m);
  }
  return uniq.length ? (wantEnglish.value ? uniq.join(', ') : uniq.join('、')) : dashPlaceholder.value;
});

const referenceLines = computed(() => {
  const items = Array.isArray(plan.value?.materials) ? plan.value!.materials : [];
  const cleaned = items.map((x) => String(x || '').trim()).filter(Boolean);
  if (!cleaned.length) return [dashPlaceholder.value];

  const keywords = wantEnglish.value
    ? ['reference', 'paper', 'book', 'isbn', 'textbook', 'literature']
    : ['教材', '课本', '参考', '文献', '论文', '书', 'ISBN'];
  const refs = cleaned.filter((m) => keywords.some((k) => m.toLowerCase().includes(k.toLowerCase())));
  if (!refs.length) return [dashPlaceholder.value];
  return refs.map((r) => (r.startsWith('-') ? r : `- ${r}`));
});

const goToTemplateSelect = () => {
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

  const prevPlan = plan.value;
  const prevTemplateId = ((props.currentMaterial?.selectedLessonTemplateId || 'lesson_simple') as string).trim() || 'lesson_simple';
  controllerRef.value?.abort();
  const controller = new AbortController();
  controllerRef.value = controller;
  generating.value = true;
  viewState.value = 'PREVIEW';

  // 生成开始时，先放一个可渲染的草稿，便于预览承载“流式填充”
  plan.value = {
    ...ensureDraftPlan(),
    objectives: [],
    materials: [],
    procedure: [],
    homework: '',
  };

  try {
    const final = await aiService.streamLessonPlan({
      material: props.currentMaterial,
      language: locale.value,
      templateId: selectedTemplateId.value,
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
          }
        }
        if (evt.type === 'final') plan.value = evt.data;
      },
    });

    plan.value = final;
    emit('updateMaterial', { lessonPlan: final, selectedLessonTemplateId: selectedTemplateId.value, lessonStyle: style.value });
    toast.success(t('lesson.toast.success'));

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
    if (e instanceof ApiError && e.kind === 'abort') {
      toast.info(t('lesson.toast.cancelled'));
      return;
    }
    toast.error(t('lesson.toast.error'));
    // 生成失败：回滚到之前的版本，避免留下半成品
    plan.value = prevPlan ?? null;
    selectedTemplateId.value = prevTemplateId;
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
            <div v-if="!plan" class="w-full min-h-[420px] flex items-center justify-center text-slate-300">
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
                  <template v-if="selectedTemplateId === 'lesson_jnu_form'">
                    <table class="w-full border-collapse text-slate-800 dark:text-slate-200">
                      <tbody>
                        <tr>
                          <td rowspan="3" class="border border-slate-200 dark:border-slate-800 align-top p-3">
                            <div class="font-black">{{ formLabels.topic }}</div>
                            <div class="mt-2 whitespace-pre-wrap">{{ plan.title }}</div>
                          </td>
                          <td class="border border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-950/30 text-center font-black p-3">
                            {{ formLabels.lessonType }}
                          </td>
                          <td class="border border-slate-200 dark:border-slate-800 align-top p-3">
                            {{ dashPlaceholder }}
                          </td>
                        </tr>
                        <tr>
                          <td
                            rowspan="2"
                            class="border border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-950/30 text-center font-black p-3"
                          >
                            {{ formLabels.lessonTime }}
                          </td>
                          <td class="border border-slate-200 dark:border-slate-800 align-top p-3">
                            {{ formLabels.datePlaceholder }}
                          </td>
                        </tr>
                        <tr>
                          <td class="border border-slate-200 dark:border-slate-800 align-top p-3">
                            {{ formLabels.periodPlaceholder }}
                          </td>
                        </tr>
                        <tr>
                          <td colspan="3" class="border border-slate-200 dark:border-slate-800 align-top p-3">
                            <div class="font-black">{{ formLabels.content }}</div>
                            <div class="mt-2 space-y-3">
                              <section>
                                <div class="font-black">{{ formLabels.basics }}</div>
                                <ul class="list-disc pl-5 space-y-1 text-slate-800 dark:text-slate-200">
                                  <li v-for="(line, i) in basicContentLines" :key="i">{{ line }}</li>
                                </ul>
                              </section>
                              <section>
                                <div class="font-black">{{ formLabels.key }}</div>
                                <ul class="list-disc pl-5 space-y-1 text-slate-800 dark:text-slate-200">
                                  <li v-for="(line, i) in objectiveSplit.key" :key="i">{{ line }}</li>
                                </ul>
                              </section>
                              <section>
                                <div class="font-black">{{ formLabels.diff }}</div>
                                <div class="text-slate-800 dark:text-slate-200 whitespace-pre-wrap">{{ objectiveSplit.difficult }}</div>
                              </section>
                            </div>
                          </td>
                        </tr>
                        <tr>
                          <td colspan="3" class="border border-slate-200 dark:border-slate-800 align-top p-3">
                            <div class="font-black">{{ formLabels.methods }}</div>
                            <div class="mt-2 space-y-1">
                              <div><span class="font-black">{{ formLabels.tools }}</span> {{ toolsText }}</div>
                              <div><span class="font-black">{{ formLabels.method }}</span> {{ inferredMethodsText }}</div>
                            </div>
                          </td>
                        </tr>
                        <tr>
                          <td colspan="3" class="border border-slate-200 dark:border-slate-800 align-top p-3">
                            <div class="font-black">{{ formLabels.homework }}</div>
                            <div class="mt-2 whitespace-pre-wrap text-slate-800 dark:text-slate-200">{{ plan.homework || dashPlaceholder }}</div>
                          </td>
                        </tr>
                        <tr>
                          <td colspan="3" class="border border-slate-200 dark:border-slate-800 align-top p-3">
                            <div class="font-black">{{ formLabels.references }}</div>
                            <ul class="mt-2 space-y-1 text-slate-800 dark:text-slate-200">
                              <li v-for="(line, i) in referenceLines" :key="i" class="whitespace-pre-wrap">{{ line }}</li>
                            </ul>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </template>

                  <template v-else-if="selectedTemplateId === 'lesson_table'">
                    <h1 class="font-black text-slate-900 dark:text-white mb-4 leading-tight" :style="titleTextStyle">
                      {{ plan.title }}
                    </h1>

                    <table class="w-full border-collapse mb-6 text-slate-800 dark:text-slate-200">
                      <tbody>
                        <tr>
                          <td class="border border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-950/30 font-black text-center p-2">
                            {{ t('lesson.labels.audience') }}
                          </td>
                          <td class="border border-slate-200 dark:border-slate-800 p-2">
                            {{ plan.targetAudience || dashPlaceholder }}
                          </td>
                          <td class="border border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-950/30 font-black text-center p-2">
                            {{ t('lesson.labels.duration') }}
                          </td>
                          <td class="border border-slate-200 dark:border-slate-800 p-2">
                            {{ plan.duration || dashPlaceholder }}
                          </td>
                        </tr>
                      </tbody>
                    </table>

                    <section class="mb-6">
                      <h2 class="font-black text-slate-900 dark:text-white mb-2" :style="h1TextStyle">{{ t('lesson.section.procedure') }}</h2>
                      <table class="w-full border-collapse text-slate-800 dark:text-slate-200">
                        <thead>
                          <tr>
                            <th class="border border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-950/30 text-left p-2 font-black">
                              {{ wantEnglish ? 'Step' : '环节' }}
                            </th>
                            <th class="border border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-950/30 text-left p-2 font-black">
                              {{ wantEnglish ? 'Duration' : '时长' }}
                            </th>
                            <th class="border border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-950/30 text-left p-2 font-black">
                              {{ wantEnglish ? 'Activity' : '活动' }}
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(p, i) in plan.procedure" :key="i">
                            <td class="border border-slate-200 dark:border-slate-800 align-top p-2 font-black">{{ p.step }}</td>
                            <td class="border border-slate-200 dark:border-slate-800 align-top p-2">{{ p.duration }}</td>
                            <td class="border border-slate-200 dark:border-slate-800 align-top p-2 whitespace-pre-wrap">{{ p.activity }}</td>
                          </tr>
                          <tr v-if="!plan.procedure.length">
                            <td class="border border-slate-200 dark:border-slate-800 p-2" colspan="3">{{ dashPlaceholder }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </section>

                    <section class="mb-6">
                      <h2 class="font-black text-slate-900 dark:text-white mb-2" :style="h1TextStyle">{{ t('lesson.section.objectives') }}</h2>
                      <ul class="list-disc pl-5 space-y-1 text-slate-800 dark:text-slate-200">
                        <li v-for="(o, i) in plan.objectives" :key="i">{{ o }}</li>
                        <li v-if="!plan.objectives.length">{{ dashPlaceholder }}</li>
                      </ul>
                    </section>

                    <section class="mb-6">
                      <h2 class="font-black text-slate-900 dark:text-white mb-2" :style="h1TextStyle">{{ t('lesson.section.materials') }}</h2>
                      <ul class="list-disc pl-5 space-y-1 text-slate-800 dark:text-slate-200">
                        <li v-for="(m, i) in plan.materials" :key="i">{{ m }}</li>
                        <li v-if="!plan.materials.length">{{ dashPlaceholder }}</li>
                      </ul>
                    </section>

                    <section class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-950/30 p-4">
                      <h2 class="font-black text-slate-900 dark:text-white mb-2" :style="h1TextStyle">{{ t('lesson.section.homework') }}</h2>
                      <p class="text-slate-800 dark:text-slate-200 whitespace-pre-wrap">{{ plan.homework || dashPlaceholder }}</p>
                    </section>
                  </template>

                  <template v-else>
                    <h1 class="font-black text-slate-900 dark:text-white mb-4 leading-tight" :style="titleTextStyle">
                      {{ plan.title }}
                    </h1>

                    <div class="flex flex-wrap gap-x-6 gap-y-2 text-slate-600 dark:text-slate-300 mb-6">
                      <div>
                        <span class="font-bold">{{ t('lesson.labels.audience') }}：</span>
                        {{ plan.targetAudience || dashPlaceholder }}
                      </div>
                      <div>
                        <span class="font-bold">{{ t('lesson.labels.duration') }}：</span>
                        {{ plan.duration || dashPlaceholder }}
                      </div>
                    </div>

                    <section class="mb-6">
                      <h2 class="font-black text-slate-900 dark:text-white mb-2" :style="h1TextStyle">{{ t('lesson.section.objectives') }}</h2>
                      <ul class="list-disc pl-5 space-y-1 text-slate-800 dark:text-slate-200">
                        <li v-for="(o, i) in plan.objectives" :key="i">{{ o }}</li>
                      </ul>
                    </section>

                    <section class="mb-6">
                      <h2 class="font-black text-slate-900 dark:text-white mb-2" :style="h1TextStyle">{{ t('lesson.section.materials') }}</h2>
                      <ul class="list-disc pl-5 space-y-1 text-slate-800 dark:text-slate-200">
                        <li v-for="(m, i) in plan.materials" :key="i">{{ m }}</li>
                      </ul>
                    </section>

                    <section class="mb-6">
                      <h2 class="font-black text-slate-900 dark:text-white mb-3" :style="h1TextStyle">{{ t('lesson.section.procedure') }}</h2>
                      <ol class="list-decimal pl-5 space-y-3 text-slate-800 dark:text-slate-200">
                        <li v-for="(p, i) in plan.procedure" :key="i">
                          <div class="font-black">
                            {{ p.step }}
                            <span class="font-bold text-slate-500 dark:text-slate-400">（{{ p.duration }}）</span>
                          </div>
                          <div class="text-slate-700 dark:text-slate-300 mt-0.5 whitespace-pre-wrap">{{ p.activity }}</div>
                        </li>
                      </ol>
                    </section>

                    <section class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-950/30 p-4">
                      <h2 class="font-black text-slate-900 dark:text-white mb-2" :style="h1TextStyle">{{ t('lesson.section.homework') }}</h2>
                      <p class="text-slate-800 dark:text-slate-200 whitespace-pre-wrap">{{ plan.homework }}</p>
                    </section>
                  </template>
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
