import type { LessonDocxTemplate, LessonPlan, LessonStyle, TeachingMaterial } from '#root/types';
import { ApiError, checkBackend, ensureBackendAvailable, requestJson, requestRaw } from '@/services/apiClient';
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

// Fallback Mock Templates（后端不可用时兜底）
export const MOCK_LESSON_TEMPLATES: LessonDocxTemplate[] = [
  { id: 'lesson_simple', name: '简洁版', thumbnailColor: 'bg-slate-600', styleDescription: '标题 + 分节列表' },
  { id: 'lesson_table', name: '表格版', thumbnailColor: 'bg-indigo-600', styleDescription: '流程表格布局' },
  { id: 'lesson_jnu_form', name: '教案表单（字段）', thumbnailColor: 'bg-emerald-600', styleDescription: '授课题目/类型/教学内容/作业等' },
];

/**
 * GET /lesson/templates
 * - 后端不可用或请求失败时，返回 mock 列表（不抛错）
 */
export async function getLessonTemplates(): Promise<LessonDocxTemplate[]> {
  const available = await checkBackend();
  if (!available) return MOCK_LESSON_TEMPLATES;

  try {
    const wrapper = await requestJson<any>('/lesson/templates', { method: 'GET' }, { timeoutMs: 8000 });
    const list = wrapper?.data || [];
    return list.map((t: any) => ({
      id: t.id || t.name,
      name: t.name || t.id,
      thumbnailColor:
        (t.id === 'lesson_simple' && 'bg-slate-600') ||
        (t.id === 'lesson_table' && 'bg-indigo-600') ||
        (t.id === 'lesson_jnu_form' && 'bg-emerald-600') ||
        'bg-slate-200',
      styleDescription: t.description || t.name || t.id,
      coverUrl: typeof t.cover === 'string' ? t.cover : undefined,
      rawTemplate: t,
    }));
  } catch (e) {
    console.warn('Failed to fetch lesson templates from backend, using mock.', e);
    return MOCK_LESSON_TEMPLATES;
  }
}

/**
 * POST /tools/lesson_plan (SSE, JSON events)
 */
export async function streamLessonPlan(input: {
  material: TeachingMaterial;
  language?: string;
  templateId?: string;
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

  const outlineFileId = `gen:${KB_USER_ID}:${material.id}:outline`;
  const kbFileIds = Array.from(new Set((material.kbFileIds ?? []).map((id) => id.trim()).filter(Boolean))).filter(
    (id) => id !== outlineFileId,
  );

  const payload = {
    title,
    subject: material.subject || '',
    description: material.description || '',
    objectives: material.objectives || '',
    outlineContent,
    language: input.language ?? 'zh',
    sessionId: material.id,
    user_id: KB_USER_ID,
    kb_file_ids: kbFileIds,
    templateId: (input.templateId || material.selectedLessonTemplateId || '').trim() || undefined,
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
  templateId?: string;
  language?: string;
  persist?: boolean;
  userId?: string;
  materialId?: string;
  signal?: AbortSignal;
}): Promise<{ blob: Blob; filename: string | null; artifactId: string | null }> {
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
        templateId: input.templateId,
        ...(typeof input.persist === 'boolean' ? { persist: input.persist } : {}),
        ...(input.userId ? { userId: input.userId } : {}),
        ...(input.materialId ? { materialId: input.materialId } : {}),
      }),
    },
    { timeoutMs: 30_000, signal: input.signal },
  );

  const blob = await res.blob();
  const filename = parseContentDispositionFilename(res.headers.get('content-disposition'));
  const artifactId = (res.headers.get('x-teachdo-artifact-id') || '').trim() || null;
  return { blob, filename, artifactId };
}
