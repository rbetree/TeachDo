import type { IconName } from '@/components/common/LucideIcon.vue';

export type KbSource = 'uploaded' | 'generated' | 'unknown';

/**
 * 知识库文件来源（用于 UI 标签）：
 * - folderId=0：上传素材（uploaded）
 * - folderId=1：生成产物（generated）
 * - 其他数值：未知（unknown）
 *
 * 注意：后端 main_api 已将 folder_id 缺省归一化为 0，因此前端把缺失/非法视为 uploaded 即可。
 */
export function getKbSource(folderId?: number): KbSource {
  if (folderId === 1) return 'generated';
  if (folderId === 2) return 'uploaded';
  if (folderId === 0 || typeof folderId !== 'number' || Number.isNaN(folderId)) return 'uploaded';
  return 'unknown';
}

export function getKbSourceUi(source: KbSource): {
  i18nKey: string;
  i18nTitleKey: string;
  icon: IconName;
  className: string;
} {
  const baseClass = 'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] leading-none font-bold border';

  if (source === 'generated') {
    return {
      i18nKey: 'kb.source.generated',
      i18nTitleKey: 'kb.source.generated_full',
      icon: 'sparkles',
      className: `${baseClass} bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-200 dark:border-purple-800/50`,
    };
  }

  if (source === 'unknown') {
    return {
      i18nKey: 'kb.source.unknown',
      i18nTitleKey: 'kb.source.unknown',
      icon: 'info',
      className: `${baseClass} bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/60 dark:text-slate-200 dark:border-slate-700`,
    };
  }

  return {
    i18nKey: 'kb.source.uploaded',
    i18nTitleKey: 'kb.source.uploaded_full',
    icon: 'upload-cloud',
    className: `${baseClass} bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-900/30 dark:text-sky-200 dark:border-sky-800/50`,
  };
}
