<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    colorClass?: string;
  }>(),
  {
    colorClass: 'text-indigo-600 dark:text-indigo-400',
  },
);
</script>

<template>
  <svg
    viewBox="0 0 40 40"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    :class="props.colorClass"
    aria-hidden="true"
  >
    <path d="M8 10H20" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M16 10V30" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M16 10H24C30 10 34 14 34 20C34 26 30 30 24 30H16" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
