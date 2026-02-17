<script setup lang="ts">
import '@icon-park/vue-next/styles/index.css';
import 'prosemirror-view/style/prosemirror.css';
import 'animate.css';

import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAppStore } from '@/stores/appStore';
import { aiService } from '@/services/aiService';

import EditorView from '@editor/views/Editor/index.vue';
import ScreenView from '@editor/views/Screen/index.vue';
import { useMainStore, useScreenStore, useSlidesStore, useSnapshotStore } from '@editor/store';
import { deleteDiscardedDB, db } from '@editor/utils/database';
import { exitFullscreen, isFullscreen } from '@editor/utils/fullscreen';
import type { Slide } from '@editor/types/slides';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const appStore = useAppStore();

const editorMainStore = useMainStore();
const editorSlidesStore = useSlidesStore();
const snapshotStore = useSnapshotStore();
const screenStore = useScreenStore();
const { screening } = storeToRefs(screenStore);

const saving = ref(false);
const exitPersisted = ref(false);

const normalizeParam = (value: unknown): string | null => {
  if (Array.isArray(value)) return value.length ? value[0] ?? null : null;
  return typeof value === 'string' ? value : null;
};

const courseId = computed(() => normalizeParam(route.params.courseId));
const unitId = computed(() => normalizeParam(route.params.unitId));

const currentCourse = computed(() => {
  const id = courseId.value;
  if (!id) return null;
  return appStore.courses.find((c) => c.id === id) ?? null;
});

const currentUnit = computed(() => {
  const course = currentCourse.value;
  const id = unitId.value;
  if (!course || !id) return null;
  return course.units.find((u) => u.id === id) ?? null;
});

const resetEditorStores = () => {
  screenStore.setScreening(false);
  editorMainStore.setActiveElementIdList([]);
  editorMainStore.updateSelectedSlidesIndex([]);
  editorMainStore.setDialogForExport('');
  editorMainStore.setSelectPanelState(false);
  editorMainStore.setSearchPanelState(false);
  editorMainStore.setNotesPanelState(false);
  editorMainStore.setSymbolPanelState(false);
  editorMainStore.setMarkupPanelState(false);
  editorMainStore.setAIPPTDialogState(false);
  editorMainStore.setGenerating(false);
};

const initEditorForUnit = async () => {
  const course = currentCourse.value;
  const unit = currentUnit.value;

  if (!course || !unit) {
    await router.replace({ name: 'workspace' });
    return;
  }

  resetEditorStores();

  // 仅在需要时清理旧的 snapshot 数据，避免 Dexie 表无限增长
  await db.snapshots.clear();
  await db.writingBoardImgs.clear();

  const doc = unit.editorDocument;
  const width = Number(doc?.width || doc?.viewport?.size || 960);
  const ratio = Number(
    doc?.viewport?.ratio || (doc?.width && doc?.height ? doc.height / doc.width : 0.5625),
  );

  editorSlidesStore.setTitle(doc?.title || unit.title || editorSlidesStore.title);
  editorSlidesStore.setViewportSize(width);
  editorSlidesStore.setViewportRatio(ratio);
  if (doc?.theme) {
    editorSlidesStore.setTheme(doc.theme as any);
  }

  if (Array.isArray(doc?.slides) && doc.slides.length) {
    editorSlidesStore.setSlides(JSON.parse(JSON.stringify(doc.slides)) as Slide[]);
  } else {
    editorSlidesStore.resetSlides();
  }
  editorSlidesStore.updateSlideIndex(0);

  // 编辑器的 sessionId 统一跟随课程，保持与生成链路一致
  editorMainStore.sessionId = course.id;

  await snapshotStore.initSnapshotDatabase();
};

watch([courseId, unitId], () => void initEditorForUnit(), { immediate: true });
watch([courseId, unitId], () => {
  exitPersisted.value = false;
});

