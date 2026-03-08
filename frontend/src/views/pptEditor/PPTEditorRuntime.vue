<script setup lang="ts">
import '@icon-park/vue-next/styles/index.css';
import 'prosemirror-view/style/prosemirror.css';
import 'animate.css';

import { computed, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { useAppStore } from '@/stores/appStore';
import { aiService } from '@/services/aiService';
import { KB_USER_ID } from '@/stores/appStore';
import { TEACHDO_EDITOR_BRIDGE_KEY } from '@editor/contexts/teachdoBridge';

import EditorView from '@editor/views/Editor/index.vue';
import ScreenView from '@editor/views/Screen/index.vue';
import { useMainStore, useScreenStore, useSlidesStore, useSnapshotStore } from '@editor/store';
import { deleteDiscardedDB, db } from '@editor/utils/database';
import { exitFullscreen, isFullscreen } from '@editor/utils/fullscreen';
import type { Slide } from '@editor/types/slides';

const emit = defineEmits<{
  /**
   * 编辑器运行时组件已挂载（用于外层 Loading 覆盖层收起）。
   */
  (e: 'ready'): void;
}>();

const route = useRoute();
const router = useRouter();
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

const materialId = computed(() => normalizeParam(route.params.materialId));

const currentMaterial = computed(() => {
  const id = materialId.value;
  if (!id) return null;
  return appStore.materials.find((m) => m.id === id) ?? null;
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

const initEditorForMaterial = async () => {
  const material = currentMaterial.value;

  if (!material) {
    await router.replace({ name: 'workspace' });
    return;
  }

  resetEditorStores();

  // 仅在需要时清理旧的 snapshot 数据，避免 Dexie 表无限增长
  await db.snapshots.clear();
  await db.writingBoardImgs.clear();

  const doc = material.editorDocument;
  const width = Number(doc?.width || doc?.viewport?.size || 960);
  const ratio = Number(doc?.viewport?.ratio || (doc?.width && doc?.height ? doc.height / doc.width : 0.5625));

  editorSlidesStore.setTitle(doc?.title || material.title || editorSlidesStore.title);
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

  // 编辑器的 sessionId 与全局 KB userId 保持一致
  editorMainStore.sessionId = KB_USER_ID;
  editorMainStore.setTeachdoMaterialId(material.id);
  editorMainStore.setTeachdoUserId(KB_USER_ID);

  await snapshotStore.initSnapshotDatabase();
};

watch([materialId], () => void initEditorForMaterial(), { immediate: true });
watch([materialId], () => {
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

const buildSlidesMarkdownFromEditor = (materialTitle: string, slides: Slide[]): string => {
  const chunks: string[] = [`# ${materialTitle}`];

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

const persistEditorDocument = (materialIdValue: string) => {
  const material = appStore.materials.find((m) => m.id === materialIdValue);
  if (!material) return;

  const width = Number(editorSlidesStore.viewportSize || 960);
  const ratio = Number(editorSlidesStore.viewportRatio || 0.5625);
  const height = width * ratio;

  const editorDocument = {
    title: editorSlidesStore.title || material.title,
    templateId: material.editorDocument?.templateId || material.selectedTemplateId || '',
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

  appStore.patchMaterial(materialIdValue, { editorDocument });

  // 产物入库（失败不阻断）
  const md = buildSlidesMarkdownFromEditor(material.title, editorDocument.slides as Slide[]);
  void aiService
    .vectorizeTextToKb({
      userId: KB_USER_ID,
      fileId: `gen:${KB_USER_ID}:${materialIdValue}:slides_final`,
      fileName: `幻灯片最终版-${material.title}.md`,
      content: md,
      fileType: 'md',
      folderId: 1,
      createdAt: Date.now(),
      sourceType: 'material',
      sourceMaterialId: materialIdValue,
      sourceMaterialTitle: material.title,
    })
    .catch((e) => console.warn('slides_final 产物入库失败（已忽略）', e));
};

const handleBackToWorkspace = async () => {
  if (!materialId.value) {
    await router.push({ name: 'workspace' });
    return;
  }

  saving.value = true;
  try {
    persistEditorDocument(materialId.value);
    exitPersisted.value = true;
  } finally {
    saving.value = false;
  }

  await router.push({ name: 'material-tab', params: { materialId: materialId.value, tab: 'ppt' } });
};

// 将“返回工作台”的触发入口放到编辑器原生顶部（EditorHeader）中。
provide(TEACHDO_EDITOR_BRIDGE_KEY, {
  backToWorkspace: handleBackToWorkspace,
  saving,
});

onBeforeRouteLeave(() => {
  if (!materialId.value) return true;
  if (exitPersisted.value) return true;
  persistEditorDocument(materialId.value);
  return true;
});

onMounted(() => {
  emit('ready');
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
</style>
