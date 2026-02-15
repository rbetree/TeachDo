<template>
  <PageLayout :current-step="3">
    <Container size="lg" class="ppt-container">
      <!-- 页面头部 -->
      <div class="page-header">
        <p class="page-step-label">Step 03 — Visuals</p>
        <h2 class="page-title">选择设计风格</h2>
        <p class="page-subtitle">从下方挑选合适的模板，开始生成 PPT</p>
      </div>

      <!-- 选项区域（根据上传文件生成、使用网络搜索） -->
      <div v-if="isOutlineFromFile" class="generate-options">
        <Checkbox v-model:value="generateFromUploadedFile">
          根据上传的文件生成PPT
        </Checkbox>
        <Checkbox v-model:value="generateFromWebSearch">
          使用网络搜索生成PPT
        </Checkbox>
      </div>

      <!-- 模板网格 -->
      <div class="template-grid">
        <Card
          v-for="template in templates"
          :key="template.id"
          :cover="template.cover"
          :cover-alt="template.name"
          hoverable
          clickable
          selectable
          :selected="selectedTemplate === template.id"
          :disabled="loading"
          @click="!loading && (selectedTemplate = template.id)"
        >
          <div class="template-info">
            <span class="template-name">{{ template.name || '经典模板' }}</span>
          </div>
        </Card>
      </div>

      <!-- 固定底部操作栏 -->
      <div
        class="ppt-action-bar"
        style="position: fixed; bottom: 40px; left: 50%; transform: translateX(-50%);"
      >
        <span class="progress-indicator">03 / 04</span>
        <Button
          type="secondary"
          size="lg"
          :disabled="loading"
          @click="$router.back()"
        >
          返回修改大纲
        </Button>
        <Button
          type="primary"
          size="lg"
          :disabled="loading || !selectedTemplate"
          :loading="loading"
          @click="createPPT"
        >
          {{ loading ? '正在生成…' : '生成演示文稿' }}
        </Button>
      </div>
    </Container>
  </PageLayout>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import api from '@/services'
import useAIPPT from '@/hooks/useAIPPT'
import useAddSlidesOrElements from '@/hooks/useAddSlidesOrElements'
import useSlideHandler from '@/hooks/useSlideHandler'
import type { AIPPTSlide } from '@/types/AIPPT'
import type { Slide, SlideTheme } from '@/types/slides'
import { useMainStore, useSlidesStore } from '@/store'
import { PageLayout, Container, Card, Button } from '@/components/common'
import Checkbox from '@/components/Checkbox.vue'

const route = useRoute()
const router = useRouter()
const mainStore = useMainStore()
const slideStore = useSlidesStore()
const { templates } = storeToRefs(slideStore)
const { sessionId, isOutlineFromFile, generateFromUploadedFile, generateFromWebSearch } =
  storeToRefs(mainStore)

const { AIPPTGenerator, presetImgPool } = useAIPPT()
const { addSlidesFromDataToEnd } = useAddSlidesOrElements()
const { isEmptySlide } = useSlideHandler()

const outline = ref(route.query.outline as string)
const language = ref(route.query.language as string)
const model = ref(route.query.model as string)
const style = ref('通用')
const selectedTemplate = ref<string>('')
const loading = ref(false)

onMounted(async () => {
  await slideStore.fetchTemplates()
  selectedTemplate.value = templates.value?.[0]?.id || ''
})

