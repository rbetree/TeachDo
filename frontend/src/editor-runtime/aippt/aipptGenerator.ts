import type {
  PPTChartElement,
  PPTElement,
  PPTImageElement,
  PPTShapeElement,
  PPTTextElement,
  Slide,
  TextType,
} from "@editor/types/slides";
import type {
  AIPPTContentChartItem,
  AIPPTContentImageItem,
  AIPPTContentTextItem,
  AIPPTLegacyTextItem,
  AIPPTSlide,
  AnyContentItem,
} from "@editor/types/AIPPT";

const isChartItem = (x: any): x is AIPPTContentChartItem =>
  x && x.kind === "chart" && Array.isArray(x.labels) && Array.isArray(x.series);
const isTextItem = (x: any): x is AIPPTContentTextItem =>
  x && x.kind === "text" && typeof x.title === "string" && typeof x.text === "string";
const isLegacyTextItem = (x: any): x is AIPPTLegacyTextItem =>
  x && x.kind === undefined && typeof x.title === "string" && typeof x.text === "string";
const isImageItem = (x: any): x is AIPPTContentImageItem => x && x.kind === "image";

export interface ImgPoolItem {
  id: string;
  src: string;
  width: number;
  height: number;
}

const randomId = (len = 10) => {
  const alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
  try {
    const bytes = new Uint8Array(len);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
  } catch {
    return Math.random().toString(36).slice(2, 2 + len).padEnd(len, "0");
  }
};

/**
 * AIPPT Slide -> 编辑器 Slide[] 映射器（有状态）
 * - 需要在一次“生成会话”内复用同一个实例，以保持过渡页编号与风格一致。
 */
