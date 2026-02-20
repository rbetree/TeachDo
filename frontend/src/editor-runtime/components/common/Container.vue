<template>
  <div class="container" :class="[sizeClass, { fluid }]">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type Size = 'sm' | 'md' | 'lg' | 'xl' | 'full'

interface Props {
  size?: Size
  fluid?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'lg',
  fluid: false
})

const sizeClass = computed(() => `container-${props.size}`)
</script>

<style scoped lang="scss">
.container {
  width: 100%;
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
  
  &.container-sm {
    max-width: 640px;
  }
  
  &.container-md {
    max-width: 768px;
  }
  
  &.container-lg {
    max-width: 1024px;
  }
  
  &.container-xl {
    max-width: 1280px;
  }
  
  &.container-full {
    max-width: 100%;
  }
  
  &.fluid {
    max-width: 100%;
    padding: 0 var(--spacing-xl);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .container {
    padding: 0 var(--spacing-md);
    
    &.fluid {
      padding: 0 var(--spacing-md);
    }
  }
}

@media (max-width: 480px) {
  .container {
    padding: 0 var(--spacing-sm);
    
    &.fluid {
      padding: 0 var(--spacing-sm);
    }
  }
}
</style>