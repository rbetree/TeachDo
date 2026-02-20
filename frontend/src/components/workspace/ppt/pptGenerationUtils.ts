import type { Presentation } from '#root/types';
import type { AIPPTSlide } from '@/editor-runtime/types/AIPPT';

export function mapAipptSlideToPreview(slide: AIPPTSlide): Presentation['slides'][number] | null {
  if (!slide) return null;

  if (slide.type === 'cover') {
    return {
      title: slide.data.title || '封面',
      content: slide.data.text ? [slide.data.text] : [],
      notes: '',
    };
  }

  if (slide.type === 'contents') {
    return {
      title: '目录',
      content: slide.data.items || [],
      notes: '',
    };
  }

  if (slide.type === 'transition') {
    const lines = [slide.data.text].filter(Boolean) as string[];
    return {
      title: slide.data.title || '章节',
      content: lines,
      notes: '',
    };
  }

  if (slide.type === 'content') {
    const contentLines = (slide.data.items || []).map((it: any) => {
      if (it?.kind === 'chart') return `图表：${it.title || it.chartType || 'chart'}`;
      if (it?.kind === 'image') return `图片：${it.title || ''} ${it.text || ''}`.trim();
      if (it?.kind === 'text') return `${it.title || ''}：${it.text || ''}`.replace(/^：/, '');
      // legacy {title,text}
      if (typeof it?.title === 'string' && typeof it?.text === 'string') return `${it.title}：${it.text}`;
      return String(it ?? '');
    });
    return {
      title: slide.data.title || '内容',
      content: contentLines.filter((x) => x && x.trim().length > 0),
      notes: '',
    };
  }

  if (slide.type === 'reference') {
    const refs = slide.data.references || [];
    return {
      title: slide.data.title || '参考资料',
      content: refs.map((r: any) => r?.text).filter(Boolean),
      notes: '',
    };
  }

  if (slide.type === 'end') {
    return {
      title: '结束',
      content: [],
      notes: '',
    };
  }

  return null;
}

export function buildSlidesMarkdown(unitTitle: string, slides: Presentation['slides']): string {
  const chunks: string[] = [`# ${unitTitle}`];

  slides.forEach((slide, index) => {
    chunks.push(`## Slide ${index + 1}: ${slide.title}`);
    if (slide.content?.length) {
      chunks.push(slide.content.map((c) => `- ${c}`).join('\n'));
    }
    if (slide.notes?.trim()) {
      chunks.push(`**Speaker Notes:**\n${slide.notes.trim()}`);
    }
    chunks.push('---');
  });

  return chunks.join('\n\n');
}

