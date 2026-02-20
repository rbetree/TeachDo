import Dexie, { type EntityTable } from 'dexie';
import type { EditorDocument, KBFile, LessonPlan, LessonStyle, Presentation } from '#root/types';

/**
 * TeachDo 持久化（IndexedDB）
 *
 * 目标：
 * - localStorage 只存轻量元数据（避免配额/卡顿）
 * - 大对象（outline/lesson/presentation/editorDocument/kbFiles）写入 IndexedDB
 *
 * 说明：
 * - 这里尽量使用结构化数据（不做 JSON stringify），避免序列化成本
 * - Date 统一转为 number(ms) 存储，读取时再恢复为 Date
 */

export const DB_NAME = 'TeachDoAppMaterial';
const APP_LARGE_ID = 'app' as const;

export interface PersistedKBFile extends Omit<KBFile, 'uploadedAt' | 'folderId'> {
  uploadedAt: number;
  folderId: number;
}

export interface AppLargeRecord {
  id: typeof APP_LARGE_ID;
  kbFiles: PersistedKBFile[];
  updatedAt: number;
}

export interface MaterialLargeRecord {
  materialId: string;
  outlineContent: string;
  lessonPlan: LessonPlan | null;
  lessonStyle: LessonStyle | null;
  presentation: Presentation | null;
  editorDocument: EditorDocument | null;
  updatedAt: number;
}

class TeachDoAppDb extends Dexie {
  appLarge!: EntityTable<AppLargeRecord, 'id'>;
  materialLarge!: EntityTable<MaterialLargeRecord, 'materialId'>;

  constructor() {
    super(DB_NAME);
    this.version(1).stores({
      appLarge: 'id, updatedAt',
      materialLarge: 'materialId, updatedAt',
    });
  }
}

const isBrowser = typeof window !== 'undefined';
let dbInstance: TeachDoAppDb | null = null;

function getDb(): TeachDoAppDb | null {
  if (!isBrowser) return null;
  if (!window.indexedDB) return null;
  if (dbInstance) return dbInstance;
  dbInstance = new TeachDoAppDb();
  return dbInstance;
}

function toTimestamp(value: unknown): number {
  if (value instanceof Date) return value.getTime();
  const asNumber = typeof value === 'number' ? value : Number.NaN;
  if (Number.isFinite(asNumber) && asNumber > 0) return asNumber;
  const parsed = new Date(String(value)).getTime();
  return Number.isFinite(parsed) ? parsed : Date.now();
}

function serializeKbFiles(list: KBFile[] | undefined): PersistedKBFile[] {
  if (!Array.isArray(list)) return [];
  return list.map((file) => ({
    id: file.id,
    name: file.name,
    size: file.size,
    type: file.type,
    status: file.status,
    progress: typeof file.progress === 'number' ? file.progress : undefined,
    uploadedAt: toTimestamp((file as any).uploadedAt),
    folderId: typeof file.folderId === 'number' ? file.folderId : 0,
    sourceType: file.sourceType,
    sourceMaterialId: file.sourceMaterialId,
    sourceMaterialTitle: file.sourceMaterialTitle,
  }));
}

function deserializeKbFiles(list: PersistedKBFile[] | undefined): KBFile[] {
  if (!Array.isArray(list)) return [];
  return list.map((file) => ({
    id: file.id,
    name: file.name,
    size: file.size,
    type: file.type,
    status: file.status,
    progress: typeof file.progress === 'number' ? file.progress : undefined,
    uploadedAt: new Date(file.uploadedAt),
    folderId: typeof file.folderId === 'number' ? file.folderId : 0,
    sourceType: file.sourceType,
    sourceMaterialId: file.sourceMaterialId,
    sourceMaterialTitle: file.sourceMaterialTitle,
  }));
}

function toPersistable<T>(value: T, fallback: T): T {
  if (value == null) return value;

  const clone = (globalThis as { structuredClone?: <U>(input: U) => U }).structuredClone;
  if (typeof clone === 'function') {
    try {
      return clone(value);
    } catch {
      // Vue Proxy 等对象会在 structuredClone 失败，继续走 JSON 兜底。
    }
  }

  try {
    return JSON.parse(JSON.stringify(value)) as T;
  } catch {
    return fallback;
  }
}

export async function deleteLegacyIndexedDb(): Promise<void> {
  if (!isBrowser) return;
  try {
    // 旧结构数据库（course/unit）
    await Dexie.delete('TeachDoApp');
  } catch {
    // ignore
  }
}

export async function saveAppLarge(input: { kbFiles: KBFile[] }): Promise<boolean> {
  const db = getDb();
  if (!db) return false;
  try {
    await db.appLarge.put({
      id: APP_LARGE_ID,
      kbFiles: serializeKbFiles(input.kbFiles),
      updatedAt: Date.now(),
    });
    return true;
  } catch (e) {
    console.warn('[TeachDoAppDb] 保存 appLarge 失败', e);
    return false;
  }
}

export async function loadAppLarge(): Promise<{ kbFiles: KBFile[] } | null> {
  const db = getDb();
  if (!db) return null;
  try {
    const record = await db.appLarge.get(APP_LARGE_ID);
    if (!record) return null;
    return {
      kbFiles: deserializeKbFiles(record.kbFiles),
    };
  } catch (e) {
    console.warn('[TeachDoAppDb] 读取 appLarge 失败', e);
    return null;
  }
}

export async function saveMaterialLarge(materialId: string, input: {
  outlineContent: string;
  lessonPlan: LessonPlan | null;
  lessonStyle: LessonStyle | null;
  presentation: Presentation | null;
  editorDocument: EditorDocument | null;
}): Promise<boolean> {
  const db = getDb();
  if (!db) return false;
  try {
    const lessonPlan = toPersistable<LessonPlan | null>(input.lessonPlan ?? null, null);
    const lessonStyle = toPersistable<LessonStyle | null>(input.lessonStyle ?? null, null);
    const presentation = toPersistable<Presentation | null>(input.presentation ?? null, null);
    const editorDocument = toPersistable<EditorDocument | null>(input.editorDocument ?? null, null);

    await db.materialLarge.put({
      materialId,
      outlineContent: input.outlineContent ?? '',
      lessonPlan,
      lessonStyle,
      presentation,
      editorDocument,
      updatedAt: Date.now(),
    });
    return true;
  } catch (e) {
    console.warn('[TeachDoAppDb] 保存 materialLarge 失败', e);
    return false;
  }
}

export async function loadMaterialLarge(materialId: string): Promise<MaterialLargeRecord | null> {
  const db = getDb();
  if (!db) return null;
  try {
    return (await db.materialLarge.get(materialId)) ?? null;
  } catch (e) {
    console.warn('[TeachDoAppDb] 读取 materialLarge 失败', e);
    return null;
  }
}

export async function deleteMaterialLarge(materialId: string): Promise<boolean> {
  const db = getDb();
  if (!db) return false;
  try {
    await db.materialLarge.delete(materialId);
    return true;
  } catch (e) {
    console.warn('[TeachDoAppDb] 删除 materialLarge 失败', e);
    return false;
  }
}
