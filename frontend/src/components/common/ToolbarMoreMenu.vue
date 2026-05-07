<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';
import LucideIcon from '@/components/common/LucideIcon.vue';

interface Props {
  label: string;
}

const props = defineProps<Props>();

const open = ref(false);
const rootRef = ref<HTMLDivElement | null>(null);

const close = () => {
  open.value = false;
};

const handlePointerDown = (event: PointerEvent) => {
  const el = rootRef.value;
  if (!el) return;
  if (event.target instanceof Node && el.contains(event.target)) return;
  close();
};

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') close();
};

watch(open, (value) => {
  if (value) {
    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeydown);
  } else {
    document.removeEventListener('pointerdown', handlePointerDown);
    document.removeEventListener('keydown', handleKeydown);
  }
});

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handlePointerDown);
  document.removeEventListener('keydown', handleKeydown);
});
</script>

<template>
  <div ref="rootRef" class="relative">
    <button
      type="button"
      class="toolbar-item w-10 justify-center px-0 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600"
      :aria-label="props.label"
      :title="props.label"
      :aria-expanded="open"
      @click="open = !open"
    >
      <LucideIcon name="ellipsis" class="w-4 h-4" />
    </button>

    <div
      v-if="open"
      class="absolute right-0 top-[calc(100%+8px)] z-30 min-w-44 overflow-hidden rounded-xl border border-slate-200 bg-white py-1.5 shadow-xl dark:border-slate-700 dark:bg-slate-800"
    >
      <slot :close="close" />
    </div>
  </div>
</template>
