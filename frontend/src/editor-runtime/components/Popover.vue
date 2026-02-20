<template>
  <div class="popover" :class="{ 'center': center }" ref="triggerRef">
    <div class="popover-content" :style="contentStyle" ref="contentRef">
      <slot name="content" v-if="contentVisible"></slot>
    </div>
    <slot></slot>
  </div>
</template>

<script lang="ts" setup>
import { type CSSProperties, onMounted, onUnmounted, ref, watch, computed, useTemplateRef } from 'vue'
import tippy, { type Instance, type Placement } from 'tippy.js'

import 'tippy.js/animations/scale.css'

const props = withDefaults(defineProps<{
  value?: boolean
  trigger?: 'click' | 'mouseenter' | 'manual'
  placement?: Placement
  appendTo?: HTMLElement | 'parent'
  contentStyle?: CSSProperties
  center?: boolean
  offset?: number
}>(), {
  value: false,
  trigger: 'click',
  placement: 'bottom',
  center: false,
  offset: 8,
})

const emit = defineEmits<{
  (event: 'update:value', payload: boolean): void
  (event: 'show'): void
  (event: 'hide'): void
}>()

const instance = ref<Instance>()
const contentVisible = ref(false)
const triggerRef = useTemplateRef<HTMLElement>('triggerRef')
const contentRef = useTemplateRef<HTMLElement>('contentRef')

const contentStyle = computed(() => {
  return props.contentStyle || {}
})

watch(() => props.value, () => {
  if (!instance.value) return
  if (props.value) instance.value.show()
  else instance.value.hide()
})

onUnmounted(() => {
  if (instance.value) instance.value.destroy()
})

onMounted(() => {
  instance.value = tippy(triggerRef.value!, {
    content: contentRef.value!,
    allowHTML: true,
    trigger: props.trigger,
    placement: props.placement,
    interactive: true,
    appendTo: props.appendTo || document.body,
    maxWidth: 'none',
    offset: [0, props.offset],
    duration: 200,
    animation: 'scale',
    theme: 'popover',
    onShow() {
      contentVisible.value = true
    },
    onShown() {
      if (!props.value) {
        emit('update:value', true)
        emit('show')
      }
    },
    onHidden() {
      if (props.value) {
        emit('update:value', false)
        emit('hide')
      }
      contentVisible.value = false
    },
  })
})
</script>

<style lang="scss" scoped>
.popover.center {
  display: flex;
  justify-content: center;
  align-items: center;
}
.popover-content {
  background-color: #ffffff;
  padding: 10px;
  border: 1px solid #e5e5e5;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, .1), 0 2px 4px -2px rgba(0, 0, 0, .1);
  border-radius: 2px;
  font-size: 13px;
  color: #333333;
}
</style>

<style lang="scss">
/* 强制所有 Popover 使用浅色主题（即使在暗黑模式下） */
.tippy-box[data-theme~='popover'] {
  border: 0;
  outline: 0;
  background-color: #ffffff !important;
  color: #333333 !important;
  
  /* 强制所有子元素也使用浅色主题 */
  * {
    background-color: inherit;
    color: inherit;
  }
  
  .popover-content {
    background-color: #ffffff !important;
    color: #333333 !important;
    border: 1px solid #e5e5e5 !important;
  }
}
</style>