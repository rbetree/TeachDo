import type { Presentation } from '#root/types';

export const PPTX_MIME = 'application/vnd.openxmlformats-officedocument.presentationml.presentation';

const clamp = (n: number, min: number, max: number) => Math.min(max, Math.max(min, n));

const toBlob = (raw: unknown, mime: string): Blob => {
  if (raw instanceof Blob) return raw;
  if (raw instanceof ArrayBuffer) return new Blob([raw], { type: mime });
  if (raw instanceof Uint8Array) {
    const copy = new Uint8Array(raw.byteLength);
    copy.set(raw);
    return new Blob([copy.buffer], { type: mime });
  }
  return new Blob([String(raw ?? '')], { type: mime });
};

export async function buildSimpleTextPptxBlob(input: { title: string; slides: Presentation['slides'] }): Promise<Blob> {
  const PptxGen = (await import('pptxgenjs')).default as any;
  const pptx = new PptxGen();
  pptx.layout = 'LAYOUT_16x9';

  const slideW = 13.333; // pptxgenjs wide layout
  const slideH = 7.5;

  const title = String(input.title || '').trim() || 'TeachDo';
  const slides = Array.isArray(input.slides) ? input.slides : [];
  const safeSlides = slides.length > 0 ? slides : [{ title: title, content: [], notes: '' }];

  for (const [index, s] of safeSlides.entries()) {
    const slide = pptx.addSlide();

    const slideTitle = String(s?.title || '').trim() || `${title} - ${index + 1}`;
    const contentLines = Array.isArray(s?.content) ? s.content.map((x) => String(x ?? '').trim()).filter(Boolean) : [];
    const notes = String(s?.notes || '').trim();

    slide.addText(slideTitle, {
      x: 0.8,
      y: 0.5,
      w: slideW - 1.6,
      h: 0.8,
      fontFace: '微软雅黑',
      fontSize: 30,
      bold: true,
      color: '1f2937',
    });

    if (contentLines.length > 0) {
      const body = contentLines.map((line) => `• ${line}`).join('\n');
      slide.addText(body, {
        x: 0.95,
        y: 1.5,
        w: slideW - 1.9,
        h: clamp(slideH - 2.2, 3.5, 5.8),
        fontFace: '微软雅黑',
        fontSize: 18,
        color: '334155',
        valign: 'top',
      });
    }

    if (notes) {
      slide.addNotes(notes);
    }
  }

  const raw: unknown = await (pptx as any).write({ outputType: 'blob' });
  return toBlob(raw, PPTX_MIME);
}

