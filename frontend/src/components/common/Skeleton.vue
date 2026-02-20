<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    variant?: 'rect' | 'circle';
  }>(),
  {
    variant: 'rect',
  },
);
</script>

<template>
  <div
    class="animate-pulse bg-slate-200 dark:bg-slate-700/60"
    :class="props.variant === 'circle' ? 'rounded-full' : 'rounded-lg'"
  ></div>
</template>
