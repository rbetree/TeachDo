import type { LessonPlan, LessonStyle, TeachingMaterial } from '#root/types';
import { ApiError, ensureBackendAvailable, requestRaw } from '@/services/apiClient';
import { SseParser, stripJsonCodeFence } from '@/utils/sse';
import { KB_USER_ID } from '@/stores/appStore';

export type LessonPlanStreamEvent =
  | { type: 'section'; section: 'objectives'; data: string[] }
  | { type: 'section'; section: 'materials'; data: string[] }
  | { type: 'section'; section: 'procedure'; data: Array<{ step: string; duration: string; activity: string }> }
  | { type: 'section'; section: 'homework'; data: string }
  | { type: 'final'; data: LessonPlan }
  | { type: 'error'; text: string };

function parseContentDispositionFilename(value: string | null): string | null {
  if (!value) return null;

  // RFC 5987: filename*=UTF-8''...
  const star = value.match(/filename\*\s*=\s*(?:UTF-8''|utf-8'')?([^;]+)/);
  if (star?.[1]) {
    const raw = star[1].trim().replace(/^"|"$/g, '');
    try {
      return decodeURIComponent(raw);
    } catch {
      return raw;
    }
  }

  const plain = value.match(/filename\s*=\s*([^;]+)/i);
  if (plain?.[1]) {
    return plain[1].trim().replace(/^"|"$/g, '');
  }

  return null;
}

/**
 * POST /tools/lesson_plan (SSE, JSON events)
 */
export async function streamLessonPlan(input: {
  material: TeachingMaterial;
  language?: string;
  onEvent?: (event: LessonPlanStreamEvent) => void;
  signal?: AbortSignal;
}): Promise<LessonPlan> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  const material = input.material;
  const title = material.title?.trim();
  if (!title) throw new ApiError('unknown', 'Unit title is required to generate lesson plan.');

  const outlineContent = material.outlineContent?.trim();
  if (!outlineContent) throw new ApiError('unknown', 'Outline is required to generate lesson plan.');

  const payload = {
    title,
    subject: material.subject || '',
    description: material.description || '',
    objectives: material.objectives || '',
    outlineContent,
    language: input.language ?? 'zh',
    sessionId: material.id,
    user_id: KB_USER_ID,
    kb_file_ids: Array.from(new Set((material.kbFileIds ?? []).map((id) => id.trim()).filter(Boolean))),
  };

  const response = await requestRaw(
    '/tools/lesson_plan',
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
  let finalPlan: LessonPlan | null = null;

  try {
    while (!finished) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const messages = parser.feed(chunk);

      for (const msg of messages) {
        const raw = msg.data.trim();
        if (!raw) continue;
        if (raw === '[DONE]') {
          finished = true;
          break;
        }

        const candidate = stripJsonCodeFence(raw).trim();
        let obj: any;
        try {
          obj = JSON.parse(candidate);
        } catch {
          continue;
        }

        if (obj?.type === 'error') {
          const text = String(obj?.text || 'Lesson plan generation error.');
          input.onEvent?.({ type: 'error', text });
          throw new ApiError('backend', text);
        }

        if (obj?.type === 'section' && obj?.section) {
          input.onEvent?.(obj as LessonPlanStreamEvent);
          continue;
        }

        if (obj?.type === 'final' && obj?.data) {
          finalPlan = obj.data as LessonPlan;
          input.onEvent?.({ type: 'final', data: finalPlan });
          continue;
        }
      }
    }
  } catch (e) {
    if (input.signal?.aborted) {
      throw new ApiError('abort', 'Request aborted.', { cause: e });
    }
    throw e;
  }

  if (!finalPlan) throw new ApiError('unknown', 'No final lesson plan received.');
  return finalPlan;
}

/**
 * POST /lesson/export/docx
 * 导出教案为 docx（附件下载返回）。
 */
export async function exportLessonDocx(input: {
  lessonPlan: LessonPlan;
  style: LessonStyle;
  language?: string;
  signal?: AbortSignal;
}): Promise<{ blob: Blob; filename: string | null }> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  const res = await requestRaw(
    '/lesson/export/docx',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lessonPlan: input.lessonPlan,
        style: input.style,
        language: input.language ?? 'zh',
      }),
    },
    { timeoutMs: 30_000, signal: input.signal },
  );

  const blob = await res.blob();
  const filename = parseContentDispositionFilename(res.headers.get('content-disposition'));
  return { blob, filename };
}
