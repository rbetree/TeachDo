<template>
  <div class="spinner-wrapper" :class="[`spinner-wrapper--${size}`, wrapperClass]">
    <div class="spinner" :class="[`spinner--${variant}`, `spinner--${size}`]" :style="spinnerStyle">
      <div class="spinner-circle"></div>
    </div>
    <p v-if="text" class="spinner-text" :class="`spinner-text--${size}`">{{ text }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * Spinner 加载动画组件
 * 
 * @component
 * @example
 * <Spinner text="加载中..." />
 * <Spinner variant="primary" size="lg" />
 */

interface Props {
  /** 变体：primary=主题色, secondary=次要色, white=白色 */
  variant?: 'primary' | 'secondary' | 'white'
  /** 尺寸：sm=24px, md=40px, lg=56px, xl=72px */
  size?: 'sm' | 'md' | 'lg' | 'xl'
  /** 提示文本 */
  text?: string
  /** 自定义包装器类名 */
  wrapperClass?: string
  /** 自定义颜色（覆盖variant） */
  color?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
})

const spinnerStyle = computed(() => {
  if (props.color) {
    return {
      '--spinner-color': props.color,
    }
  }
  return undefined
})
</script>

<style scoped lang="scss">
.spinner-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  
  &--sm {
    gap: 8px;
  }
  
  &--md {
    gap: 12px;
  }
  
  &--lg {
    gap: 16px;
  }
  
  &--xl {
    gap: 20px;
  }
}

.spinner {
  display: inline-block;
  position: relative;
  
  &--sm {
    width: 24px;
    height: 24px;
  }
  
  &--md {
    width: 40px;
    height: 40px;
  }
  
  &--lg {
    width: 56px;
    height: 56px;
  }
  
  &--xl {
    width: 72px;
    height: 72px;
  }
}

.spinner-circle {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 3px solid var(--bg-surface-secondary);
  border-top-color: var(--spinner-color, var(--primary-color));
  animation: spin 1s linear infinite;
  
  .spinner--sm & {
    border-width: 2px;
  }
  
  .spinner--md & {
    border-width: 3px;
  }
  
  .spinner--lg & {
    border-width: 4px;
  }
  
  .spinner--xl & {
    border-width: 5px;
  }
  
  .spinner--primary & {
    border-top-color: var(--spinner-color, var(--primary-color));
  }
  
  .spinner--secondary & {
    border-color: var(--border-color);
    border-top-color: var(--spinner-color, var(--text-secondary));
  }
  
  .spinner--white & {
    border-color: rgba(255, 255, 255, 0.3);
    border-top-color: var(--spinner-color, #ffffff);
  }
}

.spinner-text {
  color: var(--text-secondary);
  text-align: center;
  font-weight: 500;
  
  &--sm {
    font-size: 0.875rem;
  }
  
  &--md {
    font-size: 1rem;
  }
  
  &--lg {
    font-size: 1.125rem;
  }
  
  &--xl {
    font-size: 1.25rem;
  }
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>