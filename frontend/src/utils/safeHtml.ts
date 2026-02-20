/**
 * 将用户/模型输出作为纯文本转义，避免注入 HTML（XSS）。
 * 注意：这里只做转义，不做 Markdown 解析。
 */
export function escapeHtml(value: string): string {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

