export type GenOutputKind = 'outline' | 'lesson' | 'slides' | 'slides_final' | string;

export interface BuildGenOutputFileIdInput {
  userId: string;
  materialId: string;
  kind: GenOutputKind;
  nowMs?: number;
  rand3?: string;
}

export interface ParsedGenOutputFileId {
  user: string;
  materialId: string;
  kind: string;
  epochMs: number | null;
  rand3: string | null;
}

const pad2 = (n: number) => String(n).padStart(2, '0');

export const formatVersionLabel = (epochMs: number): string => {
  const d = new Date(epochMs);
  if (Number.isNaN(d.getTime())) return '';
  const yyyy = d.getFullYear();
  const mm = pad2(d.getMonth() + 1);
  const dd = pad2(d.getDate());
  const hh = pad2(d.getHours());
  const mi = pad2(d.getMinutes());
  const ss = pad2(d.getSeconds());
  return `${yyyy}${mm}${dd}-${hh}${mi}${ss}`;
};

export const sanitizeFilenameSegment = (raw: string): string => {
  const value = String(raw ?? '').trim();
  if (!value) return '';
  // 与后端落盘/Windows 文件名限制对齐一部分：避免下载时出现非法字符或路径穿越
  return value
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '');
};

const normalizeRand3 = (rand3: string) => {
  const s = String(rand3 || '').trim();
  if (/^\d{3}$/.test(s)) return s;
  const n = Math.floor(Math.random() * 1000);
  return String(n).padStart(3, '0');
};

export const buildGenOutputFileId = (input: BuildGenOutputFileIdInput): string => {
  const user = String(input.userId || '').trim();
  const materialId = String(input.materialId || '').trim();
  const kind = String(input.kind || '').trim();
  const epochMs = typeof input.nowMs === 'number' && Number.isFinite(input.nowMs) ? Math.floor(input.nowMs) : Date.now();
  const rand3 = normalizeRand3(input.rand3 || '');
  return `gen:${user}:${materialId}:${kind}:${epochMs}:${rand3}`;
};

export const parseGenOutputFileId = (fileId: string): ParsedGenOutputFileId | null => {
  const id = String(fileId || '').trim();
  if (!id.startsWith('gen:')) return null;

  const parts = id.split(':');
  if (parts.length < 4) return null;

  const user = (parts[1] || '').trim();
  const materialId = (parts[2] || '').trim();
  if (!user || !materialId) return null;

  const rest = parts.slice(3).map((p) => String(p ?? '').trim());
  if (!rest.length) return null;

  // 新格式：gen:{user}:{material}:{kind}:{epochMs}:{rand3}
  if (rest.length >= 3) {
    const candidateKind = rest[0];
    const epochMs = Number(rest[1]);
    const rand3 = rest[2] || '';
    if (candidateKind && Number.isFinite(epochMs) && epochMs > 0 && /^\d{1,6}$/.test(rand3)) {
      return { user, materialId, kind: candidateKind, epochMs: Math.floor(epochMs), rand3 };
    }
  }

  // 旧格式：gen:{user}:{material}:{kind...}
  return {
    user,
    materialId,
    kind: rest.join(':'),
    epochMs: null,
    rand3: null,
  };
};

export const getGenOutputEpochMs = (fileId: string): number | null => {
  const parsed = parseGenOutputFileId(fileId);
  return parsed?.epochMs ?? null;
};
