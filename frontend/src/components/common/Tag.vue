<template>
  <span
    class="tag"
    :class="[
      `tag--${variant}`,
      `tag--${size}`,
      {
        'tag--closable': closable,
        'tag--rounded': rounded,
      },
      tagClass,
    ]"
  >
    <slot></slot>
    <button
      v-if="closable"
      class="tag-close"
      type="button"
      aria-label="关闭标签"
      @click="handleClose"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </button>
  </span>
</template>

<script setup lang="ts">
/**
 * Tag 标签组件
 * 
 * @component
 * @example
 * <Tag variant="primary">主要标签</Tag>
 * <Tag variant="success" size="sm">成功</Tag>
 * <Tag closable @close="handleClose">可关闭</Tag>
 */

interface Props {
  /** 变体：default/primary/success/warning/error/info */
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info'
  /** 尺寸：sm/md/lg */
  size?: 'sm' | 'md' | 'lg'
  /** 是否可关闭 */
  closable?: boolean
  /** 是否圆角 */
  rounded?: boolean
  /** 自定义类名 */
  tagClass?: string
}

withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'md',
  closable: false,
  rounded: false,
})

interface Emits {
  (e: 'close'): void
}

const emit = defineEmits<Emits>()

const handleClose = () => {
  emit('close')
}
</script>

<style scoped lang="scss">
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  transition: all var(--transition-base);
  white-space: nowrap;
  
  /* 尺寸 */
  &--sm {
    padding: 2px 8px;
    font-size: 0.75rem;
    line-height: 1.5;
  }
  
  &--md {
    padding: 4px 12px;
    font-size: 0.875rem;
    line-height: 1.5;
  }
  
  &--lg {
    padding: 6px 16px;
    font-size: 1rem;
    line-height: 1.5;
  }
  
  &--rounded {
    border-radius: var(--radius-full);
  }
  
  /* 变体 - Default */
  &--default {
    background-color: var(--bg-surface-secondary);
    color: var(--text-secondary);
  }
  
  /* 变体 - Primary */
  &--primary {
    background-color: var(--primary-light);
    color: var(--primary-color);
  }
  
  /* 变体 - Success */
  &--success {
    background-color: var(--color-success-bg);
    color: var(--color-success);
  }
  
  /* 变体 - Warning */
  &--warning {
    background-color: var(--color-warning-bg);
    color: var(--color-warning);
  }
  
  /* 变体 - Error */
  &--error {
    background-color: var(--color-error-bg);
    color: var(--color-error);
  }
  
  /* 变体 - Info */
  &--info {
    background-color: var(--color-info-bg);
    color: var(--color-info);
  }
}

.tag-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  margin: -2px -4px -2px 2px;
  background: transparent;
  border: none;
  border-radius: 50%;
  color: currentColor;
  cursor: pointer;
  transition: all var(--transition-base);
  opacity: 0.7;
  
  &:hover {
    opacity: 1;
    background-color: rgba(0, 0, 0, 0.1);
  }
  
  &:active {
    transform: scale(0.9);
  }
  
  svg {
    display: block;
  }
}
</style>