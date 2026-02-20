<template>
  <component
    :is="tag"
    :type="nativeType"
    :disabled="disabled || loading"
    :class="buttonClass"
    @click="handleClick"
  >
    <!-- 加载状态 -->
    <span v-if="loading" class="btn-content">
      <slot />
    </span>
    <template v-else>
      <!-- 前置图标 -->
      <span v-if="$slots.icon || icon" class="btn-icon">
        <slot name="icon">
          <component :is="icon" v-if="icon" />
        </slot>
      </span>
      <!-- 按钮内容 -->
      <slot />
      <!-- 后置图标 -->
      <span v-if="$slots.suffix" class="btn-icon">
        <slot name="suffix" />
      </span>
    </template>
  </component>
</template>

<script lang="ts" setup>
import { computed } from 'vue'

interface ButtonProps {
  /** 按钮类型 */
  type?: 'primary' | 'secondary' | 'ghost' | 'success' | 'warning' | 'error'
  /** 按钮尺寸 */
  size?: 'sm' | 'md' | 'lg' | 'xl'
  /** 是否禁用 */
  disabled?: boolean
  /** 是否加载中 */
  loading?: boolean
  /** 是否块级按钮 */
  block?: boolean
  /** 是否仅显示图标 */
  iconOnly?: boolean
  /** 前置图标组件 */
  icon?: any
  /** HTML标签类型 */
  tag?: 'button' | 'a' | 'div'
  /** 原生按钮类型 */
  nativeType?: 'button' | 'submit' | 'reset'
}

const props = withDefaults(defineProps<ButtonProps>(), {
  type: 'primary',
  size: 'md',
  disabled: false,
  loading: false,
  block: false,
  iconOnly: false,
  tag: 'button',
  nativeType: 'button',
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const buttonClass = computed(() => {
  return [
    'btn',
    `btn-${props.type}`,
    {
      [`btn-${props.size}`]: props.size !== 'md',
      'btn-block': props.block,
      'btn-icon-only': props.iconOnly,
      'btn-loading': props.loading,
      'disabled': props.disabled,
    },
  ]
})

const handleClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<style lang="scss" scoped>
/* 组件特定样式已在全局样式中定义 */
</style>