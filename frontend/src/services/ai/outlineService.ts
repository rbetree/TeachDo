import type { TeachingMaterial } from '#root/types';
import { SseParser } from '@/utils/sse';
import { ApiError, ensureBackendAvailable, requestRaw } from '@/services/apiClient';
import { KB_USER_ID } from '@/stores/appStore';

/**
 * POST /tools/aippt_outline_unified (SSE Text)
 */
export async function generateOutline(
  material: TeachingMaterial,
  onStream?: (text: string) => void,
  opts: { signal?: AbortSignal } = {},
): Promise<string> {
  if (opts.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  const topic = material.title?.trim();
  if (!topic) throw new ApiError('unknown', 'Unit title is required to generate outline.');

  const content = [
    `主题：${topic}`,
    material.subject ? `学科：${material.subject}` : '',
    material.description ? `背景/简介：${material.description}` : '',
    material.objectives ? `教学目标：${material.objectives}` : '',
  ]
    .filter(Boolean)
    .join('\n');

  const formData = new FormData();
  formData.append('content', content);
  formData.append('language', 'chinese');
  formData.append('user_id', KB_USER_ID);
  for (const fileId of new Set((material.kbFileIds ?? []).map((id) => id.trim()).filter(Boolean))) {
    formData.append('kb_file_ids', fileId);
  }

  const response = await requestRaw(
    '/tools/aippt_outline_unified',
    {
      method: 'POST',
      body: formData,
    },
    { signal: opts.signal },
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
        fullText += raw;
        onStream?.(fullText);
      }
    }
  } catch (e) {
    if (opts.signal?.aborted) {
      throw new ApiError('abort', 'Request aborted.', { cause: e });
    }
    throw e;
  }

  return fullText;
}
