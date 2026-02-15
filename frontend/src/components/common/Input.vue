<template>
  <div :class="groupClass">
    <!-- 标签 -->
    <label v-if="label" :for="inputId" :class="['input-label', { required }]">
      {{ label }}
    </label>

    <!-- 输入框容器 -->
    <div :class="wrapperClass">
      <!-- 前缀图标 -->
      <span v-if="$slots.prefix || prefix" class="input-prefix">
        <slot name="prefix">
          <component :is="prefix" v-if="prefix" />
        </slot>
      </span>

      <!-- 输入框/文本域 -->
      <component
        :is="type === 'textarea' ? 'textarea' : 'input'"
        :id="inputId"
        :type="computedType"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :maxlength="maxlength"
        :class="inputClass"
        @input="handleInput"
        @change="handleChange"
        @focus="handleFocus"
        @blur="handleBlur"
      />

      <!-- 后缀图标 -->
      <span
        v-if="$slots.suffix || suffix || clearable || showPasswordToggle"
        :class="['input-suffix', { clickable: clearable || showPasswordToggle }]"
        @click="handleSuffixClick"
      >
        <slot name="suffix">
          <!-- 清除按钮 -->
          <svg
            v-if="clearable && modelValue && !disabled"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          <!-- 密码显示切换 -->
          <svg
            v-else-if="showPasswordToggle"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path v-if="passwordVisible" d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle v-if="passwordVisible" cx="12" cy="12" r="3"></circle>
            <path v-else d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
            <line v-if="!passwordVisible" x1="1" y1="1" x2="23" y2="23"></line>
          </svg>
          <component :is="suffix" v-else-if="suffix" />
        </slot>
      </span>
    </div>

    <!-- 帮助文本/错误信息 -->
    <div v-if="helpText || errorMessage || $slots.help" class="input-message">
      <template v-if="status === 'error' && errorMessage">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <span>{{ errorMessage }}</span>
      </template>
      <template v-else-if="status === 'success'">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
        <span>{{ helpText }}</span>
      </template>
      <template v-else>
        <slot name="help">{{ helpText }}</slot>
      </template>
    </div>

    <!-- 字符计数 -->
    <div v-if="showCount && maxlength" :class="['input-count', { 'limit-reached': isLimitReached }]">
      {{ characterCount }} / {{ maxlength }}
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, useSlots } from 'vue'

interface InputProps {
  /** v-model 绑定值 */
  modelValue?: string | number
  /** 输入框类型 */
  type?: 'text' | 'password' | 'email' | 'number' | 'tel' | 'url' | 'search' | 'textarea'
  /** 标签文本 */
  label?: string
  /** 占位符 */
  placeholder?: string
  /** 是否禁用 */
  disabled?: boolean
  /** 是否只读 */
  readonly?: boolean
  /** 是否必填 */
  required?: boolean
  /** 最大长度 */
  maxlength?: number
  /** 是否显示字符计数 */
  showCount?: boolean
  /** 是否可清除 */
  clearable?: boolean
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg'
  /** 验证状态 */
  status?: 'success' | 'warning' | 'error' | ''
  /** 错误信息 */
  errorMessage?: string
  /** 帮助文本 */
  helpText?: string
  /** 前缀图标 */
  prefix?: any
  /** 后缀图标 */
  suffix?: any
}

const props = withDefaults(defineProps<InputProps>(), {
  type: 'text',
  disabled: false,
  readonly: false,
  required: false,
  showCount: false,
  clearable: false,
  size: 'md',
  status: '',
})

const slots = useSlots()

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  change: [value: string | number]
  focus: [event: FocusEvent]
  blur: [event: FocusEvent]
  clear: []
}>()

const passwordVisible = ref(false)
const inputId = computed(() => `input-${Math.random().toString(36).substr(2, 9)}`)

const computedType = computed(() => {
  if (props.type === 'password') {
    return passwordVisible.value ? 'text' : 'password'
  }
  return props.type === 'textarea' ? undefined : props.type
})

const showPasswordToggle = computed(() => {
  return props.type === 'password'
})

const characterCount = computed(() => {
  return String(props.modelValue || '').length
})

const isLimitReached = computed(() => {
  return props.maxlength ? characterCount.value >= props.maxlength : false
})

const groupClass = computed(() => {
  return [
    'input-group',
    {
      [props.status]: props.status,
    },
  ]
})

const wrapperClass = computed(() => {
  return [
    'input-wrapper',
    {
      'has-prefix': props.prefix || !!slots.prefix,
      'has-suffix': props.suffix || !!slots.suffix || props.clearable || showPasswordToggle.value,
      'input-password-toggle': showPasswordToggle.value,
    },
  ]
})

const inputClass = computed(() => {
  return [
    'input-field',
    {
      [`input-${props.size}`]: props.size !== 'md',
    },
  ]
})

const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement | HTMLTextAreaElement
  emit('update:modelValue', target.value)
}

const handleChange = (event: Event) => {
  const target = event.target as HTMLInputElement | HTMLTextAreaElement
  emit('change', target.value)
}

const handleFocus = (event: FocusEvent) => {
  emit('focus', event)
}

const handleBlur = (event: FocusEvent) => {
  emit('blur', event)
}

const handleSuffixClick = () => {
  if (props.clearable && props.modelValue && !props.disabled) {
    emit('update:modelValue', '')
    emit('clear')
  }
  else if (showPasswordToggle.value) {
    passwordVisible.value = !passwordVisible.value
  }
}
</script>

<style lang="scss" scoped>
/* 组件特定样式已在全局样式中定义 */
</style>
