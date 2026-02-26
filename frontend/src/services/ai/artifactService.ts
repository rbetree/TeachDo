import { ApiError, ensureBackendAvailable, requestOkWrapper, requestRaw } from '@/services/apiClient';

export type ArtifactKind = 'pptx' | 'docx';

export interface ArtifactMeta {
  artifact_id: string;
  kind: ArtifactKind;
  file_name: string;
  created_at?: number;
  size?: number;
}

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

export async function listArtifacts(input: { userId: string; materialId: string; signal?: AbortSignal }): Promise<ArtifactMeta[]> {
  if (input.signal?.aborted) throw new ApiError('abort', 'Request aborted.');
  await ensureBackendAvailable();

  const userId = encodeURIComponent(input.userId);
  const materialId = encodeURIComponent(input.materialId);
  return await requestOkWrapper(`/artifacts/${userId}/${materialId}`, { method: 'GET' }, { timeoutMs: 12_000, signal: input.signal });
}

export async function uploadArtifact(input: {
  userId: string;
  materialId: string;
  kind: ArtifactKind;
  file: File;
  signal?: AbortSignal;
}): Promise<ArtifactMeta> {
  if (input.signal?.aborted) throw new ApiError('abort', 'Request aborted.');
  await ensureBackendAvailable();

  const userId = encodeURIComponent(input.userId);
  const materialId = encodeURIComponent(input.materialId);

  const formData = new FormData();
  formData.append('kind', input.kind);
  formData.append('file', input.file);

  return await requestOkWrapper(`/artifacts/${userId}/${materialId}`, { method: 'POST', body: formData }, { timeoutMs: 60_000, signal: input.signal });
}

export async function downloadArtifact(input: {
  userId: string;
  materialId: string;
  artifactId: string;
  signal?: AbortSignal;
}): Promise<{ blob: Blob; filename: string | null }> {
  if (input.signal?.aborted) throw new ApiError('abort', 'Request aborted.');
  await ensureBackendAvailable();

  const userId = encodeURIComponent(input.userId);
  const materialId = encodeURIComponent(input.materialId);
  const artifactId = encodeURIComponent(input.artifactId);
  const res = await requestRaw(
    `/artifacts/${userId}/${materialId}/${artifactId}`,
    { method: 'GET' },
    { timeoutMs: 60_000, signal: input.signal },
  );
  const blob = await res.blob();
  const filename = parseContentDispositionFilename(res.headers.get('content-disposition'));
  return { blob, filename };
}

export async function deleteArtifact(input: { userId: string; materialId: string; artifactId: string; signal?: AbortSignal }): Promise<void> {
  if (input.signal?.aborted) throw new ApiError('abort', 'Request aborted.');
  await ensureBackendAvailable();

  const userId = encodeURIComponent(input.userId);
  const materialId = encodeURIComponent(input.materialId);
  const artifactId = encodeURIComponent(input.artifactId);
  await requestOkWrapper(`/artifacts/${userId}/${materialId}/${artifactId}`, { method: 'DELETE' }, { timeoutMs: 12_000, signal: input.signal });
}

