/**
 * KB file_id 约定：
 * - upload:*  上传素材（用于 RAG 检索：只注入片段）
 * - gen:*     课程产出（全文注入，不经检索）
 * - full:*    全文上传（全文注入，不经检索）
 */

export const isFullTextKbFileId = (fileId: string): boolean => {
  const id = (fileId || '').trim();
  return id.startsWith('gen:') || id.startsWith('full:');
};

export const isFullUploadKbFileId = (fileId: string): boolean => {
  const id = (fileId || '').trim();
  return id.startsWith('full:');
};