const extractTextFromHtml = (html: string): string => {
  try {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return (doc.body.textContent || '').replace(/\s+/g, ' ').trim();
  } catch {
    return String(html || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
  }
};

const buildSlidesMarkdownFromEditor = (unitTitle: string, slides: Slide[]): string => {
  const chunks: string[] = [`# ${unitTitle}`];

  slides.forEach((slide, index) => {
    const texts: string[] = [];
    for (const el of slide.elements || []) {
      if ((el as any).type === 'text' && typeof (el as any).content === 'string') {
        const text = extractTextFromHtml((el as any).content);
        if (text) texts.push(text);
      } else if ((el as any).type === 'shape' && typeof (el as any).text?.content === 'string') {
        const text = extractTextFromHtml((el as any).text.content);
        if (text) texts.push(text);
      }
    }

    const title = texts[0] || `Slide ${index + 1}`;
    const body = texts.slice(1);

    chunks.push(`## Slide ${index + 1}: ${title}`);
    if (body.length) {
      chunks.push(body.map((t) => `- ${t}`).join('\n'));
    }
    if (slide.remark?.trim()) {
      chunks.push(`**Speaker Notes:**\n${slide.remark.trim()}`);
    }
    chunks.push('---');
  });

  return chunks.join('\n\n');
};

const persistEditorDocument = (courseIdValue: string, unitIdValue: string) => {
  const course = appStore.courses.find((c) => c.id === courseIdValue);
  const unit = course?.units.find((u) => u.id === unitIdValue);
  if (!course || !unit) return;

  const width = Number(editorSlidesStore.viewportSize || 960);
  const ratio = Number(editorSlidesStore.viewportRatio || 0.5625);
  const height = width * ratio;

  const editorDocument = {
    title: editorSlidesStore.title || unit.title,
    templateId: unit.editorDocument?.templateId || unit.selectedTemplateId || '',
    width,
    height,
    theme: JSON.parse(JSON.stringify(editorSlidesStore.theme)),
    slides: JSON.parse(JSON.stringify(editorSlidesStore.slides)),
    viewport: {
      size: width,
      ratio,
    },
    updatedAt: Date.now(),
  };

  appStore.updateCourseUnits(courseIdValue, (units) =>
    units.map((u) => (u.id === unitIdValue ? { ...u, editorDocument } : u)),
  );

  // 产物入库（失败不阻断）
  const md = buildSlidesMarkdownFromEditor(unit.title, editorDocument.slides as Slide[]);
  void aiService
    .vectorizeTextToKb({
      userId: courseIdValue,
      fileId: `gen:${courseIdValue}:${unitIdValue}:slides_final`,
      fileName: `幻灯片最终版-${unit.title}.md`,
      content: md,
      fileType: 'md',
      folderId: 1,
    })
    .catch((e) => console.warn('slides_final 产物入库失败（已忽略）', e));
};

const handleBackToWorkspace = async () => {
  if (!courseId.value || !unitId.value) {
    await router.push({ name: 'workspace' });
    return;
  }

  saving.value = true;
  try {
    persistEditorDocument(courseId.value, unitId.value);
    exitPersisted.value = true;
  } finally {
    saving.value = false;
  }

  await router.push({ name: 'course-unit', params: { courseId: courseId.value, unitId: unitId.value, tab: 'ppt' } });
};

onBeforeRouteLeave(() => {
  if (!courseId.value || !unitId.value) return true;
  if (exitPersisted.value) return true;
  persistEditorDocument(courseId.value, unitId.value);
  return true;
});

onBeforeUnmount(() => {
  try {
    screenStore.setScreening(false);
    if (isFullscreen()) exitFullscreen();
  } catch {
    // ignore
  }
});

// 清理一次历史 DB（不阻断编辑器加载）
void deleteDiscardedDB().catch(() => null);
</script>

<template>
  <section class="teachdo-editor-root">
    <div class="teachdo-editor-actions">
      <button
        type="button"
        class="teachdo-editor-btn"
        :disabled="saving"
        @click="handleBackToWorkspace"
      >
        <span v-if="saving">{{ t('editor.saving') }}</span>
        <span v-else>{{ t('editor.back') }}</span>
      </button>
    </div>

    <ScreenView v-if="screening" />
    <EditorView v-else />
  </section>
</template>

<style scoped lang="scss">
.teachdo-editor-root {
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background-color: #f4f4f4;
  color: #111111;

  /* 仅在编辑器容器内提供设计变量，避免污染工作台 */
  --bg-body: #f4f4f4;
  --bg-surface: #ffffff;
  --bg-surface-secondary: #ffffff;
  --bg-surface-hover: #f4f4f4;

  --text-primary: #111111;
  --text-secondary: #666666;
  --text-tertiary: #888888;

  --primary-color: #000000;
  --primary-hover: #111111;
  --primary-light: rgba(0, 0, 0, 0.08);
  --btn-primary-text-color: #ffffff;

  --border-color: #e0e0e0;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 9999px;

  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;

  --transition-fast: 0.1s;
  --transition-base: 0.2s;
  --transition-slow: 0.3s;

  --z-dropdown: 1000;
  --z-modal: 1050;
  --z-tooltip: 1100;
  --z-notification: 1150;
}

.teachdo-editor-actions {
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 2000;
}

.teachdo-editor-btn {
  appearance: none;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  color: rgba(15, 23, 42, 0.9);
  border-radius: 12px;
  padding: 10px 14px;
  font-weight: 800;
  font-size: 13px;
  cursor: pointer;
  transition: transform 0.15s ease, background-color 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.95);
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }
}
</style>
