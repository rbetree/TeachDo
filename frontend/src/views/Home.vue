<template>
  <PageLayout :currentStep="1">
    <!-- Error Modal -->
    <Modal
      v-model="showErrorModal"
      :title="errorTitle"
      size="sm"
      :show-cancel="false"
      confirm-text="我知道了"
      @confirm="closeErrorModal"
    >
      <p style="color: var(--text-primary); line-height: 1.6;">{{ errorMessage }}</p>
    </Modal>

    <!-- Hero Section -->
    <section class="home-hero">
      <div class="hero-container">
        <div class="hero-content">
          <p class="hero-step-label">Step 01 — Topic</p>
          <h1 class="hero-title">
            What will you<br />create today?
          </h1>

          <!-- 统一输入区域 -->
          <div class="input-section unified-input">
            <!-- 主题输入 -->
            <div class="input-wrapper">
              <input
                v-model="topic"
                type="text"
                class="topic-field"
                placeholder="输入 PPT 主题，例如：2025年人工智能发展趋势..."
                @keyup.enter="handlePrimaryClick"
              />
            </div>

            <!-- 文件附件区域 -->
            <div class="attachment-section">
              <!-- 已选择文件显示 -->
              <div v-if="selectedFile" class="selected-file-card compact">
                <div class="file-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                  </svg>
                </div>
                <div class="file-info">
                  <div class="file-name">{{ selectedFileInfo?.name }}</div>
                  <div class="file-size">{{ selectedFileInfo?.size }}</div>
                </div>
                <button class="btn-clear" @click.stop="clearSelectedFile" title="移除文件">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>

              <!-- 添加文件按钮 -->
              <button
                v-else
                class="attach-file-btn"
                @click="triggerFileInput"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                </svg>
                <span>附加参考文档（可选）</span>
              </button>
              <input
                ref="fileInput"
                type="file"
                accept=".pdf,.docx,.md"
                style="display: none"
                @change="handleFileSelect"
              />
            </div>

            <!-- Language and Model Selector -->
            <div class="settings-row">
              <div class="select-wrapper">
                <select
                  id="language-select"
                  v-model="language"
                  class="minimal-select"
                >
                  <option value="中文">中文</option>
                  <option value="English">English</option>
                  <option value="日本語">日本語</option>
                </select>
                <div class="select-arrow">▼</div>
              </div>

              <div class="select-wrapper">
                <select
                  id="model-select"
                  v-model="model"
                  class="minimal-select"
                >
                  <option value="GLM-4.5-Air">GLM-4.5-Air</option>
                  <option value="GLM-4.5-Plus">GLM-4.5-Plus</option>
                  <option value="deepseek-chat">DeepSeek-Chat</option>
                  <option value="claude-3-5-sonnet">Claude-3.5-Sonnet</option>
                  <option value="gpt-4o">GPT-4o</option>
                </select>
                <div class="select-arrow">▼</div>
              </div>
            </div>

            <!-- 输入提示 -->
            <p class="input-hint">
              {{ selectedFile ? '将结合文档内容生成 PPT' : '可附加参考文档辅助生成' }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Fixed Action Bar -->
    <div
      class="home-action-bar"
      style="position: fixed; bottom: 40px; left: 50%; transform: translateX(-50%);"
    >
      <span class="progress-indicator">01 / 04</span>
      <button
        class="action-btn action-btn-secondary"
        type="button"
        disabled
      >
        返回
      </button>
      <button
        class="action-btn action-btn-primary"
        type="button"
        :disabled="primaryDisabled"
        @click="handlePrimaryClick"
      >
        <Spinner v-if="loading" size="sm" variant="white" />
        <span v-if="loading">创建中...</span>
        <span v-else>开始创作</span>
      </button>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { PageLayout, Modal, Spinner } from '@/components/common'
import message from '@/utils/message'
import { useMainStore } from '@/store/main'

const router = useRouter()
const mainStore = useMainStore()

const topic = ref('')
const language = ref('中文') // 语言选择，默认中文
const model = ref('GLM-4.5-Air') // 模型配置，默认 GLM-4.5-Air
const selectedFile = ref<File | null>(null)
const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref<HTMLInputElement>()
const showErrorModal = ref(false)
const errorMessage = ref('')
const errorTitle = ref('操作失败')

// 禁用逻辑：主题是必填的
const primaryDisabled = computed(() => {
  if (loading.value) return true
  // 主题是必填的
  return !topic.value.trim()
})

// 统一的处理函数
const handlePrimaryClick = () => {
  handleStartCreation()
}

// 文件验证配置
const FILE_CONFIG = {
  maxSize: 10 * 1024 * 1024, // 10MB
  allowedTypes: ['.pdf', '.docx', '.md'],
  allowedMimeTypes: [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/markdown',
    'text/plain'
  ]
}

// 验证文件类型
const validateFileType = (file: File): boolean => {
  const fileName = file.name.toLowerCase()
  const hasValidExtension = FILE_CONFIG.allowedTypes.some(ext => fileName.endsWith(ext))
  const hasValidMimeType = FILE_CONFIG.allowedMimeTypes.includes(file.type)
  
  return hasValidExtension || hasValidMimeType
}

// 验证文件大小
const validateFileSize = (file: File): boolean => {
  return file.size <= FILE_CONFIG.maxSize
}

// 格式化文件大小显示
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 选中的文件信息显示
const selectedFileInfo = computed(() => {
  if (!selectedFile.value) return null
  return {
    name: selectedFile.value.name,
    size: formatFileSize(selectedFile.value.size)
  }
})

// 监听文件选择，进行验证
watch(selectedFile, (newFile) => {
  if (newFile) {
    // 验证文件类型
    if (!validateFileType(newFile)) {
      message.error('文件格式不支持，请上传 PDF、DOCX 或 MD 格式的文件')
      selectedFile.value = null
      if (fileInput.value) {
        fileInput.value.value = ''
      }
      return
    }
    
    // 验证文件大小
    if (!validateFileSize(newFile)) {
      message.error(`文件大小超过限制，最大支持 ${formatFileSize(FILE_CONFIG.maxSize)}`)
      selectedFile.value = null
      if (fileInput.value) {
        fileInput.value.value = ''
      }
      return
    }
    
    message.success(`文件 "${newFile.name}" 已选择`)
  }
})

const handleStartCreation = async () => {
  const hasTopic = topic.value.trim().length > 0
  const hasFile = selectedFile.value !== null

  // 主题是必填的
  if (!hasTopic) {
    showError('输入错误', '请输入PPT主题')
    return
  }

  // 验证主题长度
  if (topic.value.trim().length < 4) {
    showError('输入错误', 'PPT主题至少需要4个字符，请输入更详细的主题描述')
    return
  }

  if (topic.value.trim().length > 200) {
    showError('输入错误', 'PPT主题不能超过200个字符，请精简您的描述')
    return
  }

  // 如果有文件，验证文件
  if (hasFile) {
    if (!validateFileType(selectedFile.value!)) {
      showError('文件格式错误', '不支持的文件格式，请上传PDF、DOCX或MD格式的文档')
      clearSelectedFile()
      return
    }

    if (!validateFileSize(selectedFile.value!)) {
      showError('文件过大', `文件大小超过限制（最大${formatFileSize(FILE_CONFIG.maxSize)}），请选择更小的文件`)
      clearSelectedFile()
      return
    }
  }

  if (loading.value) return

  loading.value = true

  try {
    // 显示加载提示
    message.success('开始创建，正在跳转到大纲编辑页...')

    // 如果有文件，保存到全局状态
    if (hasFile) {
      mainStore.setUploadedFile(selectedFile.value)
      mainStore.setOutlineFromFile(true)
    }
    else {
      mainStore.setUploadedFile(null)
      mainStore.setOutlineFromFile(false)
    }

    // 统一跳转到大纲编辑页
    await router.push({
      path: '/outline',
      query: {
        topic: hasTopic ? topic.value.trim() : undefined,
        hasFile: hasFile ? 'true' : undefined,
        fileName: hasFile ? selectedFile.value!.name : undefined,
        language: language.value,
        model: model.value,
      },
    })
  }
  catch (error) {
    console.error('导航失败:', error)
    loading.value = false
    showError('导航失败', '页面跳转时发生错误，请检查网络连接后重试')
  }
}

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    selectedFile.value = input.files[0]
  }
}

