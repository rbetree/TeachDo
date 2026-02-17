import { ApiError, ensureBackendAvailable, requestOkWrapper } from '@/services/apiClient';

/**
 * POST /kb/upload
 * 上传知识库文件并向量化（folder_id: 0=上传素材，1=生成产物）。
 */
export async function kbUpload(input: { userId: string; file: File; folderId?: number; signal?: AbortSignal }): Promise<{
  user_id: string;
  file_id: string;
  file_name: string;
  file_type: string;
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
    folder_id: number;
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
      }),
    },
    { timeoutMs: 20_000, signal: input.signal },
  );
}

