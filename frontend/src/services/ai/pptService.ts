import type { PPTTemplate } from '#root/types';
import { SseParser, stripJsonCodeFence } from '@/utils/sse';
import type { AIPPTSlide } from '@/editor-runtime/types/AIPPT';
import { ApiError, checkBackend, ensureBackendAvailable, requestJson, requestRaw } from '@/services/apiClient';

// Fallback Mock Templates
export const MOCK_TEMPLATES: PPTTemplate[] = [
  { id: 'classic_blue', name: '商务蓝', thumbnailColor: 'bg-blue-600', styleDescription: 'Professional, Clean' },
  { id: 'warm_orange', name: '活力橙', thumbnailColor: 'bg-orange-500', styleDescription: 'Energetic, Warm' },
  { id: 'nature_green', name: '自然绿', thumbnailColor: 'bg-emerald-600', styleDescription: 'Calm, Educational' },
];

/**
 * GET /templates
 * - 后端不可用或请求失败时，返回 mock 列表（不抛错）
 */
export async function getTemplates(): Promise<PPTTemplate[]> {
  const available = await checkBackend();
  if (!available) return MOCK_TEMPLATES;

  try {
    const wrapper = await requestJson<any>('/templates', { method: 'GET' }, { timeoutMs: 8000 });
    const list = wrapper?.data || [];
    return list.map((t: any) => ({
      id: t.id || t.name,
      name: t.name || t.id,
      thumbnailColor: 'bg-slate-200',
      styleDescription: t.name || t.id,
      // main_api already returns /api/data/*.jpg
      coverUrl: typeof t.cover === 'string' ? t.cover : undefined,
      rawTemplate: t,
    }));
  } catch (e) {
    console.warn('Failed to fetch templates from backend, using mock.', e);
    return MOCK_TEMPLATES;
  }
}

/**
 * GET /data/{templateId}.json
 * 获取模板详情（slides/theme/width/height 等）
 */
export async function getTemplateFileData(templateId: string): Promise<any> {
  await ensureBackendAvailable();

  const id = (templateId || '').trim();
  if (!id) throw new ApiError('unknown', 'templateId is required.');

  return await requestJson<any>(`/data/${id}.json`, { method: 'GET' }, { timeoutMs: 12_000 });
}

/**
 * POST /tools/ppt (SSE, JSON per slide)
 * 返回 AIPPTSlide[]；并可通过 onSlide 增量回调。
 */
export async function streamPptSlides(input: {
  content: string;
  sessionId: string;
  language?: string;
  generateFromWebSearch?: boolean;
  generateFromUploadedFile?: boolean;
  generateWithImages?: boolean;
  kbFolderIds?: number[] | null;
  kbFileIds?: string[] | null;
  onSlide?: (slide: AIPPTSlide) => void;
  signal?: AbortSignal;
}): Promise<AIPPTSlide[]> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  const payload = {
    content: input.content,
    language: input.language ?? 'zh',
    sessionId: input.sessionId,
    generateFromWebSearch: input.generateFromWebSearch ?? true,
    generateFromUploadedFile: input.generateFromUploadedFile ?? false,
    generateWithImages: input.generateWithImages ?? false,
    kb_folder_ids: input.kbFolderIds ?? null,
    kb_file_ids: input.kbFileIds ?? null,
  };

  const response = await requestRaw(
    '/tools/ppt',
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

  const slides: AIPPTSlide[] = [];
  let finished = false;

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
          // 非 JSON（例如零散文本片段）直接忽略
          continue;
        }

        const type = obj?.type;
        if (type === 'error') {
          throw new ApiError('backend', obj?.text || 'PPT generation error.');
        }

        if (type === 'cover' || type === 'contents' || type === 'transition' || type === 'content' || type === 'reference' || type === 'end') {
          const slide = obj as AIPPTSlide;
          slides.push(slide);
          input.onSlide?.(slide);
        }
      }
    }
  } catch (e) {
    if (input.signal?.aborted) {
      throw new ApiError('abort', 'Request aborted.', { cause: e });
    }
    throw e;
  }

  return slides;
}

/**
 * @deprecated 历史命名（沿袭自旧接口 /tools/aippt），请使用 `streamPptSlides`。
 */
export const streamAipptSlides = streamPptSlides;
