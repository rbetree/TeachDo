<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { renderAsync } from 'docx-preview';
import type { Options } from 'docx-preview';

interface Props {
  docx: Blob | ArrayBuffer | Uint8Array | null;
  options?: Partial<Options>;
}

const props = defineProps<Props>();

const renderKey = ref(0);
const bodyRef = ref<HTMLElement | null>(null);
const styleRef = ref<HTMLElement | null>(null);

let destroyed = false;
let renderSeq = 0;

const renderDocx = async (docx: Props['docx']) => {
  renderSeq += 1;
  const seq = renderSeq;
  renderKey.value = seq;

  await nextTick();
  if (destroyed) return;
  if (seq !== renderSeq) return;

  const body = bodyRef.value;
  const styleContainer = styleRef.value;
  if (!body) return;

  body.innerHTML = '';
  if (styleContainer) styleContainer.innerHTML = '';
  if (!docx) return;

  const options: Partial<Options> = {
    className: 'td-docx',
    inWrapper: true,
    breakPages: true,
    ignoreWidth: false,
    ignoreHeight: false,
    ignoreFonts: false,
    renderHeaders: true,
    renderFooters: true,
    renderFootnotes: true,
    renderEndnotes: true,
    ...(props.options || {}),
  };

  try {
    await renderAsync(docx as any, body, styleContainer || body, options);
  } catch (e) {
    console.warn('DocxPreview 渲染失败（已忽略）', e);
  }
};

watch(
  () => props.docx,
  (docx) => {
    void renderDocx(docx);
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  destroyed = true;
  renderSeq += 1;
  if (bodyRef.value) bodyRef.value.innerHTML = '';
  if (styleRef.value) styleRef.value.innerHTML = '';
});
</script>

<template>
  <div class="td-docx-preview w-full">
    <!-- styleContainer 不展示，但需要留在 DOM 中让样式生效 -->
    <div :key="`td-docx-style-${renderKey}`" ref="styleRef" class="hidden" aria-hidden="true"></div>
    <div :key="`td-docx-body-${renderKey}`" ref="bodyRef" class="w-full"></div>
  </div>
</template>

