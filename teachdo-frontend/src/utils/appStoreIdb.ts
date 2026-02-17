import Dexie, { type EntityTable } from 'dexie';
import type {
  ChatMessage,
  CourseGroup,
  CourseUnit,
  EditorDocument,
  KBFile,
  LessonPlan,
  Presentation,
} from '#root/types';

/**
 * TeachDo 持久化（IndexedDB）
 *
 * 目标：
 * - localStorage 只存轻量元数据（避免配额/卡顿）
 * - 大对象（editorDocument、presentation、lessonPlan、outline、chatHistory、kbFiles）写入 IndexedDB
 *
 * 说明：
 * - 这里尽量使用结构化数据（不做 JSON stringify），避免序列化成本
 * - Date 统一转为 number(ms) 存储，读取时再恢复为 Date
 */

const DB_NAME = 'TeachDoApp';

export interface PersistedKBFile extends Omit<KBFile, 'uploadedAt' | 'folderId'> {
  uploadedAt: number;
  folderId: number;
}

export interface PersistedChatMessage extends Omit<ChatMessage, 'timestamp'> {
  timestamp: number;
}

export interface CourseLargeRecord {
  courseId: string;
  kbFiles: PersistedKBFile[];
  chatHistory: PersistedChatMessage[];
  updatedAt: number;
}

export interface UnitLargeRecord {
  id: string; // `${courseId}:${unitId}`
  courseId: string;
  unitId: string;
  outlineContent: string;
  lessonPlan: LessonPlan | null;
  presentation: Presentation | null;
  editorDocument: EditorDocument | null;
  updatedAt: number;
}

class TeachDoAppDb extends Dexie {
  courseLarge!: EntityTable<CourseLargeRecord, 'courseId'>;
  unitLarge!: EntityTable<UnitLargeRecord, 'id'>;

  constructor() {
    super(DB_NAME);
    this.version(1).stores({
      courseLarge: 'courseId, updatedAt',
      unitLarge: 'id, courseId, unitId, updatedAt',
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

export function makeUnitKey(courseId: string, unitId: string): string {
  return `${courseId}:${unitId}`;
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
  }));
}

function serializeChatHistory(list: ChatMessage[] | undefined): PersistedChatMessage[] {
  if (!Array.isArray(list)) return [];
  return list.map((msg) => ({
    role: msg.role === 'user' ? 'user' : 'model',
    text: msg.text,
    timestamp: toTimestamp((msg as any).timestamp),
  }));
}

function deserializeChatHistory(list: PersistedChatMessage[] | undefined): ChatMessage[] {
  if (!Array.isArray(list)) return [];
  return list.map((msg) => ({
    role: msg.role === 'user' ? 'user' : 'model',
    text: msg.text,
    timestamp: new Date(msg.timestamp),
  }));
}

export async function saveCourseLarge(course: CourseGroup): Promise<boolean> {
  const db = getDb();
  if (!db) return false;
  try {
    await db.courseLarge.put({
      courseId: course.id,
      kbFiles: serializeKbFiles(course.kbFiles),
      chatHistory: serializeChatHistory(course.chatHistory),
      updatedAt: Date.now(),
    });
    return true;
  } catch (e) {
    console.warn('[TeachDoAppDb] 保存 courseLarge 失败', e);
    return false;
  }
}

export async function saveUnitLarge(courseId: string, unit: CourseUnit): Promise<boolean> {
  const db = getDb();
  if (!db) return false;
  try {
    await db.unitLarge.put({
      id: makeUnitKey(courseId, unit.id),
      courseId,
      unitId: unit.id,
      outlineContent: unit.outlineContent ?? '',
      lessonPlan: unit.lessonPlan ?? null,
      presentation: unit.presentation ?? null,
      editorDocument: unit.editorDocument ?? null,
      updatedAt: Date.now(),
    });
    return true;
  } catch (e) {
    console.warn('[TeachDoAppDb] 保存 unitLarge 失败', e);
    return false;
  }
}

export async function loadCourseLarge(courseId: string): Promise<{ kbFiles: KBFile[]; chatHistory: ChatMessage[] } | null> {
  const db = getDb();
  if (!db) return null;
  try {
    const record = await db.courseLarge.get(courseId);
    if (!record) return null;
    return {
      kbFiles: deserializeKbFiles(record.kbFiles),
      chatHistory: deserializeChatHistory(record.chatHistory),
    };
  } catch (e) {
    console.warn('[TeachDoAppDb] 读取 courseLarge 失败', e);
    return null;
  }
}

export async function loadUnitLargeByCourse(courseId: string): Promise<Map<string, UnitLargeRecord>> {
  const db = getDb();
  if (!db) return new Map();
  try {
    const records = await db.unitLarge.where('courseId').equals(courseId).toArray();
    const map = new Map<string, UnitLargeRecord>();
    for (const record of records) {
      map.set(record.unitId, record);
    }
    return map;
  } catch (e) {
    console.warn('[TeachDoAppDb] 读取 unitLarge 失败', e);
    return new Map();
  }
}