const createPPT = async () => {
  if (!selectedTemplate.value) return
  mainStore.setGenerating(true)
  loading.value = true

  slideStore.resetSlides()

  router.push(`/editor?session_id=${sessionId.value}`)

  try {
    const stream = await api.AIPPT_Content({
      content: outline.value,
      language: language.value,
      style: style.value,
      model: model.value,
      generateFromUploadedFile: generateFromUploadedFile.value,
      generateFromWebSearch: generateFromWebSearch.value,
      sessionId: sessionId.value,
    })

    // 初始化图片池（mock 兜底）
    const mockImgs = await api.getMockData('imgs')
    presetImgPool(mockImgs)

    const templateData = await api.getFileData(selectedTemplate.value)
    const templateSlides: Slide[] = templateData.slides
    const templateTheme: SlideTheme = templateData.theme
    slideStore.setTheme(templateTheme)

    // 根据模板的宽度和高度动态设置 viewportSize 和 viewportRatio
    if (templateData.width && templateData.height) {
      slideStore.setViewportSize(templateData.width)
      slideStore.setViewportRatio(templateData.height / templateData.width)
    }

    const reader: ReadableStreamDefaultReader<Uint8Array> = stream.body!.getReader()
    const decoder = new TextDecoder('utf-8')

    let buffer = '' // 用来跨 chunk 缓存

    const processEvent = (evt: string) => {
      // evt 是一条完整的 SSE 事件（不包含尾部空行）
      // 兼容多行 data:，拼接起来
      const dataLines = evt
        .split('\n')
        .filter(l => l.startsWith('data:'))
        .map(l => l.slice(5).trimStart()) // 去掉 'data: '

      const payload = dataLines.join('\n')

      if (!payload) return
      if (payload === '[DONE]') {
        loading.value = false
        mainStore.setAIPPTDialogState(false)
        mainStore.setGenerating(false)
        return 'DONE'
      }

      // 某些模型可能会包围 ```json``` fence，这里做容错
      const jsonText = payload.replace(/```json|```/g, '').trim()

      try {
        const slide: AIPPTSlide = JSON.parse(jsonText)

        // 处理后端返回的图片池
        if (slide.images?.length) {
          const backendImages = slide.images.map((img: any) => ({
            id: img.id || Math.random().toString(),
            src: img.src,
            width: img.width || 1920,
            height: img.height || 1080
          }))
          presetImgPool(backendImages)
        }

        // 用模板生成并插入
        const slideGenerator = AIPPTGenerator(templateSlides, [slide])
        for (const generatedSlide of slideGenerator) {
          if (isEmptySlide.value) {
            slideStore.setSlides([generatedSlide])
          }
          else {
            addSlidesFromDataToEnd([generatedSlide])
          }
        }
      }
      catch (e) {
        // 如果这条不是完整 JSON（比如后端按"文本片段"流），可以考虑改成累积 JSON 方案
        console.warn('解析 JSON 失败，跳过本条事件：', e, jsonText)
      }
    }

    const pump = (): any =>
      reader.read().then(({ done, value }) => {
        if (done) {
          // 读流结束：兜底把缓冲里最后一条尝试处理
          if (buffer.trim()) {
            const status = processEvent(buffer)
            buffer = ''
            if (status === 'DONE') return
          }
          loading.value = false
          mainStore.setGenerating(false)
          return
        }

        buffer += decoder.decode(value, { stream: true })

        // SSE 以空行分隔事件：\n\n（注意：可能是 \r\n\r\n）
        const parts = buffer.split(/\r?\n\r?\n/)
        // 最后一段可能是不完整，留在缓冲
        buffer = parts.pop() || ''

        for (const evt of parts) {
          const status = processEvent(evt)
          if (status === 'DONE') {
            reader.cancel()
            return
          }
        }

        return pump()
      })

    await pump()
  }
  catch (e) {
    loading.value = false
    mainStore.setGenerating(false)
    // eslint-disable-next-line no-console
    console.error(e)
  }
}
</script>

<style lang="scss" scoped>
/* 容器布局 */
.ppt-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* 页面头部 */
.page-header {
  text-align: center;
  margin-bottom: var(--spacing-lg);
  flex-shrink: 0;
}

.page-step-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xs);
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-sm) 0;
  letter-spacing: -0.025em;
}

.page-subtitle {
  font-size: 1rem;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

/* 生成选项 */
.generate-options {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  box-shadow: var(--shadow-sm);
}

/* 模板网格布局 */
.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  width: 100%;
  flex: 1;
  overflow-y: auto;
  align-content: start;
}

/* 模板信息 */
.template-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.template-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

/* 固定底部操作栏 */
.ppt-action-bar {
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
  .page-title {
    font-size: 1.5rem;
  }

  .page-subtitle {
    font-size: 0.875rem;
  }

  .template-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-md);
  }

  .action-bar {
    flex-direction: column-reverse;
    gap: var(--spacing-sm);

    :deep(.btn) {
      width: 100%;
    }
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 1.25rem;
  }
}
</style>
