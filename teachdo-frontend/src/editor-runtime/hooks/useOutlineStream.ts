import type { Ref } from 'vue'
import useAIPPT from './useAIPPT'

interface UseOutlineStreamOptions {
  outline: Ref<string>
  outlineRef?: Ref<HTMLElement | undefined>
}

export default function useOutlineStream(options: UseOutlineStreamOptions) {
  const { outline, outlineRef } = options
  const { getMdContent } = useAIPPT()

  /**
   * 将后端返回的流式 Response 读入到 outline 中。
   * 后端使用 SSE (text/event-stream) 输出，格式与内容生成接口保持一致：
   *   data: <payload>\n\n
   * 其中 payload 为大纲的增量文本片段，结束时 payload 为 "[DONE]"。
   */
  const streamFromResponse = async (response: Response): Promise<void> => {
    if (!response.body) {
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')

    // 清空旧内容
    outline.value = ''

    let buffer = ''

    // 逐 chunk 读取并解析 SSE 事件
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE 事件以空行分隔
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''

      for (const evt of events) {
        // 提取 data: 行，拼成 payload
        const dataLines = evt
          .split('\n')
          .filter(line => line.startsWith('data:'))
          .map(line => line.slice(5).trimStart())

        const payload = dataLines.join('\n')
        if (!payload) continue

        if (payload === '[DONE]') {
          // 显式结束，直接跳出
          buffer = ''
          break
        }

        // 对于大纲，我们直接把 payload 当作增量文本拼接
        outline.value += payload

        // 自动滚动到底部 - 滚动父容器而不是 pre 元素本身
        if (outlineRef?.value && outlineRef.value.parentElement) {
          const parent = outlineRef.value.parentElement
          parent.scrollTop = parent.scrollHeight
        }
      }
    }

    // 统一后处理：提取 markdown 内容并去掉 think/注释块
    outline.value = getMdContent(outline.value)
    outline.value = outline.value
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/<think>[\s\S]*?<\/think>/g, '')
  }

  return {
    streamFromResponse,
  }
}
