<template>
  <div
    class="card"
    :class="[
      `card--${variant}`,
      {
        'card--hoverable': hoverable,
        'card--clickable': clickable,
        'card--selected': selected,
        'card--disabled': disabled,
      },
      cardClass,
    ]"
    :role="clickable ? 'button' : undefined"
    :tabindex="clickable && !disabled ? 0 : undefined"
    @click="handleClick"
    @keydown.enter="handleClick"
    @keydown.space.prevent="handleClick"
  >
    <!-- 选中图标 -->
    <div v-if="selectable && selected" class="card-check-icon">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
    </div>

    <!-- 卡片头部 -->
    <div v-if="$slots.header || cover" class="card-header" :class="headerClass">
      <slot name="header">
        <img v-if="cover" :src="cover" :alt="coverAlt" class="card-cover" />
      </slot>
    </div>

    <!-- 卡片内容 -->
    <div class="card-body" :class="bodyClass">
      <slot></slot>
    </div>

    <!-- 卡片底部 -->
    <div v-if="$slots.footer" class="card-footer" :class="footerClass">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Card 卡片组件
 * 
 * @component
 * @example
 * <Card hoverable clickable @click="handleCardClick">
 *   <h3>卡片标题</h3>
 *   <p>卡片内容</p>
 * </Card>
 * 
 * <Card selectable :selected="isSelected" @click="toggleSelect">
 *   <template #header>
 *     <img src="..." alt="..." />
 *   </template>
 *   <h3>模板名称</h3>
 * </Card>
 */

interface Props {
  /** 变体：default=默认, bordered=边框, shadow=阴影 */
  variant?: 'default' | 'bordered' | 'shadow'
  /** 是否可悬停（显示悬停效果） */
  hoverable?: boolean
  /** 是否可点击 */
  clickable?: boolean
  /** 是否可选择 */
  selectable?: boolean
  /** 是否选中 */
  selected?: boolean
  /** 是否禁用 */
  disabled?: boolean
  /** 封面图片地址 */
  cover?: string
  /** 封面图片alt文本 */
  coverAlt?: string
  /** 自定义卡片类名 */
  cardClass?: string
  /** 自定义头部类名 */
  headerClass?: string
  /** 自定义内容区类名 */
  bodyClass?: string
  /** 自定义底部类名 */
  footerClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  hoverable: false,
  clickable: false,
  selectable: false,
  selected: false,
  disabled: false,
  coverAlt: '',
})

interface Emits {
  (e: 'click', event: MouseEvent | KeyboardEvent): void
}

const emit = defineEmits<Emits>()

const handleClick = (event: MouseEvent | KeyboardEvent) => {
  if (props.disabled) return
  if (props.clickable) {
    emit('click', event)
  }
}
</script>

<style scoped lang="scss">
.card {
  background-color: var(--bg-surface);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  position: relative;
  transition: all var(--transition-base);
  
  &--default {
    border: 1px solid transparent;
  }
  
  &--bordered {
    border: 1px solid var(--border-color);
  }
  
  &--shadow {
    border: 1px solid transparent;
    box-shadow: var(--shadow-sm);
  }
  
  &--hoverable:not(&--disabled):hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-md);
  }
  
  &--clickable:not(&--disabled) {
    cursor: pointer;
    
    &:active {
      transform: translateY(-2px);
    }
  }
  
  &--selected {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 4px var(--primary-light);
  }
  
  &--disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.card-check-icon {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 28px;
  height: 28px;
  background-color: var(--primary-color);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  animation: checkIconAppear 0.2s ease;
}

@keyframes checkIconAppear {
  from {
    opacity: 0;
    transform: scale(0.5);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.card-header {
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  overflow: hidden;
}

.card-cover {
  width: 100%;
  height: auto;
  display: block;
  object-fit: cover;
}

.card-body {
  padding: 16px;
  flex: 1;
}

.card-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
}

/* 响应式 */
@media (max-width: 768px) {
  .card-body {
    padding: 12px;
  }
  
  .card-footer {
    padding: 10px 12px;
  }
}
</style>