const handleFileDrop = (event: DragEvent) => {
  isDragOver.value = false
  const files = event.dataTransfer?.files
  if (files && files[0]) {
    selectedFile.value = files[0]
  }
}

// 清除选中的文件
const clearSelectedFile = () => {
  selectedFile.value = null
  mainStore.setUploadedFile(null)
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 显示错误对话框
const showError = (title: string, msg: string) => {
  errorTitle.value = title
  errorMessage.value = msg
  showErrorModal.value = true
}

// 关闭错误对话框
const closeErrorModal = () => {
  showErrorModal.value = false
}
</script>

<style scoped lang="scss">
.home-hero {
  display: flex;
  justify-content: center;
  padding: 80px 20px 72px;
  animation: fadeIn 0.6s ease-out;
  width: 100%;
}

.hero-container {
  width: 100%;
  max-width: 960px; /* 设置为标准且美观的宽度 */
  margin: 0 auto;
}

.hero-content {
  text-align: center;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.hero-step-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
}

.hero-title {
  font-size: 3rem;
  font-weight: 600;
  line-height: 1.2;
  margin-bottom: 1rem;
  letter-spacing: -0.03em;
  letter-spacing: -0.025em;
  
  @media (max-width: 768px) {
    font-size: 2rem;
  }
}

.hero-subtitle {
  font-size: 1.125rem;
  color: var(--text-secondary);
  margin-bottom: 2.5rem;
  line-height: 1.6;
}

/* Input Section */
.input-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  width: 100%;
}

