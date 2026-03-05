import type { LessonPlan, LessonStyle } from '#root/types';
import {
  loadLessonDocxPreview,
  makeLessonDocxPreviewKey,
  saveLessonDocxPreview,
  type LessonDocxPreviewRecord,
} from '@/utils/appStoreIdb';

export const DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

const memoryCache = new Map<string, LessonDocxPreviewRecord>();

function normalizeText(input: unknown): string {
  return String(input ?? '')
    .replace(/\s+/g, ' ')
    .trim();
}

function hash32FNV1a(input: string): number {
  // FNV-1a 32-bit
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

function hash32Djb2(input: string): number {
  // DJB2 32-bit
  let hash = 5381;
  for (let i = 0; i < input.length; i += 1) {
    hash = ((hash << 5) + hash + input.charCodeAt(i)) >>> 0;
  }
  return hash >>> 0;
}

function hashText(input: string): string {
  const a = hash32FNV1a(input);
  const b = hash32Djb2(input);
  // base36 更短，足够用于本地缓存比对
  return `${a.toString(36)}${b.toString(36)}`;
}

export function computeLessonPlanHash(plan: LessonPlan): string {
  const parts: string[] = [];
  parts.push(normalizeText(plan.title));
  parts.push(normalizeText(plan.targetAudience));
  parts.push(normalizeText(plan.duration));
  parts.push((plan.objectives || []).map(normalizeText).join('\n'));
  parts.push((plan.materials || []).map(normalizeText).join('\n'));
  parts.push(
    (plan.procedure || [])
      .map((step) => [step?.step, step?.duration, step?.activity].map(normalizeText).join('|'))
      .join('\n'),
  );
  parts.push(normalizeText(plan.homework));

  return hashText(parts.join('\u001f'));
}

export function computeLessonStyleHash(style: LessonStyle): string {
  const parts: string[] = [];
  parts.push(normalizeText(style.fontZh));
  parts.push(String(style.titleSizePt ?? ''));
  parts.push(String(style.h1SizePt ?? ''));
  parts.push(String(style.h2SizePt ?? ''));
  parts.push(String(style.bodySizePt ?? ''));
  parts.push(String(style.lineSpacing ?? ''));
  parts.push(String(style.marginTopCm ?? ''));
  parts.push(String(style.marginBottomCm ?? ''));
  parts.push(String(style.marginLeftCm ?? ''));
  parts.push(String(style.marginRightCm ?? ''));
  return hashText(parts.join('\u001f'));
}

export async function loadLessonDocxPreviewCached(input: {
  materialId: string;
  templateId: string;
  locale: string;
}): Promise<LessonDocxPreviewRecord | null> {
  const cacheKey = makeLessonDocxPreviewKey(input);
  const cached = memoryCache.get(cacheKey);
  if (cached) return cached;

  const record = await loadLessonDocxPreview(input);
  if (record) memoryCache.set(cacheKey, record);
  return record;
}

export async function saveLessonDocxPreviewCached(input: {
  materialId: string;
  templateId: string;
  locale: string;
  planHash: string;
  styleHash: string;
  buffer: ArrayBuffer;
}): Promise<boolean> {
  const ok = await saveLessonDocxPreview(input);
  if (!ok) return false;

  const cacheKey = makeLessonDocxPreviewKey(input);
  memoryCache.set(cacheKey, {
    cacheKey,
    materialId: String(input.materialId || '').trim(),
    templateId: String(input.templateId || '').trim(),
    locale: String(input.locale || '').trim() || 'zh',
    planHash: String(input.planHash || '').trim(),
    styleHash: String(input.styleHash || '').trim(),
    buffer: input.buffer,
    byteLength: input.buffer?.byteLength || 0,
    updatedAt: Date.now(),
  });

  return true;
}

export function clearLessonDocxPreviewMemoryByMaterialId(materialId: string): void {
  const id = String(materialId || '').trim();
  if (!id) return;
  for (const key of memoryCache.keys()) {
    if (key.startsWith(`lessonDocxPreview:${id}:`)) {
      memoryCache.delete(key);
    }
  }
}

