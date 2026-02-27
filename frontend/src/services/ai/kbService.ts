import { ApiError, ensureBackendAvailable, requestOkWrapper, requestRaw } from '@/services/apiClient';

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
 * POST /kb/upload
 * 上传知识库文件并向量化（folder_id: 0=上传素材，1=生成产物，2=全文上传）。
 */
export async function kbUpload(input: {
  userId: string;
  file: File;
  folderId?: number;
  fileId?: string;
  signal?: AbortSignal;
}): Promise<{
  user_id: string;
  file_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  folder_id: number;
  status: string;
}> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  const formData = new FormData();
  formData.append('user_id', input.userId);
  formData.append('folder_id', String(input.folderId ?? 0));
  if (typeof input.fileId === 'string' && input.fileId.trim()) {
    formData.append('file_id', input.fileId.trim());
  }
  formData.append('file_type', input.file.name.split('.').pop() || 'unknown');
  formData.append('file', input.file);

  return await requestOkWrapper('/kb/upload', { method: 'POST', body: formData }, { timeoutMs: 120_000, signal: input.signal });
}

/**
 * GET /kb/files/{user_id}
 */
export async function kbListFiles(input: { userId: string; folderId?: number; signal?: AbortSignal }): Promise<
  Array<{
    user_id: string;
    file_id: string;
    file_name: string;
    file_type: string;
    file_size: number;
    folder_id: number;
    created_at?: number;
    source_type?: 'upload' | 'material';
    source_material_id?: string;
    source_material_title?: string;
  }>
> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  const userId = encodeURIComponent(input.userId);
  const qs = typeof input.folderId === 'number' ? `?folder_id=${encodeURIComponent(String(input.folderId))}` : '';
  return await requestOkWrapper(`/kb/files/${userId}${qs}`, { method: 'GET' }, { timeoutMs: 12_000, signal: input.signal });
}

/**
 * DELETE /kb/files/{user_id}/{file_id}
 */
export async function kbDeleteFile(input: { userId: string; fileId: string; signal?: AbortSignal }): Promise<void> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  const userId = encodeURIComponent(input.userId);
  const fileId = encodeURIComponent(input.fileId);
  await requestOkWrapper(`/kb/files/${userId}/${fileId}`, { method: 'DELETE' }, { timeoutMs: 12_000, signal: input.signal });
}

/**
 * GET /kb/files/{user_id}/{file_id}/export
 * 导出知识库文件内容（以附件下载返回）。
 */
export async function kbExportFile(input: {
  userId: string;
  fileId: string;
  signal?: AbortSignal;
}): Promise<{ blob: Blob; filename: string | null }> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  const userId = encodeURIComponent(input.userId);
  const fileId = encodeURIComponent(input.fileId);
  const res = await requestRaw(
    `/kb/files/${userId}/${fileId}/export`,
    { method: 'GET' },
    { timeoutMs: 30_000, signal: input.signal },
  );
  const blob = await res.blob();
  const filename = parseContentDispositionFilename(res.headers.get('content-disposition'));
  return { blob, filename };
}

/**
 * POST /kb/vectorize/text
 * 将生成/编辑后的文本写入知识库索引（产物入库）。
 */
export async function vectorizeTextToKb(input: {
  userId: string;
  fileId: string;
  fileName: string;
  content: string;
  fileType?: string;
  folderId?: number;
  createdAt?: number;
  sourceType?: 'upload' | 'material';
  sourceMaterialId?: string;
  sourceMaterialTitle?: string;
  signal?: AbortSignal;
}): Promise<void> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  await requestOkWrapper(
    '/kb/vectorize/text',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: input.userId,
        file_id: input.fileId,
        file_name: input.fileName,
        content: input.content,
        file_type: input.fileType ?? 'md',
        folder_id: input.folderId ?? 1,
        ...(typeof input.createdAt === 'number' ? { created_at: input.createdAt } : {}),
        ...(input.sourceType ? { source_type: input.sourceType } : {}),
        ...(input.sourceMaterialId ? { source_material_id: input.sourceMaterialId } : {}),
        ...(input.sourceMaterialTitle ? { source_material_title: input.sourceMaterialTitle } : {}),
      }),
    },
    { timeoutMs: 20_000, signal: input.signal },
  );
}
