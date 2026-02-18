import type { ChatMessage, TeachingMaterial } from '#root/types';
import { ApiError, ensureBackendAvailable, requestRaw } from '@/services/apiClient';
import { SseParser } from '@/utils/sse';
import { KB_USER_ID } from '@/stores/appStore';

type AssistantRequestMessage = {
  role: 'user' | 'assistant';
  content: string;
};

function toAssistantMessages(history: ChatMessage[]): AssistantRequestMessage[] {
  const result: AssistantRequestMessage[] = [];
  for (const msg of history) {
    const content = (msg.text || '').trim();
    if (!content) continue;
    result.push({ role: msg.role === 'user' ? 'user' : 'assistant', content });
  }
  return result;
}

type AssistantMaterialContext = Pick<TeachingMaterial, 'title' | 'subject' | 'description' | 'objectives'>;

/**
 * POST /tools/assistant_chat (SSE Text delta)
 * - data: <delta text>
 * - data: {"type":"error","text":"..."} 作为结构化错误
 * - data: [DONE] 结束
 */
export async function streamAssistantReply(input: {
  messages: ChatMessage[];
  material?: AssistantMaterialContext | null;
  kbFileIds?: string[] | null;
  language?: string;
  onDelta?: (delta: string) => void;
  signal?: AbortSignal;
}): Promise<string> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  const payload = {
    messages: toAssistantMessages(input.messages),
    user_id: KB_USER_ID,
    kb_file_ids: (input.kbFileIds ?? []).map((id) => id.trim()).filter(Boolean),
    material: input.material ?? null,
    language: input.language ?? 'zh',
  };

  const response = await requestRaw(
    '/tools/assistant_chat',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    { signal: input.signal },
  );

  if (!response.body) throw new ApiError('unknown', 'No response body.');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = new SseParser();

  let finished = false;
  let fullText = '';

  try {
    while (!finished) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const messages = parser.feed(chunk);

      for (const msg of messages) {
        const raw = msg.data;
        if (!raw) continue;
        if (raw.trim() === '[DONE]') {
          finished = true;
          break;
        }

        const trimmed = raw.trim();
        if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
          try {
            const obj = JSON.parse(trimmed) as any;
            if (obj?.type === 'error') {
              throw new ApiError('backend', obj?.text || 'Assistant error.');
            }
          } catch (e) {
            if (e instanceof ApiError) throw e;
            // 不是 JSON 或解析失败：按普通文本处理
          }
        }

        fullText += raw;
        input.onDelta?.(raw);
      }
    }
  } catch (e) {
    if (input.signal?.aborted) {
      throw new ApiError('abort', 'Request aborted.', { cause: e });
    }
    throw e;
  }

  return fullText;
}
