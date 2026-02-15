<template>
  <div class="loading-container" :class="containerClass">
    <Spinner :variant="variant" :size="size" :color="color" />
    
    <div v-if="text || $slots.default" class="loading-content">
      <h3 v-if="text" class="loading-text">{{ text }}</h3>
      <slot></slot>
    </div>
    
    <div v-if="showProgress" class="loading-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
      </div>
      <span class="progress-text">{{ progress }}%</span>
    </div>
    
    <p v-if="description" class="loading-description">{{ description }}</p>
  </div>
</template>

<script setup lang="ts">
import Spinner from './Spinner.vue'

/**
 * Loading 加载组件（带进度提示）
 * 
 * @component
 * @example
 * <Loading text="正在生成演示文稿..." description="AI 正在撰写内容并应用设计，请稍候" />
 * <Loading text="上传中..." :progress="uploadProgress" show-progress />
 */

interface Props {
  /** 主要提示文本 */
  text?: string
  /** 描述文本 */
  description?: string
  /** Spinner变体 */
  variant?: 'primary' | 'secondary' | 'white'
  /** Spinner尺寸 */
  size?: 'sm' | 'md' | 'lg' | 'xl'
  /** 自定义颜色 */
  color?: string
  /** 是否显示进度条 */
  showProgress?: boolean
  /** 进度值 (0-100) */
  progress?: number
  /** 自定义容器类名 */
  containerClass?: string
}

withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'lg',
  showProgress: false,
  progress: 0,
})
</script>

<style scoped lang="scss">
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 200px;
}

.loading-content {
  margin-top: 24px;
  text-align: center;
  max-width: 500px;
}

.loading-text {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.loading-description {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 16px 0 0 0;
  text-align: center;
  max-width: 400px;
}

.loading-progress {
  margin-top: 24px;
  width: 100%;
  max-width: 300px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background-color: var(--bg-surface-secondary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-hover) 100%);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--primary-color);
  text-align: center;
}

/* 响应式 */
@media (max-width: 768px) {
  .loading-container {
    padding: 30px 16px;
  }
  
  .loading-text {
    font-size: 1.125rem;
  }
}
</style>