/* 统一输入区域 */
.unified-input {
  width: 100%;

  .input-wrapper {
    width: 100%;
  }

  .topic-field {
    width: 100%;
    padding: 1rem 0;
    border-radius: 0;
    border: none;
    border-bottom: 1px solid var(--border-color);
    background-color: transparent;
    color: var(--text-primary);
    font-size: 1.4rem;
    outline: none;
    transition: all 0.2s ease;
    min-height: 48px;

    &::placeholder {
      color: var(--text-secondary);
      opacity: 0.6;
    }

    &:focus {
      border-bottom-color: var(--text-primary);
    }

    @media (max-width: 768px) {
      font-size: 1rem;
      padding: 0.875rem 1rem;

      &:focus {
        font-size: 16px;
      }
    }
  }

  .settings-row {
    display: flex;
    gap: 1rem;
    margin-top: 1.5rem;
    width: 100%;
    justify-content: flex-start;

    @media (max-width: 768px) {
      gap: 0.75rem;
      margin-top: 1rem;
      flex-wrap: wrap;
      justify-content: center;
    }
  }

  .input-hint {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin: 0;
    text-align: center;
  }
}

/* 文件附件区域 */
.attachment-section {
  width: 100%;
  display: flex;
  justify-content: flex-start;
}

.attach-file-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--text-primary);
    color: var(--text-primary);
    background-color: var(--bg-surface);
  }

  svg {
    flex-shrink: 0;
  }
}

.select-wrapper {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
}

.minimal-select {
  width: 100%;
  appearance: none;
  background-color: var(--bg-surface);
  border: none;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 0.9rem;
  color: var(--text-primary);
  cursor: pointer;
}

.select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  font-size: 0.7rem;
  color: var(--text-secondary);
}

.selected-file-card {
  border: 1px solid var(--primary-color);
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  background-color: var(--bg-surface);
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  animation: slideIn 0.3s ease-out;

  .file-icon {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    background-color: rgba(0, 0, 0, 0.04);
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: center;

    svg {
      color: var(--primary-color);
    }
  }

  .file-info {
    flex: 1;
    min-width: 0;
    text-align: left;

    .file-name {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-primary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 200px;
    }

    .file-size {
      font-size: 0.75rem;
      color: var(--text-secondary);
    }
  }

  .btn-clear {
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    min-width: 28px;
    min-height: 28px;
    border-radius: 50%;
    border: none;
    background-color: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    user-select: none;
    -webkit-tap-highlight-color: transparent;

    &:hover {
      background-color: var(--bg-surface-secondary);
      color: var(--text-primary);
    }

    &:active {
      transform: scale(0.95);
    }
  }
  
  @media (max-width: 768px) {
    padding: 1rem;
    gap: 0.75rem;
    
    .file-icon {
      width: 40px;
      height: 40px;
      
      svg {
        width: 24px;
        height: 24px;
      }
    }
    
    .file-info {
      .file-name {
        font-size: 0.875rem;
      }
      
      .file-size {
        font-size: 0.75rem;
      }
    }
    
    .btn-clear {
      width: 40px;
      height: 40px;
      min-width: 40px;
      min-height: 40px;
    }
  }
}

.upload-area {
  width: 100%;
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-lg);
  padding: 3rem 2rem;
  background-color: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  min-height: 180px;

  svg {
    color: var(--primary-color);
    transition: transform 0.2s ease;
  }

  &:hover,
  &.drag-over {
    border-color: var(--text-primary);
    background-color: var(--bg-surface);

    svg {
      transform: translateY(-4px);
    }
  }
  
  &:active {
    transform: scale(0.99);
  }

  .upload-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .upload-hint {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin: 0;
  }
  
  @media (max-width: 768px) {
    padding: 2rem 1.5rem;
    min-height: 160px;
    
    svg {
      width: 40px;
      height: 40px;
    }
    
    .upload-title {
      font-size: 0.8125rem;
    }
    
    .upload-hint {
      font-size: 0.75rem;
    }
  }
}

.btn-start {
  padding: 1rem 3rem;
  border-radius: var(--radius-full);
  border: none;
  background: var(--primary-color);
  color: white;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.16);
  min-height: 48px;
  position: relative;
  user-select: none;
  -webkit-tap-highlight-color: transparent;

  svg {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
  }

  &:hover:not(:disabled) {
    background: var(--primary-hover);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none !important;
  }
  
  @media (max-width: 768px) {
    padding: 1rem 2rem;
    font-size: 1rem;
    min-height: 48px;
    width: 100%;
    max-width: 100%;
    
    &:active:not(:disabled) {
      transform: scale(0.98);
    }
  }
}

/* Fixed bottom action bar - 对齐 HTML 原型样式 */
.home-action-bar {
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

.action-btn {
  padding: 10px 24px;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: transparent;

  &:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
}

.action-btn-primary {
  background-color: var(--text-primary);
  color: var(--bg-body);

  &:hover:not(:disabled) {
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
}

.action-btn-secondary {
  color: var(--text-primary);

  &:hover:not(:disabled) {
    background-color: var(--bg-surface);
  }
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
