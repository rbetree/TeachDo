<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="modelValue"
        class="modal-overlay"
        :class="{ 'modal-overlay--center': center }"
        @click="handleOverlayClick"
      >
        <div
          ref="modalRef"
          class="modal-container"
          :class="[`modal-container--${size}`, modalClass]"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="title ? 'modal-title' : undefined"
          @click.stop
        >
          <!-- Header -->
          <div v-if="title || $slots.header || showClose" class="modal-header">
            <slot name="header">
              <h3 v-if="title" id="modal-title" class="modal-title">{{ title }}</h3>
            </slot>
            <button
              v-if="showClose"
              class="modal-close"
              type="button"
              aria-label="关闭对话框"
              @click="handleClose"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="modal-body" :class="bodyClass">
            <slot></slot>
          </div>

          <!-- Footer -->
          <div v-if="$slots.footer || showFooter" class="modal-footer">
            <slot name="footer">
              <button
                v-if="showCancel"
                class="btn btn-secondary"
                type="button"
                @click="handleCancel"
              >
                {{ cancelText }}
              </button>
              <button
                v-if="showConfirm"
                class="btn btn-primary"
                type="button"
                :disabled="confirmDisabled"
                @click="handleConfirm"
              >
                {{ confirmText }}
              </button>
            </slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'

/**
 * Modal 模态框组件
 * 
 * @component
 * @example
 * <Modal v-model="visible" title="提示" @confirm="handleConfirm">
 *   <p>确认要删除吗？</p>
 * </Modal>
 */

interface Props {
  /** 是否显示模态框 */
  modelValue: boolean
  /** 标题 */
  title?: string
  /** 尺寸：sm=400px, md=600px, lg=800px, xl=1000px, full=90% */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  /** 是否显示关闭按钮 */
  showClose?: boolean
  /** 是否显示底部 */
  showFooter?: boolean
  /** 是否显示取消按钮 */
  showCancel?: boolean
  /** 是否显示确认按钮 */
  showConfirm?: boolean
  /** 取消按钮文本 */
  cancelText?: string
  /** 确认按钮文本 */
  confirmText?: string
  /** 确认按钮是否禁用 */
  confirmDisabled?: boolean
  /** 点击遮罩层是否关闭 */
  closeOnClickOverlay?: boolean
  /** 按ESC键是否关闭 */
  closeOnEsc?: boolean
  /** 是否垂直居中 */
  center?: boolean
  /** 自定义模态框类名 */
  modalClass?: string
  /** 自定义内容区类名 */
  bodyClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  showClose: true,
  showFooter: true,
  showCancel: true,
  showConfirm: true,
  cancelText: '取消',
  confirmText: '确定',
  confirmDisabled: false,
  closeOnClickOverlay: true,
  closeOnEsc: true,
  center: false,
})

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'close'): void
  (e: 'cancel'): void
  (e: 'confirm'): void
}

const emit = defineEmits<Emits>()

const modalRef = ref<HTMLElement>()

const handleClose = () => {
  emit('update:modelValue', false)
  emit('close')
}

const handleCancel = () => {
  emit('cancel')
  handleClose()
}

const handleConfirm = () => {
  emit('confirm')
}

const handleOverlayClick = () => {
  if (props.closeOnClickOverlay) {
    handleClose()
  }
}

const handleEscKey = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.closeOnEsc && props.modelValue) {
    handleClose()
  }
}

// 监听模态框显示状态，控制body滚动
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    document.body.style.overflow = 'hidden'
  }
  else {
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  document.addEventListener('keydown', handleEscKey)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscKey)
  document.body.style.overflow = ''
})
</script>

<style scoped lang="scss">
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 16px;
  z-index: var(--z-modal);
  overflow-y: auto;
  
  &--center {
    align-items: center;
  }
}

.modal-container {
  background-color: var(--bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 100%;
  max-height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  margin: auto 0;
  
  &--sm {
    max-width: 400px;
  }
  
  &--md {
    max-width: 600px;
  }
  
  &--lg {
    max-width: 800px;
  }
  
  &--xl {
    max-width: 1000px;
  }
  
  &--full {
    max-width: 90%;
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--border-color);
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background-color: transparent;
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-base);
  flex-shrink: 0;
  
  &:hover {
    background-color: var(--bg-surface-secondary);
    color: var(--text-primary);
  }
  
  &:active {
    transform: scale(0.95);
  }
}

.modal-body {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  color: var(--text-primary);
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}

/* 动画效果 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--transition-slow);
  
  .modal-container {
    transition: transform var(--transition-slow), opacity var(--transition-slow);
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  
  .modal-container {
    transform: scale(0.95);
    opacity: 0;
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 20px 12px;
  }
  
  .modal-container {
    max-height: calc(100vh - 40px);
    
    &--sm,
    &--md,
    &--lg,
    &--xl {
      max-width: 100%;
    }
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding-left: 16px;
    padding-right: 16px;
  }
}
</style>