export function createAipptGenerator() {
  let imgPool: ImgPoolItem[] = [];
  let transitionIndex = 0;
  let transitionTemplate: Slide | null = null;

  const reset = () => {
    imgPool = [];
    transitionIndex = 0;
    transitionTemplate = null;
  };

  const presetImgPool = (imgs: ImgPoolItem[]) => {
    imgPool = Array.isArray(imgs) ? [...imgs] : [];
  };

  const checkTextType = (el: PPTElement, type: TextType) => {
    return (
      (el.type === "text" && (el as PPTTextElement).textType === type) ||
      (el.type === "shape" && (el as PPTShapeElement).text && (el as PPTShapeElement).text!.type === type)
    );
  };

  const checkChartItemMark = (el: PPTElement) => {
    return el.type === "chart" && (el as any).chartMark === "item";
  };

  const checkImageType = (el: PPTElement, imageType: string) =>
    el.type === "image" && (el as PPTImageElement).imageType === imageType;

  const countImageItemSlots = (slide: Slide) => slide.elements.filter((el) => checkImageType(el, "itemFigure")).length;

  const getUseableTemplates = (templates: Slide[], n: number, type: TextType) => {
    const list = templates.filter((slide) => slide.elements.filter((el) => checkTextType(el, type)).length >= n);
    if (!list.length) return [];

    // 优先选择元素数量最接近需求数量的模板
    let target = list[0];
    if (n <= 2) {
      const sorted = [...list].sort((a, b) => {
        const aLen = a.elements.filter((el) => checkTextType(el, type)).length;
        const bLen = b.elements.filter((el) => checkTextType(el, type)).length;
        return aLen - bLen;
      });
      target = sorted[sorted.length - 1]!;
    } else {
      target = list.reduce((closest, current) => {
        const currentLen = current.elements.filter((el) => checkTextType(el, type)).length;
        const closestLen = closest.elements.filter((el) => checkTextType(el, type)).length;
        return currentLen - n <= closestLen - n ? current : closest;
      });
    }

    const targetLen = target.elements.filter((el) => checkTextType(el, type)).length;
    return templates.filter((slide) => slide.elements.filter((el) => checkTextType(el, type)).length === targetLen);
  };

  const countChartSlots = (slide: Slide) => {
    const marked = slide.elements.filter((el) => el.type === "chart" && (el as any).chartMark === "item").length;
    if (marked > 0) return marked;
    return slide.elements.filter((el) => el.type === "chart").length;
  };

  const countTextItemSlots = (slide: Slide) =>
    slide.elements.filter(
      (el) =>
        (el.type === "text" && (el as any).textType === "item") ||
        (el.type === "shape" && (el as any).text?.type === "item"),
    ).length;

  const getUseableContentTemplates = (templates: Slide[], items: AnyContentItem[]) => {
    const needChart = items.filter(isChartItem).length;
    const needText = items.filter((it) => isTextItem(it) || isLegacyTextItem(it)).length;
    const needImage = items.filter(isImageItem).length;

    let candidates = templates.filter(
      (slide) =>
        countChartSlots(slide) >= needChart &&
        countTextItemSlots(slide) >= needText &&
        (needImage === 0 || countImageItemSlots(slide) >= needImage),
    );

    if (candidates.length === 0) {
      if (needImage > 0) {
        candidates = templates
          .filter((slide) => countImageItemSlots(slide) > 0)
          .sort(
            (a, b) =>
              countImageItemSlots(b) - countImageItemSlots(a) ||
              countChartSlots(b) - countChartSlots(a) ||
              countTextItemSlots(b) - countTextItemSlots(a),
          );
      } else if (needChart > 0) {
        candidates = templates
          .filter((slide) => countChartSlots(slide) > 0)
          .sort((a, b) => countChartSlots(b) - countChartSlots(a) || countTextItemSlots(b) - countTextItemSlots(a));
      } else {
        return getUseableTemplates(templates, needText, "item");
      }
    }

    const score = (slide: Slide) => {
      const cOverflow = Math.max(0, countChartSlots(slide) - needChart);
      const tOverflow = Math.max(0, countTextItemSlots(slide) - needText);
      const iOverflow = Math.max(0, countImageItemSlots(slide) - needImage);
      return iOverflow * 10000 + cOverflow * 100 + tOverflow;
    };

    const bestScore = Math.min(...candidates.map(score));
    return candidates.filter((s) => score(s) === bestScore);
  };

  const getAdaptedFontsize = ({
    text,
    fontSize,
    fontFamily,
    width,
    maxLine,
  }: {
    text: string;
    fontSize: number;
    fontFamily: string;
    width: number;
    maxLine: number;
  }) => {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d")!;

    let newFontSize = fontSize;
    const minFontSize = 10;

    while (newFontSize >= minFontSize) {
      context.font = `${newFontSize}px ${fontFamily}`;
      const textWidth = context.measureText(text).width;
      const line = Math.ceil(textWidth / width);

      if (line <= maxLine) return newFontSize;

      const step = newFontSize <= 22 ? 1 : 2;
      newFontSize = newFontSize - step;
    }

    return minFontSize;
  };

  const getFontInfo = (htmlString: string) => {
    const fontSizeRegex = /font-size:\s*(\d+(?:\.\d+)?)\s*px/i;
    const fontFamilyRegex = /font-family:\s*['"]?([^'";]+)['"]?\s*(?=;|>|$)/i;

    const defaultInfo = {
      fontSize: 16,
      fontFamily: "Microsoft Yahei",
    };

    const fontSizeMatch = htmlString.match(fontSizeRegex);
    const fontFamilyMatch = htmlString.match(fontFamilyRegex);

    return {
      fontSize: fontSizeMatch ? +fontSizeMatch[1]!.trim() : defaultInfo.fontSize,
      fontFamily: fontFamilyMatch ? fontFamilyMatch[1]!.trim() : defaultInfo.fontFamily,
    };
  };

  const getNewTextElement = ({
    el,
    text,
    maxLine,
    longestText,
    digitPadding,
  }: {
    el: PPTTextElement | PPTShapeElement;
    text: string;
    maxLine: number;
    longestText?: string;
    digitPadding?: boolean;
  }): PPTTextElement | PPTShapeElement => {
    const padding = 10;
    const width = el.width - padding * 2 - 2;

    let content = el.type === "text" ? el.content : el.text!.content;
    const fontInfo = getFontInfo(content);
    const size = getAdaptedFontsize({
      text: longestText || text,
      fontSize: fontInfo.fontSize,
      fontFamily: fontInfo.fontFamily,
      width,
      maxLine,
    });

    const parser = new DOMParser();
    const doc = parser.parseFromString(content, "text/html");

    const treeWalker = document.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
    const firstTextNode = treeWalker.nextNode();
    if (firstTextNode) {
      if (digitPadding && firstTextNode.textContent && firstTextNode.textContent.length === 2 && text.length === 1) {
        firstTextNode.textContent = "0" + text;
      } else {
        firstTextNode.textContent = text;
      }
    }

    if (doc.body.innerHTML.indexOf("font-size") === -1) {
      const p = doc.querySelector("p");
      if (p) p.style.fontSize = "16px";
    }

    content = doc.body.innerHTML.replace(/font-size:(.+?)px/g, `font-size: ${size}px`);

    return el.type === "text"
      ? { ...el, content, lineHeight: size < 15 ? 1.2 : el.lineHeight }
      : { ...el, text: { ...el.text!, content } };
  };

  const getNewChartElement = (el: PPTChartElement, item: AIPPTContentChartItem): PPTChartElement => {
    const legends = item.series.map((s) => s.name ?? "");
    const series = item.series.map((s) => s.data);
    return {
      ...el,
      chartType: item.chartType,
      data: {
        labels: item.labels,
        series,
        legends,
      },
      options: { ...(el.options || {}), ...(item.options || {}) },
      themeColors: item.themeColors || el.themeColors,
      textColor: item.textColor || el.textColor,
    };
  };

  const getUseableImage = (el: PPTImageElement): ImgPoolItem | null => {
    if (!imgPool.length) return null;

    let imgs: ImgPoolItem[] = [];
    if (el.width === el.height) imgs = imgPool.filter((img) => img.width === img.height);
    else if (el.width > el.height) imgs = imgPool.filter((img) => img.width > img.height);
    else imgs = imgPool.filter((img) => img.width <= img.height);
    if (!imgs.length) imgs = imgPool;

    const picked = imgs[Math.floor(Math.random() * imgs.length)];
    imgPool = imgPool.filter((item) => item.id !== picked.id);
    return picked;
  };

  const getNewImgElement = (el: PPTImageElement): PPTImageElement => {
    const img = getUseableImage(el);
    if (!img) return el;

    // 保持模板中图片槽位的几何与裁剪（clip/filters 等）不变，
    // 仅替换图片源，避免破坏模板的圆形/异形裁剪与布局。
    return { ...el, src: img.src };
  };

  /**
   * PPT 内容生成映射器（生成器函数）
   * @param templateSlides 模板幻灯片
   * @param _AISlides AI生成的幻灯片数据
   * @param imgs 图片资源
   */
  function* AIPPTGenerator(templateSlides: Slide[], _AISlides: AIPPTSlide[], imgs?: ImgPoolItem[]) {
    if (imgs) imgPool = [...imgs];

    const AISlides: AIPPTSlide[] = [];

    // 预处理：根据内容数量进行分页
    for (const template of _AISlides) {
      if (template.type === "content") {
        const items = template.data.items as AnyContentItem[];
        if (items.length === 5 || items.length === 6) {
          const items1 = items.slice(0, 3);
          const items2 = items.slice(3);
          AISlides.push({ ...template, data: { ...template.data, items: items1 } });
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 3 } as any);
        } else if (items.length === 7 || items.length === 8) {
          const items1 = items.slice(0, 4);
          const items2 = items.slice(4);
          AISlides.push({ ...template, data: { ...template.data, items: items1 } });
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 4 } as any);
        } else if (items.length === 9 || items.length === 10) {
          const items1 = items.slice(0, 3);
          const items2 = items.slice(3, 6);
          const items3 = items.slice(6);
          AISlides.push({ ...template, data: { ...template.data, items: items1 } });
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 3 } as any);
          AISlides.push({ ...template, data: { ...template.data, items: items3 }, offset: 6 } as any);
        } else if (items.length > 10) {
          const items1 = items.slice(0, 4);
          const items2 = items.slice(4, 8);
          const items3 = items.slice(8);
          AISlides.push({ ...template, data: { ...template.data, items: items1 } });
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 4 } as any);
          AISlides.push({ ...template, data: { ...template.data, items: items3 }, offset: 8 } as any);
        } else {
          AISlides.push(template);
        }
      } else if (template.type === "contents") {
        const items = template.data.items;
        if (items.length === 11) {
          const items1 = items.slice(0, 6);
          const items2 = items.slice(6);
          AISlides.push({ ...template, data: { ...template.data, items: items1 } });
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 6 } as any);
        } else if (items.length > 11) {
          const items1 = items.slice(0, 10);
          const items2 = items.slice(10);
          AISlides.push({ ...template, data: { ...template.data, items: items1 } });
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 10 } as any);
        } else {
          AISlides.push(template);
        }
      } else if ((template as any).type === "reference") {
        const references = (template as any).data.references;
        const totalCount = references.length;

        if (totalCount <= 10) {
          AISlides.push(template);
        } else if (totalCount <= 20) {
          const perPage = Math.ceil(totalCount / 2);
          const refs1 = references.slice(0, perPage);
          const refs2 = references.slice(perPage);
          AISlides.push({ ...(template as any), data: { ...(template as any).data, references: refs1 } });
          AISlides.push({ ...(template as any), data: { ...(template as any).data, references: refs2 }, offset: perPage });
        } else if (totalCount <= 30) {
          const refs1 = references.slice(0, 10);
          const refs2 = references.slice(10, 20);
          const refs3 = references.slice(20);
          AISlides.push({ ...(template as any), data: { ...(template as any).data, references: refs1 } });
          AISlides.push({ ...(template as any), data: { ...(template as any).data, references: refs2 }, offset: 10 });
          AISlides.push({ ...(template as any), data: { ...(template as any).data, references: refs3 }, offset: 20 });
        } else {
          let offset = 0;
          while (offset < totalCount) {
            const pageRefs = references.slice(offset, offset + 10);
            AISlides.push({ ...(template as any), data: { ...(template as any).data, references: pageRefs }, offset });
            offset += 10;
          }
        }
      } else {
        AISlides.push(template);
      }
    }

    const coverTemplates = templateSlides.filter((slide) => slide.type === "cover");
    const contentsTemplates = templateSlides.filter((slide) => slide.type === "contents");
    const transitionTemplates = templateSlides.filter((slide) => slide.type === "transition");
    const contentTemplates = templateSlides.filter((slide) => slide.type === "content");
    const referenceTemplates = templateSlides.filter((slide) => slide.type === "reference");
    const endTemplates = templateSlides.filter((slide) => slide.type === "end");

    if (!transitionTemplate && transitionTemplates.length) {
      transitionTemplate = transitionTemplates[Math.floor(Math.random() * transitionTemplates.length)]!;
    }

    for (const item of AISlides) {
      if (item.type === "cover") {
        const coverTemplate = coverTemplates[Math.floor(Math.random() * coverTemplates.length)]!;
        const elements = coverTemplate.elements.map((el) => {
          if (el.type === "image" && (el as any).imageType && imgPool.length) return getNewImgElement(el as PPTImageElement);
          if (el.type !== "text" && el.type !== "shape") return el;
          if (checkTextType(el, "title") && item.data.title) {
            return getNewTextElement({ el: el as any, text: item.data.title, maxLine: 1 });
          }
          if (checkTextType(el, "content") && (item as any).data.text) {
            return getNewTextElement({ el: el as any, text: (item as any).data.text, maxLine: 3 });
          }
          return el;
        });
        yield { ...coverTemplate, id: randomId(10), elements };
      } else if (item.type === "contents") {
        const _contentsTemplates = getUseableTemplates(contentsTemplates, item.data.items.length, "item");
        const contentsTemplate = _contentsTemplates[Math.floor(Math.random() * _contentsTemplates.length)]!;

        const sortedNumberItems = contentsTemplate.elements.filter((el) => checkTextType(el, "itemNumber"));
        const sortedNumberItemIds = sortedNumberItems
          .sort((a, b) => {
            if (sortedNumberItems.length > 6) {
              let aContent = "",
                bContent = "";
              if (a.type === "text") aContent = (a as PPTTextElement).content;
              if (a.type === "shape") aContent = (a as PPTShapeElement).text!.content;
              if (b.type === "text") bContent = (b as PPTTextElement).content;
              if (b.type === "shape") bContent = (b as PPTShapeElement).text!.content;
              if (aContent && bContent) return parseInt(aContent) - parseInt(bContent);
            }
            const aIndex = a.left + a.top * 2;
            const bIndex = b.left + b.top * 2;
            return aIndex - bIndex;
          })
          .map((el) => el.id);

        const sortedItems = contentsTemplate.elements.filter((el) => checkTextType(el, "item"));
        const sortedItemIds = sortedItems
          .sort((a, b) => {
            if (sortedItems.length > 6) {
              const aItemNumber = sortedNumberItems.find((item) => item.groupId === a.groupId);
              const bItemNumber = sortedNumberItems.find((item) => item.groupId === b.groupId);
              if (aItemNumber && bItemNumber) {
                let aContent = "",
                  bContent = "";
                if (aItemNumber.type === "text") aContent = (aItemNumber as PPTTextElement).content;
                if (aItemNumber.type === "shape") aContent = (aItemNumber as PPTShapeElement).text!.content;
                if (bItemNumber.type === "text") bContent = (bItemNumber as PPTTextElement).content;
                if (bItemNumber.type === "shape") bContent = (bItemNumber as PPTShapeElement).text!.content;
                if (aContent && bContent) return parseInt(aContent) - parseInt(bContent);
              }
            }
            const aIndex = a.left + a.top * 2;
            const bIndex = b.left + b.top * 2;
            return aIndex - bIndex;
          })
          .map((el) => el.id);

        const longestText = item.data.items.reduce(
          (longest, current) => (current.length > longest.length ? current : longest),
          "",
        );

        const unusedElIds: string[] = [];
        const unusedGroupIds: string[] = [];

        const elements = contentsTemplate.elements
          .map((el) => {
            if (el.type === "image" && (el as any).imageType && imgPool.length) return getNewImgElement(el as PPTImageElement);
            if (el.type !== "text" && el.type !== "shape") return el;

            if (checkTextType(el, "item")) {
              const index = sortedItemIds.findIndex((id) => id === el.id);
              const itemTitle = item.data.items[index];
              if (itemTitle) return getNewTextElement({ el: el as any, text: itemTitle, maxLine: 1, longestText });

              unusedElIds.push(el.id);
              if (el.groupId) unusedGroupIds.push(el.groupId);
            }

            if (checkTextType(el, "itemNumber")) {
              const index = sortedNumberItemIds.findIndex((id) => id === el.id);
              const offset = (item as any).offset || 0;
              return getNewTextElement({
                el: el as any,
                text: index + offset + 1 + "",
                maxLine: 1,
                digitPadding: true,
              });
            }

            return el;
          })
          .filter((el) => !unusedElIds.includes(el.id) && !(el.groupId && unusedGroupIds.includes(el.groupId)));

        yield { ...contentsTemplate, id: randomId(10), elements };
      } else if (item.type === "transition") {
        transitionIndex += 1;
        const tpl = transitionTemplate || transitionTemplates[0];
        if (!tpl) continue;

        const elements = tpl.elements.map((el) => {
          if (el.type === "image" && (el as any).imageType && imgPool.length) return getNewImgElement(el as PPTImageElement);
          if (el.type !== "text" && el.type !== "shape") return el;
          if (checkTextType(el, "title") && item.data.title) {
            return getNewTextElement({ el: el as any, text: item.data.title, maxLine: 1 });
          }
          if (checkTextType(el, "content") && item.data.text) {
            return getNewTextElement({ el: el as any, text: item.data.text, maxLine: 3 });
          }
          if (checkTextType(el, "partNumber")) {
            return getNewTextElement({ el: el as any, text: transitionIndex + "", maxLine: 1, digitPadding: true });
          }
          return el;
        });
        yield { ...tpl, id: randomId(10), elements };
      } else if (item.type === "content") {
        const _contentTemplates = getUseableContentTemplates(contentTemplates, item.data.items);
        const contentTemplate = _contentTemplates[Math.floor(Math.random() * _contentTemplates.length)]!;

        const items = item.data.items as AnyContentItem[];

        const sortedTitleItemIds = contentTemplate.elements
          .filter((el) => checkTextType(el, "itemTitle"))
          .sort((a, b) => a.left + a.top * 2 - (b.left + b.top * 2))
          .map((el) => el.id);

        const sortedSubtitleIds = contentTemplate.elements
          .filter((el) => checkTextType(el, "subtitle"))
          .sort((a, b) => a.left + a.top * 2 - (b.left + b.top * 2))
          .map((el) => el.id);

        const sortedImageItemFigureIds = contentTemplate.elements
          .filter((el) => checkImageType(el, "itemFigure"))
          .sort((a, b) => a.left + a.top * 2 - (b.left + b.top * 2))
          .map((el) => el.id);

        const sortedTextItemIds = contentTemplate.elements
          .filter((el) => checkTextType(el, "item"))
          .sort((a, b) => a.left + a.top * 2 - (b.left + b.top * 2))
          .map((el) => el.id);

        const sortedContentForImageIds = contentTemplate.elements
          .filter((el) => checkTextType(el, "content"))
          .sort((a, b) => a.left + a.top * 2 - (b.left + b.top * 2))
          .map((el) => el.id);

        let sortedChartItemIds = contentTemplate.elements
          .filter((el) => checkChartItemMark(el))
          .sort((a, b) => a.left + a.top * 2 - (b.left + b.top * 2))
          .map((el) => el.id);

        if (sortedChartItemIds.length === 0) {
          sortedChartItemIds = contentTemplate.elements
            .filter((el) => el.type === "chart")
            .sort((a, b) => a.left + a.top * 2 - (b.left + b.top * 2))
            .map((el) => el.id);
        }

        const sortedNumberItemIds = contentTemplate.elements
          .filter((el) => checkTextType(el, "itemNumber"))
          .sort((a, b) => a.left + a.top * 2 - (b.left + b.top * 2))
          .map((el) => el.id);

        const textTitleList: string[] = [];
        const textBodyList: string[] = [];
        items.forEach((_it) => {
          if (isTextItem(_it) || isLegacyTextItem(_it)) {
            if (_it.title) textTitleList.push(_it.title);
            if (_it.text) textBodyList.push(_it.text);
          }
        });
        const longestTitle = textTitleList.reduce(
          (longest, current) => (current.length > longest.length ? current : longest),
          "",
        );
        const longestText = textBodyList.reduce(
          (longest, current) => (current.length > longest.length ? current : longest),
          "",
        );

        const chartItems = items.filter(isChartItem) as AIPPTContentChartItem[];
        const imageItems = items.filter(isImageItem) as AIPPTContentImageItem[];
        const hasImageItems = imageItems.length > 0;

        const elements = contentTemplate.elements.map((el) => {
          if (hasImageItems) {
            if (checkImageType(el, "itemFigure")) {
              const idx = sortedImageItemFigureIds.findIndex((id) => id === el.id);
              const it = imageItems[idx];
              if (it && it.src) {
                const imgEl = el as PPTImageElement;
                return { ...imgEl, src: it.src };
              }
              return el;
            }

            if (checkTextType(el, "subtitle")) {
              const idx = sortedSubtitleIds.findIndex((id) => id === el.id);
              const it = imageItems[idx];
              if (it && it.title) return getNewTextElement({ el: el as any, text: it.title, maxLine: 1 });
              return el;
            }

            if (checkTextType(el, "content")) {
              const idx = sortedContentForImageIds.findIndex((id) => id === el.id);
              const it = imageItems[idx];
              if (it && it.text) return getNewTextElement({ el: el as any, text: it.text, maxLine: 6 });
            }
          }

          if (el.type === "image" && (el as any).imageType && imgPool.length) return getNewImgElement(el as PPTImageElement);

          if (el.type === "chart") {
            const idx = sortedChartItemIds.findIndex((id) => id === el.id);
            const chartItem = chartItems[idx];
            if (chartItem) return getNewChartElement(el as PPTChartElement, chartItem);
            return el;
          }

          if (el.type !== "text" && el.type !== "shape") return el;

          if (items.length === 1) {
            const only = items[0]!;
            if ((isTextItem(only) || isLegacyTextItem(only)) && checkTextType(el, "content") && (only as any).text) {
              return getNewTextElement({ el: el as any, text: (only as any).text, maxLine: 6 });
            }
            if (isChartItem(only) && checkTextType(el, "content") && only.text) {
              return getNewTextElement({ el: el as any, text: only.text, maxLine: 6 });
            }
          } else {
            if (checkTextType(el, "itemTitle")) {
              const index = sortedTitleItemIds.findIndex((id) => id === el.id);
              const contentItem = items[index];
              if (contentItem) {
                if (isTextItem(contentItem) && contentItem.title) {
                  return getNewTextElement({
                    el: el as any,
                    text: contentItem.title,
                    longestText: longestTitle,
                    maxLine: 1,
                  });
                }
                if (isLegacyTextItem(contentItem) && contentItem.title) {
                  return getNewTextElement({
                    el: el as any,
                    text: contentItem.title,
                    longestText: longestTitle,
                    maxLine: 1,
                  });
                }
                if (isChartItem(contentItem) && contentItem.title) {
                  return getNewTextElement({
                    el: el as any,
                    text: contentItem.title,
                    longestText: longestTitle || contentItem.title,
                    maxLine: 1,
                  });
                }
              }
            }

            if (checkTextType(el, "item")) {
              const index = sortedTextItemIds.findIndex((id) => id === el.id);
              const contentItem = items[index];
              if (contentItem) {
                if (isTextItem(contentItem) && contentItem.text) {
                  return getNewTextElement({ el: el as any, text: contentItem.text, longestText, maxLine: 4 });
                }
                if (isLegacyTextItem(contentItem) && contentItem.text) {
                  return getNewTextElement({ el: el as any, text: contentItem.text, longestText, maxLine: 4 });
                }
              }
            }

            if (checkTextType(el, "itemNumber")) {
              const index = sortedNumberItemIds.findIndex((id) => id === el.id);
              const offset = (item as any).offset || 0;
              return getNewTextElement({ el: el as any, text: index + offset + 1 + "", maxLine: 1, digitPadding: true });
            }
          }

          if (checkTextType(el, "title") && (item as any).data.title) {
            return getNewTextElement({ el: el as any, text: (item as any).data.title, maxLine: 1 });
          }
          return el;
        });

        yield { ...contentTemplate, id: randomId(10), elements };
      } else if ((item as any).type === "reference") {
        const referenceCount = (item as any).data.references.length;

        let _referenceTemplates: Slide[] = [];
        _referenceTemplates = referenceTemplates.filter((slide) => {
          const refNumberCount = slide.elements.filter((el) => checkTextType(el, "referenceNumber" as any)).length;
          return refNumberCount >= referenceCount && refNumberCount <= 10;
        });

        if (_referenceTemplates.length === 0) {
          _referenceTemplates = getUseableTemplates(referenceTemplates, referenceCount, "referenceNumber" as any);
        }

        const referenceTemplate = _referenceTemplates[Math.floor(Math.random() * _referenceTemplates.length)]!;

        const sortedReferenceNumberIds = referenceTemplate.elements
          .filter((el) => checkTextType(el, "referenceNumber" as any))
          .sort((a, b) => a.left + a.top * 2 - (b.left + b.top * 2))
          .map((el) => el.id);

        const sortedReferenceTextIds = referenceTemplate.elements
          .filter((el) => checkTextType(el, "item" as any))
          .sort((a, b) => a.left + a.top * 2 - (b.left + b.top * 2))
          .map((el) => el.id);

        const references = (item as any).data.references as { text: string }[];
        const longest = references.reduce((longest, current) => (current.text.length > longest.length ? current.text : longest), "");

        const unusedElIds: string[] = [];
        const elements = referenceTemplate.elements
          .map((el) => {
            if (el.type === "image" && (el as any).imageType && imgPool.length) return getNewImgElement(el as PPTImageElement);
            if (el.type !== "text" && el.type !== "shape") return el;

            if (checkTextType(el, "referenceNumber" as any)) {
              const index = sortedReferenceNumberIds.findIndex((id) => id === el.id);
              const offset = (item as any).offset || 0;
              const no = references[index] ? index + offset + 1 : null;
              if (no === null) {
                unusedElIds.push(el.id);
                return el;
              }
              return getNewTextElement({ el: el as any, text: String(no), maxLine: 1, digitPadding: true });
            }

            if (checkTextType(el, "item" as any)) {
              const index = sortedReferenceTextIds.findIndex((id) => id === el.id);
              const ref = references[index];
              if (ref?.text) return getNewTextElement({ el: el as any, text: ref.text, maxLine: 3, longestText: longest });
              unusedElIds.push(el.id);
              return el;
            }

            if (checkTextType(el, "title") && (item as any).data.title) {
              return getNewTextElement({ el: el as any, text: (item as any).data.title, maxLine: 1 });
            }
            return el;
          })
          .filter((el) => !unusedElIds.includes(el.id));

        yield { ...referenceTemplate, id: randomId(10), elements };
      } else if (item.type === "end") {
        const endTemplate = endTemplates[Math.floor(Math.random() * endTemplates.length)]!;
        yield { ...endTemplate, id: randomId(10) };
      }
    }
  }

  const generateSlides = (templateSlides: Slide[], slides: AIPPTSlide[], imgs?: ImgPoolItem[]) => {
    return [...AIPPTGenerator(templateSlides, slides, imgs)];
  };

  return {
    reset,
    presetImgPool,
    generateSlides,
    AIPPTGenerator,
  };
}
