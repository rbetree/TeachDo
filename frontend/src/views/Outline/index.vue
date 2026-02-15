<template>
  <!-- 使用 PageLayout 组件包裹整个页面 -->
  <PageLayout :current-step="2">
    <!-- 使用 Container 组件包裹内容 -->
    <Container size="lg" class="outline-container">
      <!-- 页面头部 - 对齐极简 Step 文案 -->
      <div class="page-header">
        <p class="page-step-label">Step 02 — Outline</p>
        <h2>调整结构</h2>
        <span class="text-secondary text-sm">AI 已根据您的主题生成初步大纲</span>
      </div>

      <!-- 大纲编辑器容器 - 统一容器 -->
      <div class="outline-editor-container">
        <!-- 生成中的半透明提示条 -->
        <div v-if="outlineCreating" class="generating-overlay">
          <div class="generating-badge">
            <div class="badge-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                <path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </div>
            <span class="badge-text">AI 正在生成大纲...</span>
          </div>
        </div>
        
        <!-- 统一的内容区域 - 始终存在 -->
        <div class="outline-content">
          <!-- 生成中显示实时内容 -->
          <pre v-if="outlineCreating" ref="outlineRef" class="outline-display">{{ outline }}</pre>
          
          <!-- 编辑状态显示编辑器 -->
          <OutlineEditor v-else v-model:value="outline" />
        </div>
      </div>

      <!-- 固定底部操作栏 - 与 HTML 原型保持一致 -->
      <div
        v-if="!outlineCreating"
        class="outline-action-bar"
        style="position: fixed; bottom: 40px; left: 50%; transform: translateX(-50%);"
      >
        <span class="progress-indicator">02 / 04</span>
        <Button 
          type="secondary" 
          @click="goBack"
        >
          返回
        </Button>
        <Button 
          type="primary" 
          @click="goPPT"
        >
          下一步：选择模板
        </Button>
      </div>
    </Container>
  </PageLayout>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '@/services'
import message from '@/utils/message'
import OutlineEditor from '@/components/OutlineEditor.vue'
import { PageLayout, Container, Button } from '@/components/common'
import { useMainStore } from '@/store/main'
import useOutlineStream from '@/hooks/useOutlineStream'

const router = useRouter()
const route = useRoute()
const mainStore = useMainStore()

// 从路由参数接收数据
const language = ref((route.query.language as string) || '中文')
const model = ref((route.query.model as string) || 'GLM-4.5-Air')
const topic = ref((route.query.topic as string) || '')
const hasFile = ref(route.query.hasFile === 'true')

// 大纲相关状态
const outline = ref('')
const outlineCreating = ref(false)
const outlineRef = ref<HTMLElement>()

// 抽取的流式处理逻辑
const { streamFromResponse } = useOutlineStream({ outline, outlineRef })

// 页面挂载时自动生成大纲
onMounted(async () => {
  // 主题是必填的
  const hasTopic = topic.value.trim().length > 0

  if (!hasTopic) {
    message.warning('请先输入主题')
    router.push('/')
    return
  }

  // 使用统一 API 生成大纲
  await generateOutlineUnified()
})

// 统一的大纲生成函数
const generateOutlineUnified = async () => {
  const file = mainStore.uploadedFile

  outlineCreating.value = true

  try {
    // 调用统一的 API，主题始终传递
    const response = await api.AIPPT_Outline_Unified({
      content: topic.value.trim(),
      file: file || undefined,
      language: language.value,
      userId: 'default_user',
    })

    await streamFromResponse(response)

    // 根据是否有文件设置状态
    mainStore.setOutlineFromFile(!!file)

    if (file) {
      message.success('已结合文档生成大纲')
    }
  }
  catch (error) {
    message.error('生成失败，请重试')
    // eslint-disable-next-line no-console
    console.error('生成大纲失败:', error)
  }
  finally {
    outlineCreating.value = false
  }
}

// 返回上一步
const goBack = () => {
  router.push('/')
}

// 跳转到模板选择页
const goPPT = () => {
  if (!outline.value.trim()) {
    message.error('请先生成大纲内容')
    return
  }

  router.push({
    name: 'PPT',
    query: {
      outline: outline.value,
      language: language.value,
      model: model.value,
    }
  })
}
</script>

<style lang="scss" scoped>
/* 容器布局 */
.outline-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 900px;
  height: 100%;
}

/* V3.1.2: 页面头部样式 */
.page-header {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-xl);
  
  .page-step-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
  }
  
  h2 {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
  }
  
  .text-secondary {
    color: var(--text-secondary);
    font-size: 0.875rem;
  }
}

/* 大纲编辑器容器 - 固定大小，统一样式 */
.outline-editor-container {
  position: relative;
  width: 100%;
  height: 600px;
  min-height: 600px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--spacing-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 生成中的覆盖层 - 半透明徽章 */
.generating-overlay {
  position: absolute;
  top: var(--spacing-md);
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  pointer-events: none;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

/* 紧凑的生成提示徽章 */
.generating-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  background-color: rgba(var(--primary-color-rgb, 0, 0, 0), 0.9);
  color: white;
  border-radius: var(--radius-full);
  font-size: 0.875rem;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(8px);
}

[data-theme="dark"] .generating-badge {
  color: #000000;
}

.badge-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  animation: spin 2s linear infinite;
  
  svg {
    display: block;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.badge-text {
  white-space: nowrap;
}

/* 统一的内容区域 - 固定高度，内容溢出滚动 */
.outline-content {
  flex: 1;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--spacing-xl);
  background-color: var(--bg-surface);
  
  /* 自定义滚动条 */
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-track {
    background: var(--bg-surface-secondary);
    border-radius: 3px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 3px;
    
    &:hover {
      background: var(--text-secondary);
    }
  }
  
  /* 生成中的大纲显示 - 与编辑器保持一致的背景 */
  .outline-display {
    color: var(--text-primary);
    line-height: 1.8;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: system-ui, -apple-system, sans-serif;
    background-color: transparent;
    border-radius: var(--radius-md);
    padding: 0;
    margin: 0;
    min-height: 100%;
  }
}

/* 固定底部操作栏样式 - 对齐 HTML Action Bar */
.outline-action-bar {
  position: fixed;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 1rem;
  background-color: var(--bg-body);
  padding: 12px 24px;
  border-radius: 999px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--border-color);
  z-index: 100;
}

.progress-indicator {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-right: 0.75rem;
  padding-right: 0.75rem;
  border-right: 1px solid var(--border-color);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    h2 {
      font-size: 1.5rem;
    }
  }
  
  /* 移动端容器保持固定大小 */
  .outline-editor-container {
    height: 500px;
    min-height: 500px;
  }
  
  /* 移动端提示徽章 */
  .generating-badge {
    font-size: 0.8125rem;
    padding: 6px var(--spacing-sm);
    
    .badge-icon svg {
      width: 14px;
      height: 14px;
    }
  }
  
  /* 移动端内容区域 */
  .outline-content {
    padding: var(--spacing-md);
    
    .outline-display {
      font-size: 0.9rem;
    }
  }
  
  /* 移动端操作栏 */
  .action-bar {
    flex-direction: column-reverse;
    
    :deep(.btn) {
      width: 100%;
    }
  }
}
</style>
