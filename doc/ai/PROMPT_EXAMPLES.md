# 一些prompt示例
图表的渲染，我的生成PPT的代码，模版，还有数据如下，代码会根据模版和数据进行渲染，生成图表
核心文件
src/types/AIPPT.ts src/hooks/useAIPPT.ts src/views/components/element/ChartElement
处理逻辑：
src/types/AIPPT.ts中定义图表的类型 AIPPTContentChartItem， 支持 ECharts-like 的数据格式（labels 对应横轴或扇区，series 是多维数据集）。
export type AIPPTChartType = 'line' | 'bar' | 'pie'

src/hooks/useAIPPT.ts中的isChartItem判断返回的数据类型是否为AIPPTContentChartItem，然后进行渲染

模板匹配逻辑，AIPPTGenerator() 中，处理 item.type === 'content' 的部分
找到可用的模版
const _contentTemplates = getUseableContentTemplates(contentTemplates, items)

getNewChartElement 负责核心渲染
AIPPTContentChartItem → isChartItem → getNewChartElement → PPTChartElement → ChartRenderer
src/views/components/element/ChartElement， 内部真正渲染图表的部分交给 <Chart /> 子组件处理。src/views/components/element/ChartElement/Chart.vue中的echarts进行最终渲染。


数据：
[
    {
        "kind": "chart",
        "title": "2025 上半年活跃用户",
        "text": "2025 上半年活跃用户text",
        "chartType": "line",
        "labels": [
            "1月",
            "2月",
            "3月",
            "4月",
            "5月",
            "6月"
        ],
        "series": [
            {
                "name": "iOS",
                "data": [
                    12,
                    15,
                    18,
                    22,
                    24,
                    27
                ]
            },
            {
                "name": "Android",
                "data": [
                    10,
                    13,
                    17,
                    20,
                    23,
                    25
                ]
            }
        ],
        "options": {
            "legend": {
                "top": 8
            },
            "xAxis": {
                "boundaryGap": false
            },
            "yAxis": {
                "name": "万"
            }
        }
    }
]


匹配的模版
{
    "id": "gLwjShOKqV",
    "elements": [
        {
            "type": "image",
            "id": "HR7WY_Ua4K",
            "src": "https://images.pexels.com/photos/29968980/pexels-photo-29968980.jpeg?auto=compress&cs=tinysrgb&w=600",
            "width": 372.8317223198594,
            "height": 562.5,
            "left": 0,
            "top": 0,
            "fixedRatio": true,
            "rotate": 0,
            "lock": true,
            "radius": 0,
            "filters": {
                "grayscale": "100%"
            },
            "imageType": "pageFigure"
        },
        {
            "type": "text",
            "id": "iDNXMfOQas",
            "left": 451.4176786773429,
            "top": 52.26334519572953,
            "width": 510.82443653618026,
            "height": 56,
            "content": "<p style=\"\"><span style=\"font-size: 36px;\"><span style=\"color: rgb(155, 0, 0);\">模板内容页标题</span></span></p>",
            "rotate": 0,
            "defaultFontName": "",
            "defaultColor": "#333",
            "vertical": false,
            "lineHeight": 1,
            "paragraphSpace": 0,
            "textType": "title"
        },
        {
            "type": "shape",
            "id": "FbzdiQDJ_N",
            "left": 419.4176786773429,
            "top": 64.26334519572953,
            "width": 32,
            "height": 32,
            "viewBox": [
                200,
                200
            ],
            "path": "M 0 0 L 80 0 L 200 100 L 80 200 L 0 200 L 120 100 L 0 0 Z",
            "fill": "rgb(155, 0, 0)",
            "fixedRatio": true,
            "rotate": 0,
            "lock": false
        },
        {
            "type": "text",
            "id": "cdIpGuod9c",
            "left": 419.4176786773429,
            "top": 150.18886230728336,
            "width": 542.8244365361803,
            "height": 92,
            "content": "<p style=\"\">内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项正文内容项</p>",
            "rotate": 0,
            "defaultFontName": "",
            "defaultColor": "#333",
            "vertical": false,
            "textType": "content"
        },
        {
            "type": "line",
            "id": "HD2su2VCDC",
            "left": 419.4176786773429,
            "top": 123.04141353244943,
            "start": [
                0,
                0
            ],
            "end": [
                540.4804270462632,
                0
            ],
            "points": [
                "",
                ""
            ],
            "color": "rgb(155, 0, 0)",
            "style": "solid",
            "width": 2,
            "lock": false
        },
        {
            "type": "shape",
            "id": "TQV5PxJWky",
            "left": 952.2597864768684,
            "top": 11.378540183867166,
            "width": 36.65230204626337,
            "height": 36.65230204626337,
            "viewBox": [
                36.65230204626337,
                36.65230204626337
            ],
            "path": "M 0 0 L 0 36.65230204626337 L 36.65230204626337 36.65230204626337 L 36.65230204626337 32.98707184163703 L 3.6652302046263374 32.98707184163703 L 3.6652302046263374 0 Z",
            "fill": "rgb(155, 0, 0)",
            "fixedRatio": false,
            "rotate": 180,
            "pathFormula": "L",
            "keypoints": [
                0.1
            ],
            "lock": true
        },
        {
            "type": "shape",
            "id": "I5KUVlgMTr",
            "left": 952.2597864768684,
            "top": 513.6679826512456,
            "width": 36.65230204626337,
            "height": 36.65230204626337,
            "viewBox": [
                36.65230204626337,
                36.65230204626337
            ],
            "path": "M 0 0 L 0 36.65230204626337 L 36.65230204626337 36.65230204626337 L 36.65230204626337 32.98707184163703 L 3.6652302046263374 32.98707184163703 L 3.6652302046263374 0 Z",
            "fill": "rgb(155, 0, 0)",
            "fixedRatio": false,
            "rotate": -90,
            "pathFormula": "L",
            "keypoints": [
                0.1
            ],
            "lock": true
        },
        {
            "type": "chart",
            "id": "kAFzeAEdzb",
            "chartType": "bar",
            "left": 486.5768400607973,
            "top": 266.25797448165866,
            "width": 408.5061137692717,
            "height": 254.33280170122276,
            "rotate": 0,
            "themeColors": [
                "#5b9bd5",
                "#ed7d31",
                "#a5a5a5",
                "#ffc000",
                "#4472c4",
                "#70ad47"
            ],
            "textColor": "#333",
            "data": {
                "labels": [
                    "类别1",
                    "类别2",
                    "类别3",
                    "类别4",
                    "类别5"
                ],
                "legends": [
                    "系列1",
                    "系列2"
                ],
                "series": [
                    [
                        12,
                        19,
                        5,
                        2,
                        18
                    ],
                    [
                        7,
                        11,
                        13,
                        21,
                        9
                    ]
                ]
            },
            "chartMark": "item"
        }
    ],
    "background": {
        "type": "solid",
        "color": "#fff"
    },
    "type": "content"
}





文件名: src/types/AIPPT.ts
内容: // 图片信息接口
export interface AIPPTImage {
  id: string
  src: string
  width: number
  height: number
  alt?: string
  photographer?: string
  url?: string
}

// 基础幻灯片接口，包含图片字段
export interface AIPPTBaseSlide {
  images?: AIPPTImage[]
}

export interface AIPPTCover extends AIPPTBaseSlide {
  type: 'cover'
  data: {
    title: string
    text: string
  }
}

export interface AIPPTContents extends AIPPTBaseSlide {
  type: 'contents'
  data: {
    items: string[]
  }
  offset?: number
}

export interface AIPPTTransition extends AIPPTBaseSlide {
  type: 'transition'
  data: {
    title: string
    text: string
  }
}

export type AnyContentItem = AIPPTContentChartItem | AIPPTContentTextItem | AIPPTLegacyTextItem


// ==============================
// 👉 内容页：items 支持“文本项 + 图表项”
//    同时兼容旧结构 { title, text }（无 kind 字段）
// ==============================

/** 旧版（兼容）文本项：无 kind 字段 */
export interface AIPPTLegacyTextItem {
  title: string
  text: string
}

/** 新版文本项：显式带 kind 区分 */
export interface AIPPTContentTextItem {
  kind: 'text'
  title: string
  text: string
}

/** 仅支持的图表类型：折线图(line) / 柱状图(bar) / 饼图(pie) */
export type AIPPTChartType = 'line' | 'bar' | 'pie'

/** 图表序列（数据列） */
export interface AIPPTChartSeries {
  name?: string
  data: number[] // 必须与 labels.length 对齐
}

/** 新增：内容页里的图表项（仅支持 line/bar/pie） */
export interface AIPPTContentChartItem {
  kind: 'chart'
  /** 可选：图表主标题 */
  title?: string
  /** 图表描述文本 */
  text?: string
  /** 折线图/柱状图/饼图 */
  chartType: AIPPTChartType
  /** 类目轴或饼图扇区标签 */
  labels: string[]
  /** 数据序列；饼图仅使用第一组 series */
  series: AIPPTChartSeries[]
  /** 透传到图表渲染层（如 EChartsOption 的增量配置） */
  options?: Record<string, any>
  /** 主题色与文字色（可选） */
  themeColors?: string[]
  textColor?: string
}

/** 内容页可包含的 item 联合类型（含兼容项） */
export type AIPPTContentItem =
  | AIPPTLegacyTextItem
  | AIPPTContentTextItem
  | AIPPTContentChartItem

export interface AIPPTContent extends AIPPTBaseSlide {
  type: 'content'
  data: {
    title: string
    items: AnyContentItem[]
  },
  offset?: number
}

export interface AIPPTReference extends AIPPTBaseSlide {
  type: 'reference'
  data: {
    title: string
    references: {
      text: string
      number?: string | number
      pmid?: string
      url?: string
      doi?: string
    }[]
  }
  offset?: number
}

export interface AIPPTEnd extends AIPPTBaseSlide {
  type: 'end'
}

export type AIPPTSlide =
  | AIPPTCover
  | AIPPTContents
  | AIPPTTransition
  | AIPPTContent
  | AIPPTReference
  | AIPPTEnd

// ==============================
// 类型守卫 & 运行时校验辅助
// ==============================

export function isChartItem(
  item: AIPPTContentItem
): item is AIPPTContentChartItem {
  return (item as any).kind === 'chart'
}

export function isTextItem(
  item: AIPPTContentItem
): item is AIPPTContentTextItem {
  return (item as any).kind === 'text'
}

/** 兼容旧版：没有 kind 但具备 title/text 即视作旧文本项 */
export function isLegacyTextItem(
  item: AIPPTContentItem
): item is AIPPTLegacyTextItem {
  const anyItem = item as any
  return (
    anyItem &&
    anyItem.kind === undefined &&
    typeof anyItem.title === 'string' &&
    typeof anyItem.text === 'string'
  )
}

/** （可选）运行时校验：限制仅 line/bar/pie */
export const SUPPORTED_CHART_TYPES = ['line', 'bar', 'pie'] as const
export function isSupportedChartType(t: any): t is AIPPTChartType {
  return (SUPPORTED_CHART_TYPES as readonly string[]).includes(t)
}

文件名: src/hooks/useAIPPT.ts
内容: import { ref } from 'vue'
import { nanoid } from 'nanoid'
import type {
  ImageClipDataRange,
  PPTElement,
  PPTImageElement,
  PPTShapeElement,
  PPTTextElement,
  PPTChartElement,
  Slide,
  TextType
} from '@/types/slides'
import type { AIPPTSlide, AnyContentItem, AIPPTContentChartItem, AIPPTContentTextItem, AIPPTLegacyTextItem } from '@/types/AIPPT'
import { useSlidesStore } from '@/store'
import useAddSlidesOrElements from './useAddSlidesOrElements'
import useSlideHandler from './useSlideHandler'


const isChartItem = (x: any): x is AIPPTContentChartItem =>
  x && x.kind === 'chart' && Array.isArray(x.labels) && Array.isArray(x.series)
const isTextItem = (x: any): x is AIPPTContentTextItem =>
  x && x.kind === 'text' && typeof x.title === 'string' && typeof x.text === 'string'
const isLegacyTextItem = (x: any): x is AIPPTLegacyTextItem =>
  x && x.kind === undefined && typeof x.title === 'string' && typeof x.text === 'string'

interface ImgPoolItem {
  id: string
  src: string
  width: number
  height: number
}

export default () => {
  const slidesStore = useSlidesStore()
  const { addSlidesFromData, addSlidesFromDataToEnd } = useAddSlidesOrElements()
  const { isEmptySlide } = useSlideHandler()

  // 图片池，用于存储可用的图片资源
  const imgPool = ref<ImgPoolItem[]>([])
  // 过渡页的索引，用于显示章节编号
  const transitionIndex = ref(0)
  // 过渡页模板，确保同一演示文稿中过渡页风格一致
  const transitionTemplate = ref<Slide | null>(null)

  const checkTextType = (el: PPTElement, type: TextType) => {
    return (el.type === 'text' && (el as PPTTextElement).textType === type)
      || (el.type === 'shape' && (el as PPTShapeElement).text && (el as PPTShapeElement).text!.type === type)
  }

  const checkChartItemMark = (el: PPTElement) => {
    return el.type === 'chart' && (el as any).chartMark === 'chartItem'
  }

  /**
   * 获取可用的模板
   * 根据需要的元素数量和类型，选择最合适的模板
   * @param templates 所有可用模板
   * @param n 需要的元素数量
   * @param type 元素的文本类型
   * @returns 合适的模板列表
   */
  const getUseableTemplates = (templates: Slide[], n: number, type: TextType) => {
    // 特殊处理：如果只需要1个元素，尝试使用只有标题和正文的模板
    if (n === 1) {
      const list = templates.filter(slide => {
        const items = slide.elements.filter(el => checkTextType(el, type))
        const titles = slide.elements.filter(el => checkTextType(el, 'title'))
        const texts = slide.elements.filter(el => checkTextType(el, 'content'))

        return !items.length && titles.length === 1 && texts.length === 1
      })

      if (list.length) return list
    }

    let target: Slide | null = null

    // 查找具有足够元素的模板
    const list = templates.filter(slide => {
      const len = slide.elements.filter(el => checkTextType(el, type)).length
      return len >= n
    })

    // 如果没有足够的模板，选择元素最多的模板
    if (list.length === 0) {
      const sorted = templates.sort((a, b) => {
        const aLen = a.elements.filter(el => checkTextType(el, type)).length
        const bLen = b.elements.filter(el => checkTextType(el, type)).length
        return aLen - bLen
      })
      target = sorted[sorted.length - 1]
    }
    else {
      // 选择最接近需求数量的模板
      target = list.reduce((closest, current) => {
        const currentLen = current.elements.filter(el => checkTextType(el, type)).length
        const closestLen = closest.elements.filter(el => checkTextType(el, type)).length
        return (currentLen - n) <= (closestLen - n) ? current : closest
      })
    }

    // 返回所有具有相同元素数量的模板
    return templates.filter(slide => {
      const len = slide.elements.filter(el => checkTextType(el, type)).length
      const targetLen = target!.elements.filter(el => checkTextType(el, type)).length
      return len === targetLen
    })
  }

  const countChartSlots = (slide: Slide) => {
    const marked = slide.elements.filter(el => el.type === 'chart' && (el as any).chartMark === 'chartItem').length
    if (marked > 0) return marked
    return slide.elements.filter(el => el.type === 'chart').length
  }

  const countTextItemSlots = (slide: Slide) =>
    slide.elements.filter(el => (el.type === 'text' && (el as any).textType === 'item') || (el.type === 'shape' && (el as any).text?.type === 'item')).length

  const getUseableContentTemplates = (templates: Slide[], items: AnyContentItem[]) => {
    const needChart = items.filter(isChartItem).length
    const needText = items.filter(it => isTextItem(it) || isLegacyTextItem(it)).length
    // 筛选到的候选模版数量
    let candidates = templates.filter(slide => countChartSlots(slide) >= needChart && countTextItemSlots(slide) >= needText)

    if (candidates.length === 0) {
      if (needChart > 0) {
        candidates = templates
          .filter(slide => countChartSlots(slide) > 0)
          .sort((a, b) => (countChartSlots(b) - countChartSlots(a)) || (countTextItemSlots(b) - countTextItemSlots(a)))
      } else {
        return getUseableTemplates(templates, needText, 'item')
      }
    }

    const score = (slide: Slide) => {
      const cOverflow = Math.max(0, countChartSlots(slide) - needChart)
      const tOverflow = Math.max(0, countTextItemSlots(slide) - needText)
      return cOverflow * 100 + tOverflow
    }
    const bestScore = Math.min(...candidates.map(score))
    return candidates.filter(s => score(s) === bestScore)
  }

  const getAdaptedFontsize = ({
    text,
    fontSize,
    fontFamily,
    width,
    maxLine,
  }: {
    text: string
    fontSize: number
    fontFamily: string
    width: number
    maxLine: number
  }) => {
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')!

    let newFontSize = fontSize
    const minFontSize = 10

    // 逐步减小字体大小，直到文本能在指定行数内显示
    while (newFontSize >= minFontSize) {
      context.font = `${newFontSize}px ${fontFamily}`
      const textWidth = context.measureText(text).width
      const line = Math.ceil(textWidth / width)

      if (line <= maxLine) return newFontSize

      const step = newFontSize <= 22 ? 1 : 2
      newFontSize = newFontSize - step
    }

    return minFontSize
  }

  /**
   * 从HTML字符串中提取字体信息
   * @param htmlString HTML格式的文本内容
   * @returns 字体大小和字体族信息
   */
  const getFontInfo = (htmlString: string) => {
    const fontSizeRegex = /font-size:\s*(\d+(?:\.\d+)?)\s*px/i
    const fontFamilyRegex = /font-family:\s*['"]?([^'";]+)['"]?\s*(?=;|>|$)/i

    const defaultInfo = {
      fontSize: 16,
      fontFamily: 'Microsoft Yahei',
    }

    const fontSizeMatch = htmlString.match(fontSizeRegex)
    const fontFamilyMatch = htmlString.match(fontFamilyRegex)

    return {
      fontSize: fontSizeMatch ? (+fontSizeMatch[1].trim()) : defaultInfo.fontSize,
      fontFamily: fontFamilyMatch ? fontFamilyMatch[1].trim() : defaultInfo.fontFamily,
    }
  }

  /**
   * 创建新的文本元素，自动调整字体大小以适应容器
   * @param params 包含元素、文本内容、最大行数等参数
   * @returns 更新后的文本元素
   */
  const getNewTextElement = ({
    el,
    text,
    maxLine,
    longestText,
    digitPadding,
  }: {
    el: PPTTextElement | PPTShapeElement
    text: string
    maxLine: number
    longestText?: string
    digitPadding?: boolean
  }): PPTTextElement | PPTShapeElement => {
    const padding = 10
    const width = el.width - padding * 2 - 2

    let content = el.type === 'text' ? el.content : el.text!.content

    // 获取原始字体信息
    const fontInfo = getFontInfo(content)

    // 计算适应的字体大小
    const size = getAdaptedFontsize({
      text: longestText || text,
      fontSize: fontInfo.fontSize,
      fontFamily: fontInfo.fontFamily,
      width,
      maxLine,
    })

    // 解析HTML内容并替换文本
    const parser = new DOMParser()
    const doc = parser.parseFromString(content, 'text/html')

    const treeWalker = document.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT)

    const firstTextNode = treeWalker.nextNode()
    if (firstTextNode) {
      // 数字补零处理（用于编号）
      if (digitPadding && firstTextNode.textContent && firstTextNode.textContent.length === 2 && text.length === 1) {
        firstTextNode.textContent = '0' + text
      }
      else firstTextNode.textContent = text
    }

    // 确保有字体大小设置
    if (doc.body.innerHTML.indexOf('font-size') === -1) {
      const p = doc.querySelector('p')
      if (p) p.style.fontSize = '16px'
    }

    // 更新所有字体大小
    content = doc.body.innerHTML.replace(/font-size:(.+?)px/g, `font-size: ${size}px`)

    return el.type === 'text'
      ? { ...el, content, lineHeight: size < 15 ? 1.2 : el.lineHeight }
      : { ...el, text: { ...el.text!, content } }
  }

  const getNewChartElement = (el: PPTChartElement, item: AIPPTContentChartItem): PPTChartElement => {
    const legends = item.series.map(s => s.name ?? '')
    const series = item.series.map(s => s.data)
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
    }
  }

  const getUseableImage = (el: PPTImageElement): ImgPoolItem | null => {
    let img: ImgPoolItem | null = null

    let imgs = []

    // 根据元素的宽高比选择合适的图片
    if (el.width === el.height) imgs = imgPool.value.filter(img => img.width === img.height)
    else if (el.width > el.height) imgs = imgPool.value.filter(img => img.width > img.height)
    else imgs = imgPool.value.filter(img => img.width <= img.height)
    if (!imgs.length) imgs = imgPool.value

    // 随机选择一张图片并从池中移除
    img = imgs[Math.floor(Math.random() * imgs.length)]
    imgPool.value = imgPool.value.filter(item => item.id !== img!.id)

    return img
  }

  /**
   * 创建新的图片元素，自动裁剪以适应容器
   * @param el 原始图片元素
   * @returns 更新后的图片元素
   */
  const getNewImgElement = (el: PPTImageElement): PPTImageElement => {
    const img = getUseableImage(el)
    if (!img) return el

    // 计算裁剪范围以保持宽高比
    let scale = 1
    let w = el.width
    let h = el.height
    let range: ImageClipDataRange = [[0, 0], [0, 0]]
    const radio = el.width / el.height

    if (img.width / img.height >= radio) {
      // 图片更宽，左右裁剪
      scale = img.height / el.height
      w = img.width / scale
      const diff = (w - el.width) / 2 / w * 100
      range = [[diff, 0], [100 - diff, 100]]
    }
    else {
      // 图片更高，上下裁剪
      scale = img.width / el.width
      h = img.height / scale
      const diff = (h - el.height) / 2 / h * 100
      range = [[0, diff], [100, 100 - diff]]
    }

    const clipShape = (el.clip && el.clip.shape) ? el.clip.shape : 'rect'
    const clip = { range, shape: clipShape }
    const src = img.src

    return { ...el, src, clip }
  }

  /**
   * 提取Markdown内容
   * @param content 原始内容
   * @returns 提取的Markdown内容
   */
  const getMdContent = (content: string) => {
    const regex = /```markdown([^```]*)```/
    const match = content.match(regex)
    if (match) return match[1].trim()
    return content.replace('```markdown', '').replace('```', '')
  }

  /**
   * 提取JSON内容
   * @param content 原始内容
   * @returns 提取的JSON内容
   */
  const getJSONContent = (content: string) => {
    const regex = /```json([^```]*)```/
    const match = content.match(regex)
    if (match) return match[1].trim()
    return content.replace('```json', '').replace('```', '')
  }

  /**
   * 预设图片池
   * @param imgs 图片列表
   */
  const presetImgPool = (imgs: ImgPoolItem[]) => {
    imgPool.value = imgs
  }

  /**
   * AI PPT生成器（生成器函数）
   * @param templateSlides 模板幻灯片
   * @param _AISlides AI生成的幻灯片数据
   * @param imgs 图片资源
   */
  function* AIPPTGenerator(templateSlides: Slide[], _AISlides: AIPPTSlide[], imgs?: ImgPoolItem[]) {
    if (imgs) imgPool.value = imgs

    const AISlides: AIPPTSlide[] = []

    // 预处理：根据内容数量进行分页
    for (const template of _AISlides) {
      if (template.type === 'content') {
        const items = (template.data.items as AnyContentItem[])
        if (items.length === 5 || items.length === 6) {
          // 5-6个项目：分成2页（3+剩余）
          const items1 = items.slice(0, 3)
          const items2 = items.slice(3)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 3 })
        }
        else if (items.length === 7 || items.length === 8) {
          // 7-8个项目：分成2页（4+剩余）
          const items1 = items.slice(0, 4)
          const items2 = items.slice(4)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 4 })
        }
        else if (items.length === 9 || items.length === 10) {
          // 9-10个项目：分成3页（3+3+剩余）
          const items1 = items.slice(0, 3)
          const items2 = items.slice(3, 6)
          const items3 = items.slice(6)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 3 })
          AISlides.push({ ...template, data: { ...template.data, items: items3 }, offset: 6 })
        }
        else if (items.length > 10) {
          // 超过10个项目：分成3页（4+4+剩余）
          const items1 = items.slice(0, 4)
          const items2 = items.slice(4, 8)
          const items3 = items.slice(8)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 4 })
          AISlides.push({ ...template, data: { ...template.data, items: items3 }, offset: 8 })
        }
        else {
          AISlides.push(template)
        }
      }
      else if (template.type === 'contents') {
        // 目录页分页逻辑：每页最多10个项目
        const items = template.data.items
        if (items.length === 11) {
          // 11个项目：分成2页（6+5）
          const items1 = items.slice(0, 6)
          const items2 = items.slice(6)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 6 })
        }
        else if (items.length > 11) {
          // 超过11个项目：分成2页（10+剩余）
          const items1 = items.slice(0, 10)
          const items2 = items.slice(10)
          AISlides.push({ ...template, data: { ...template.data, items: items1 } })
          AISlides.push({ ...template, data: { ...template.data, items: items2 }, offset: 10 })
        }
        else {
          AISlides.push(template)
        }
      }
      else if (template.type === 'reference') {
        // 引用页分页逻辑：每页5-10个引用
        const references = template.data.references
        const totalCount = references.length

        if (totalCount <= 10) {
          // 10个及以下：一页显示
          AISlides.push(template)
        }
        else if (totalCount <= 20) {
          // 11-20个：分成2页，尽量平均分配
          const perPage = Math.ceil(totalCount / 2)
          const refs1 = references.slice(0, perPage)
          const refs2 = references.slice(perPage)
          AISlides.push({ ...template, data: { ...template.data, references: refs1 } })
          AISlides.push({ ...template, data: { ...template.data, references: refs2 }, offset: perPage })
        }
        else if (totalCount <= 30) {
          // 21-30个：分成3页，每页最多10个
          const refs1 = references.slice(0, 10)
          const refs2 = references.slice(10, 20)
          const refs3 = references.slice(20)
          AISlides.push({ ...template, data: { ...template.data, references: refs1 } })
          AISlides.push({ ...template, data: { ...template.data, references: refs2 }, offset: 10 })
          AISlides.push({ ...template, data: { ...template.data, references: refs3 }, offset: 20 })
        }
        else {
          // 超过30个：每页10个
          let offset = 0
          while (offset < totalCount) {
            const pageRefs = references.slice(offset, offset + 10)
            AISlides.push({
              ...template,
              data: { ...template.data, references: pageRefs },
              offset: offset
            })
            offset += 10
          }
        }
      }
      else AISlides.push(template)
    }

    // 按类型分类模板
    const coverTemplates = templateSlides.filter(slide => slide.type === 'cover')
    const contentsTemplates = templateSlides.filter(slide => slide.type === 'contents')
    const transitionTemplates = templateSlides.filter(slide => slide.type === 'transition')
    const contentTemplates = templateSlides.filter(slide => slide.type === 'content')
    const referenceTemplates = templateSlides.filter(slide => slide.type === 'reference')
    const endTemplates = templateSlides.filter(slide => slide.type === 'end')

    // 初始化过渡页模板（确保风格一致）
    if (!transitionTemplate.value) {
      const _transitionTemplate = transitionTemplates[Math.floor(Math.random() * transitionTemplates.length)]
      transitionTemplate.value = _transitionTemplate
    }

    // 处理每个AI幻灯片
    for (const item of AISlides) {
      // 封面页处理
      if (item.type === 'cover') {
        const coverTemplate = coverTemplates[Math.floor(Math.random() * coverTemplates.length)]
        const elements = coverTemplate.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
          if (el.type !== 'text' && el.type !== 'shape') return el
          if (checkTextType(el, 'title') && item.data.title) {
            return getNewTextElement({ el: el as any, text: item.data.title, maxLine: 1 })
          }
          if (checkTextType(el, 'content') && item.data.text) {
            return getNewTextElement({ el: el as any, text: item.data.text, maxLine: 3 })
          }
          return el
        })
        yield { ...coverTemplate, id: nanoid(10), elements }
      }
      // 目录页处理
      else if (item.type === 'contents') {
        const _contentsTemplates = getUseableTemplates(contentsTemplates, item.data.items.length, 'item')
        const contentsTemplate = _contentsTemplates[Math.floor(Math.random() * _contentsTemplates.length)]

        // 对编号元素进行排序
        const sortedNumberItems = contentsTemplate.elements.filter(el => checkTextType(el, 'itemNumber'))
        const sortedNumberItemIds = sortedNumberItems.sort((a, b) => {
          // 如果元素较多，尝试从内容中提取编号进行排序
          if (sortedNumberItems.length > 6) {
            let aContent = '', bContent = ''
            if (a.type === 'text') aContent = (a as PPTTextElement).content
            if (a.type === 'shape') aContent = (a as PPTShapeElement).text!.content
            if (b.type === 'text') bContent = (b as PPTTextElement).content
            if (b.type === 'shape') bContent = (b as PPTShapeElement).text!.content
            if (aContent && bContent) {
              const aIndex = parseInt(aContent)
              const bIndex = parseInt(bContent)

              return aIndex - bIndex
            }
          }
          // 默认按位置排序（从左到右，从上到下）
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        // 对项目元素进行排序
        const sortedItems = contentsTemplate.elements.filter(el => checkTextType(el, 'item'))
        const sortedItemIds = sortedItems.sort((a, b) => {
          // 如果有编号元素，按编号元素的顺序排序
          if (sortedItems.length > 6) {
            const aItemNumber = sortedNumberItems.find(item => item.groupId === a.groupId)
            const bItemNumber = sortedNumberItems.find(item => item.groupId === b.groupId)

            if (aItemNumber && bItemNumber) {
              let aContent = '', bContent = ''
              if (aItemNumber.type === 'text') aContent = (aItemNumber as PPTTextElement).content
              if (aItemNumber.type === 'shape') aContent = (aItemNumber as PPTShapeElement).text!.content
              if (bItemNumber.type === 'text') bContent = (bItemNumber as PPTTextElement).content
              if (bItemNumber.type === 'shape') bContent = (bItemNumber as PPTShapeElement).text!.content
              if (aContent && bContent) {
                const aIndex = parseInt(aContent)
                const bIndex = parseInt(bContent)

                return aIndex - bIndex
              }
            }
          }
          // 默认按位置排序
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        // 找出最长的文本用于字体大小计算
        const longestText = item.data.items.reduce((longest, current) => current.length > longest.length ? current : longest, '')

        const unusedElIds: string[] = []
        const unusedGroupIds: string[] = []

        const elements = contentsTemplate.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
          if (el.type !== 'text' && el.type !== 'shape') return el

          if (checkTextType(el, 'item')) {
            const index = sortedItemIds.findIndex(id => id === el.id)
            const itemTitle = item.data.items[index]
            if (itemTitle) return getNewTextElement({ el: el as any, text: itemTitle, maxLine: 1, longestText })

            // 标记未使用的元素
            unusedElIds.push(el.id)
            if (el.groupId) unusedGroupIds.push(el.groupId!)
          }

          if (checkTextType(el, 'itemNumber')) {
            const index = sortedNumberItemIds.findIndex(id => id === el.id)
            const offset = item.offset || 0
            return getNewTextElement({ el: el as any, text: index + offset + 1 + '', maxLine: 1, digitPadding: true })
          }
          return el
        }).filter(el => !unusedElIds.includes(el.id) && !(el.groupId && unusedGroupIds.includes(el.groupId)))

        yield { ...contentsTemplate, id: nanoid(10), elements }
      }
      // 过渡页处理
      else if (item.type === 'transition') {
        transitionIndex.value = transitionIndex.value + 1
        const elements = transitionTemplate.value!.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
          if (el.type !== 'text' && el.type !== 'shape') return el
          if (checkTextType(el, 'title') && item.data.title) {
            return getNewTextElement({ el: el as any, text: item.data.title, maxLine: 1 })
          }
          if (checkTextType(el, 'content') && item.data.text) {
            return getNewTextElement({ el: el as any, text: item.data.text, maxLine: 3 })
          }
          if (checkTextType(el, 'partNumber')) {
            return getNewTextElement({ el: el as any, text: transitionIndex.value + '', maxLine: 1, digitPadding: true })
          }
          return el
        })
        yield { ...transitionTemplate.value!, id: nanoid(10), elements }
      }
      else if (item.type === 'content') {
        const items = item.data.items as AnyContentItem[]
        const _contentTemplates = getUseableContentTemplates(contentTemplates, items)
        const contentTemplate = _contentTemplates[Math.floor(Math.random() * _contentTemplates.length)]

        const sortedTitleItemIds = contentTemplate.elements
          .filter(el => checkTextType(el, 'itemTitle'))
          .sort((a, b) => (a.left + a.top * 2) - (b.left + b.top * 2))
          .map(el => el.id)

        const sortedTextItemIds = contentTemplate.elements
          .filter(el => checkTextType(el, 'item'))
          .sort((a, b) => (a.left + a.top * 2) - (b.left + b.top * 2))
          .map(el => el.id)

        let sortedChartItemIds = contentTemplate.elements
          .filter(el => checkChartItemMark(el))
          .sort((a, b) => (a.left + a.top * 2) - (b.left + b.top * 2))
          .map(el => el.id)
        if (sortedChartItemIds.length === 0) {
          sortedChartItemIds = contentTemplate.elements
            .filter(el => el.type === 'chart')
            .sort((a, b) => (a.left + a.top * 2) - (b.left + b.top * 2))
            .map(el => el.id)
        }

        const sortedNumberItemIds = contentTemplate.elements
          .filter(el => checkTextType(el, 'itemNumber'))
          .sort((a, b) => (a.left + a.top * 2) - (b.left + b.top * 2))
          .map(el => el.id)

        const textTitleList: string[] = []
        const textBodyList: string[] = []
        items.forEach(_it => {
          if (isTextItem(_it) || isLegacyTextItem(_it)) {
            if (_it.title) textTitleList.push(_it.title)
            if (_it.text) textBodyList.push(_it.text)
          }
        })
        const longestTitle = textTitleList.reduce((longest, current) => current.length > longest.length ? current : longest, '')
        const longestText = textBodyList.reduce((longest, current) => current.length > longest.length ? current : longest, '')

        const chartItems = items.filter(isChartItem) as AIPPTContentChartItem[]

        const elements = contentTemplate.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)

          if (el.type === 'chart') {
            const idx = sortedChartItemIds.findIndex(id => id === el.id)
            const chartItem = chartItems[idx]
            if (chartItem) return getNewChartElement(el as PPTChartElement, chartItem)
            return el
          }

          if (el.type !== 'text' && el.type !== 'shape') return el

          if (items.length === 1) {
            const only = items[0]
            if ((isTextItem(only) || isLegacyTextItem(only)) && checkTextType(el, 'content') && only.text) {
              return getNewTextElement({ el: el as any, text: only.text, maxLine: 6 })
            }
          }
          else {
            // 处理项目标题
            if (checkTextType(el, 'itemTitle')) {
              const index = sortedTitleItemIds.findIndex(id => id === el.id)
              const contentItem = items[index]
              if (contentItem) {
                if (isTextItem(contentItem) && contentItem.title) {
                  return getNewTextElement({ el: el as any, text: contentItem.title, longestText: longestTitle, maxLine: 1 })
                }
                if (isLegacyTextItem(contentItem) && contentItem.title) {
                  return getNewTextElement({ el: el as any, text: contentItem.title, longestText: longestTitle, maxLine: 1 })
                }
                if (isChartItem(contentItem) && contentItem.title) {
                  return getNewTextElement({ el: el as any, text: contentItem.title, longestText: longestTitle || contentItem.title, maxLine: 1 })
                }
              }
            }

            if (checkTextType(el, 'item')) {
              const index = sortedTextItemIds.findIndex(id => id === el.id)
              const contentItem = items[index]
              if (contentItem) {
                if (isTextItem(contentItem) && contentItem.text) {
                  return getNewTextElement({ el: el as any, text: contentItem.text, longestText, maxLine: 4 })
                }
                if (isLegacyTextItem(contentItem) && contentItem.text) {
                  return getNewTextElement({ el: el as any, text: contentItem.text, longestText, maxLine: 4 })
                }
              }
            }

            if (checkTextType(el, 'itemNumber')) {
              const index = sortedNumberItemIds.findIndex(id => id === el.id)
              const offset = item.offset || 0
              return getNewTextElement({ el: el as any, text: index + offset + 1 + '', maxLine: 1, digitPadding: true })
            }
          }
          // 处理页面标题
          if (checkTextType(el, 'title') && item.data.title) {
            return getNewTextElement({ el: el as any, text: item.data.title, maxLine: 1 })
          }
          return el
        })

        yield { ...contentTemplate, id: nanoid(10), elements }
      }
      else if (item.type === 'reference') {
        const referenceCount = item.data.references.length
        let _referenceTemplates: Slide[] = []

        _referenceTemplates = referenceTemplates.filter(slide => {
          const refNumberCount = slide.elements.filter(el => checkTextType(el, 'referenceNumber')).length
          // 选择引用位置数量在需求数量到10个之间的模板
          return refNumberCount >= referenceCount && refNumberCount <= 10
        })

        // 如果没有完全匹配的模板，使用通用方法选择
        if (_referenceTemplates.length === 0) {
          _referenceTemplates = getUseableTemplates(referenceTemplates, referenceCount, 'referenceNumber')
        }

        const referenceTemplate = _referenceTemplates[Math.floor(Math.random() * _referenceTemplates.length)]

        // 对各种引用元素进行排序（按位置从左到右、从上到下）
        const sortedRefNumberIds = referenceTemplate.elements.filter(el => checkTextType(el, 'referenceNumber')).sort((a, b) => {
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        const sortedPmidIds = referenceTemplate.elements.filter(el => checkTextType(el, 'pmid')).sort((a, b) => {
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        const sortedUrlIds = referenceTemplate.elements.filter(el => checkTextType(el, 'url')).sort((a, b) => {
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        const sortedDoiIds = referenceTemplate.elements.filter(el => checkTextType(el, 'doi')).sort((a, b) => {
          const aIndex = a.left + a.top * 2
          const bIndex = b.left + b.top * 2
          return aIndex - bIndex
        }).map(el => el.id)

        const unusedElIds: string[] = []
        const unusedGroupIds: string[] = []

        const elements = referenceTemplate.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
          if (el.type !== 'text' && el.type !== 'shape') return el

          if (checkTextType(el, 'title') && item.data.title) {
            return getNewTextElement({ el: el as any, text: item.data.title, maxLine: 1 })
          }

          // 处理引用编号
          if (checkTextType(el, 'referenceNumber')) {
            const index = sortedRefNumberIds.findIndex(id => id === el.id)
            const reference = item.data.references[index]
            if (reference) {
              let number = ''
              if (reference.number !== undefined) {
                // 使用自定义编号
                const offset = item.offset || 0
                number = typeof reference.number === 'number'
                  ? (reference.number + offset).toString()
                  : reference.number
              }
              else {
                // 自动生成编号
                const offset = item.offset || 0
                number = (index + offset + 1).toString()
              }
              return getNewTextElement({ el: el as any, text: `[${number}]`, maxLine: 1 })
            }
            else {
              // 没有对应的引用数据，标记为未使用
              unusedElIds.push(el.id)
              if (el.groupId) unusedGroupIds.push(el.groupId)
            }
          }

          // 处理PMID
          if (checkTextType(el, 'pmid')) {
            const index = sortedPmidIds.findIndex(id => id === el.id)
            const reference = item.data.references[index]
            if (reference && reference.pmid) {
              return getNewTextElement({ el: el as any, text: `PMID: ${reference.pmid}`, maxLine: 1 })
            }
            else {
              unusedElIds.push(el.id)
              if (el.groupId) unusedGroupIds.push(el.groupId)
            }
          }

          // 处理URL
          if (checkTextType(el, 'url')) {
            const index = sortedUrlIds.findIndex(id => id === el.id)
            const reference = item.data.references[index]
            if (reference && reference.url) {
              return getNewTextElement({ el: el as any, text: reference.url, maxLine: 2 })
            }
            else {
              unusedElIds.push(el.id)
              if (el.groupId) unusedGroupIds.push(el.groupId)
            }
          }

          // 处理DOI
          if (checkTextType(el, 'doi')) {
            const index = sortedDoiIds.findIndex(id => id === el.id)
            const reference = item.data.references[index]
            if (reference && reference.doi) {
              return getNewTextElement({ el: el as any, text: `DOI: ${reference.doi}`, maxLine: 1 })
            }
            else {
              unusedElIds.push(el.id)
              if (el.groupId) unusedGroupIds.push(el.groupId)
            }
          }

          return el
        }).filter(el => !unusedElIds.includes(el.id) && !(el.groupId && unusedGroupIds.includes(el.groupId)))

        yield { ...referenceTemplate, id: nanoid(10), elements }
      }
      // 结束页处理
      else if (item.type === 'end') {
        const endTemplate = endTemplates[Math.floor(Math.random() * endTemplates.length)]
        const elements = endTemplate.elements.map(el => {
          if (el.type === 'image' && (el as any).imageType && imgPool.value.length) return getNewImgElement(el as PPTImageElement)
          return el
        })
        yield { ...endTemplate, id: nanoid(10), elements }
      }
    }
  }

  /**
   * 生成AI PPT
   * @param templateSlides 模板幻灯片
   * @param _AISlides AI生成的幻灯片数据
   * @param imgs 图片资源
   */
  const AIPPT = (templateSlides: Slide[], _AISlides: AIPPTSlide[], imgs?: ImgPoolItem[]) => {
    // 生成所有幻灯片
    const slides = [...AIPPTGenerator(templateSlides, _AISlides, imgs)]

    // 根据当前是否为空演示文稿决定是替换还是追加
    if (isEmptySlide.value) slidesStore.setSlides(slides)
    else addSlidesFromDataToEnd(slides)
  }

  return {
    presetImgPool,
    AIPPT,
    getMdContent,
    getJSONContent,
    AIPPTGenerator,
  }
}

文件名: src/views/components/element/ChartElement/index.vue
内容: <template>
  <div class="editable-element-chart"
    :class="{ 'lock': elementInfo.lock }"
    :style="{
      top: elementInfo.top + 'px',
      left: elementInfo.left + 'px',
      width: elementInfo.width + 'px',
      height: elementInfo.height + 'px',
    }"
  >
    <div
      class="rotate-wrapper"
      :style="{ transform: `rotate(${elementInfo.rotate}deg)` }"
    >
      <div 
        class="element-content" 
        :style="{
          backgroundColor: elementInfo.fill,
        }"
        v-contextmenu="contextmenus"
        @mousedown="$event => handleSelectElement($event)"
        @touchstart="$event => handleSelectElement($event)"
        @dblclick="openDataEditor()"
      >
        <ElementOutline
          :width="elementInfo.width"
          :height="elementInfo.height"
          :outline="elementInfo.outline"
        />
        <Chart
          :width="elementInfo.width"
          :height="elementInfo.height"
          :type="elementInfo.chartType"
          :data="elementInfo.data"
          :themeColors="elementInfo.themeColors"
          :textColor="elementInfo.textColor"
          :lineColor="elementInfo.lineColor"
          :options="elementInfo.options"
        />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { PPTChartElement } from '@/types/slides'
import type { ContextmenuItem } from '@/components/Contextmenu/types'
import emitter, { EmitterEvents } from '@/utils/emitter'

import ElementOutline from '@/views/components/element/ElementOutline.vue'
import Chart from './Chart.vue'

const props = defineProps<{
  elementInfo: PPTChartElement
  selectElement: (e: MouseEvent | TouchEvent, element: PPTChartElement, canMove?: boolean) => void
  contextmenus: () => ContextmenuItem[] | null
}>()

const handleSelectElement = (e: MouseEvent | TouchEvent) => {
  if (props.elementInfo.lock) return
  e.stopPropagation()

  props.selectElement(e, props.elementInfo)
}

const openDataEditor = () => {
  emitter.emit(EmitterEvents.OPEN_CHART_DATA_EDITOR)
}
</script>

<style lang="scss" scoped>
.editable-element-chart {
  position: absolute;

  &.lock .element-content {
    cursor: default;
  }
}
.rotate-wrapper {
  width: 100%;
  height: 100%;
}
.element-content {
  width: 100%;
  height: 100%;
  overflow: hidden;
  cursor: move;
}
</style>

文件名: src/views/components/element/ChartElement/BaseChartElement.vue
内容: <template>
  <div class="base-element-chart"
    :class="{ 'is-thumbnail': target === 'thumbnail' }"
    :style="{
      top: elementInfo.top + 'px',
      left: elementInfo.left + 'px',
      width: elementInfo.width + 'px',
      height: elementInfo.height + 'px',
    }"
  >
    <div
      class="rotate-wrapper"
      :style="{ transform: `rotate(${elementInfo.rotate}deg)` }"
    >
      <div 
        class="element-content"
        :style="{
          backgroundColor: elementInfo.fill,
        }"
      >
        <ElementOutline
          :width="elementInfo.width"
          :height="elementInfo.height"
          :outline="elementInfo.outline"
        />
        <Chart
          :width="elementInfo.width"
          :height="elementInfo.height"
          :type="elementInfo.chartType"
          :data="elementInfo.data"
          :themeColors="elementInfo.themeColors"
          :textColor="elementInfo.textColor"
          :lineColor="elementInfo.lineColor"
          :options="elementInfo.options"
        />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { PPTChartElement } from '@/types/slides'

import ElementOutline from '@/views/components/element/ElementOutline.vue'
import Chart from './Chart.vue'

defineProps<{
  elementInfo: PPTChartElement
  target?: string
}>()
</script>

<style lang="scss" scoped>
.base-element-chart {
  position: absolute;

  &.is-thumbnail {
    pointer-events: none;
  }
}
.rotate-wrapper {
  width: 100%;
  height: 100%;
}
.element-content {
  width: 100%;
  height: 100%;
}
</style>
文件名: src/views/components/element/ChartElement/Chart.vue
内容: <template>
  <div class="chart" ref="chartRef"></div>
</template>

<script lang="ts" setup>
import { onMounted, useTemplateRef, computed, watch } from 'vue'
import tinycolor from 'tinycolor2'
import type { ChartData, ChartOptions, ChartType } from '@/types/slides'
import { getChartOption } from './chartOption'

import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, ScatterChart, RadarChart } from 'echarts/charts'
import { LegendComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  RadarChart,
  LegendComponent,
  SVGRenderer,
])

const props = defineProps<{
  width: number
  height: number
  type: ChartType
  data: ChartData
  themeColors: string[]
  textColor?: string
  lineColor?: string
  options?: ChartOptions
}>()

let chart: echarts.ECharts | null = null
const chartRef = useTemplateRef<HTMLElement>('chartRef')

const themeColors = computed(() => {
  let colors: string[] = []
  if (props.themeColors.length >= 10) colors = props.themeColors
  else if (props.themeColors.length === 1) colors = tinycolor(props.themeColors[0]).analogous(10).map(color => color.toRgbString())
  else {
    const len = props.themeColors.length
    const supplement = tinycolor(props.themeColors[len - 1]).analogous(10 + 1 - len).map(color => color.toRgbString())
    colors = [...props.themeColors.slice(0, len - 1), ...supplement]
  }
  return colors
})

const updateOption = () => {
  const option = getChartOption({
    type: props.type,
    data: props.data,
    themeColors: themeColors.value,
    textColor: props.textColor,
    lineColor: props.lineColor,
    lineSmooth: props.options?.lineSmooth || false,
    stack: props.options?.stack || false,
  })
  if (option) chart!.setOption(option, true)
}

onMounted(() => {
  chart = echarts.init(chartRef.value, null, { renderer: 'svg' })
  updateOption()

  const resizeListener = () => chart!.resize()
  const resizeObserver = new ResizeObserver(resizeListener)
  resizeObserver.observe(chartRef.value!)
})

watch(() => props.type, updateOption)
watch(() => props.data, updateOption)
watch(() => props.themeColors, updateOption)
watch(() => props.textColor, updateOption)
</script>

<style lang="scss" scoped>
.chart {
  width: 100%;
  height: 100%;
}
</style>
文件名: src/views/components/element/ChartElement/chartOption.ts
内容: import type { ComposeOption } from 'echarts/core'
import type {
  BarSeriesOption,
  LineSeriesOption,
  PieSeriesOption,
  ScatterSeriesOption,
  RadarSeriesOption,
} from 'echarts/charts'
import type { ChartData, ChartType } from '@/types/slides'

type EChartOption = ComposeOption<BarSeriesOption | LineSeriesOption | PieSeriesOption | ScatterSeriesOption | RadarSeriesOption>

export interface ChartOptionPayload {
  type: ChartType
  data: ChartData
  themeColors: string[]
  textColor?: string
  lineColor?: string
  lineSmooth?: boolean
  stack?: boolean
}

export const getChartOption = ({
  type,
  data,
  themeColors,
  textColor,
  lineColor,
  lineSmooth,
  stack,
}: ChartOptionPayload): EChartOption | null => {
  // ... 图表配置生成逻辑
}

---

# 后端 Prompt 模板

## 1. 大纲生成 Prompt

文件名: backend/simpleOutline/prompt.py
用途: 根据用户输入生成PPT大纲的提示词模板

设计说明:
- 当用户输入长度 > 1000 字符时，使用 OUTLINE_INSTRUCTION_NO_SEARCH（不搜索）
- 当用户输入长度 <= 1000 字符时，���用 OUTLINE_INSTRUCTION_WITH_SEARCH（带搜索）
- 原因：长文本通常是用户上传的文档，应基于文档内容生成；短文本可能只是主题，需要搜索补充

内容:
```python
# 阈值配置
USER_INPUT_NUMBER = 1000

# 使用搜索生成大纲
OUTLINE_INSTRUCTION_WITH_SEARCH = """
根据用户的描述或者参考内容生成大纲。按下面的格式生成大纲，仅生成大纲即可，无需多余说明, 可以在使用DocumentSearch进行大纲的细节补充。
输出格式与规则（严格遵守）：
- 使用Markdown标题层级：# 标题 → ## 一级部分 → ### 二级小节 → 列表要点
- 一级部分数量：5个；每个一级部分下含3–4个二级小节
- 每个二级小节列出3–5个要点；要点使用短句，动词开头，不超过18字，不要句号
- 全文不写引言/结语/目录，不写解释性段落，不加任何额外说明
- 术语统一、风格一致，必要时加入可量化指标或示例
- 语言：{language}

输出示例格式如下：
# 标题

## 一级部分
### 二级小节
- 要点1
- 要点2
- 要点3

### 二级小节
- 要点1
- 要点2
- 要点3
- 要点4
- 要点5
"""

# 不使用搜索生成大纲
OUTLINE_INSTRUCTION_NO_SEARCH = """
根据用户的描述或者参考内容生成大纲。按下面的格式生成大纲，仅生成大纲即可，无需多余说明, 尽量根据用户提供的信息生成高质量的符合格式要求的大纲。
输出格式与规则（严格遵守）：
- 使用Markdown标题层级：# 标题 → ## 一级部分 → ### 二级小节 → 列表要点
- 一级部分数量：5个；每个一级部分下含3–4个二级小节
- 每个二级小节列出3–5个要点；要点使用短句，动词开头，不超过18字，不要句号
- 全文不写引言/结语/目录，不写解释性段落，不加任何额外说明
- 术语统一、风格一致，必要时加入可量化指标或示例
- 语言：{language}

输出示例格式如下：
# 标题

## 一级部分
### 二级小节
- 要点1
- 要点2
- 要点3

### 二级小节
- 要点1
- 要点2
- 要点3
- 要点4
- 要点5
"""
```

---

## 2. PPT 内容生成 Prompt

文件名: backend/slide_agent/slide_agent/sub_agents/ppt_writer/prompt.py
用途: 根据大纲生成各类型PPT页面内容的提示词模板

### 2.1 前缀 Prompt（通用约束）

```python
# 不带图片，不搜索的基础前缀
PREFIX_PAGE_PROMPT = """
# 通用约束：
1. 你将收到一段 单行 JSON，键名固定为 type 和 data（如有）。
2. 保持原有结构与键名尽量不变：**不得修改已有字段的名称**；**不得删除既有字段**。除非另有"内容页特例"说明，不得新增字段或改变数组长度。
3. 统一输出为{language}；专有名词可带英文小写缩写。
4. 文风：简洁、商务演示友好，避免夸张或无法证实的数字。
5. 严禁输出除 JSON 外的任何内容（包括说明、Markdown、代码块围栏）。
"""

# 带搜索图片的前缀
PREFIX_PAGE_PROMPT_WITH_IMAGE = """
# 通用约束：
1. 你将收到一段 单行 JSON，键名固定为 type 和 data（如有）。
2. 保持原有结构与键名尽量不变：**不得修改已有字段的名称**；**不得删除既有字段**。除非另有"内容页特例"说明，不得新增字段或改变数组长度。
3. 统一输出为{language}；专有名词可带英文小写缩写。
4. 文风：简洁、商务演示友好，避免夸张或无法证实的数字。
5. 严禁输出除 JSON 外的任何内容（包括说明、Markdown、代码块围栏）。

# 重要：图片搜索工具使用
你必须为每个页面搜索合适的配图！使用 SearchImage 工具搜索相关图片，然后将图片信息添加到返回的 JSON 中。

# 图片搜索规则：
- 封面页：搜索与主题相关的商务、抽象或科技类图片，关键词如 "business abstract"、"technology background"
- 内容页：根据内容主题搜索相关图片，如技术类内容搜索 "technology"、"innovation"
- 过渡页：搜索抽象或商务类图片，关键词如 "abstract background"、"business concept"
- 结束页：搜索简洁的商务或抽象图片，关键词如 "minimal business"、"clean abstract"

# 图片数据格式：
在 JSON 中添加 images 字段，包含搜索到的图片信息：
{
  "type": "cover",
  "data": { ... },
  "images": [
    {
      "id": "图片ID",
      "src": "图片URL",
      "alt": "图片描述"
    }
  ]
}
"""

# 带搜索的前缀
PREFIX_PAGE_PROMPT_WITH_SEARCH = """
# 通用约束：
1. 你将收到一段 单行 JSON，键名固定为 type 和 data（如有）。
2. 保持原有结构与键名尽量不变：**不得修改已有字段的名称**；**不得删除既有字段**。除非另有"内容页特例"说明，不得新增字段或改变数组长度。
3. 必须使用搜索工具{tool_names}进行搜索，然后完成内容扩充。
4. 统一输出为{language}；专有名词可带英文小写缩写。
5. 文风：简洁、商务演示友好，避免夸张或无法证实的数字。
6. 严禁输出除 JSON 外的任何内容（包括说明、Markdown、代码块围栏）。
"""
```

### 2.2 各页面类型 Prompt

```python
# 封面页
COVER_PAGE_PROMPT = """
封面页（type: "cover"）
你是PPT封面文案优化器,使用的语言是{language}。保持 title 原样，不改；重写 data.text 为 18～32 字的副标题，强调主题价值与适用场景，避免标点堆叠与口号化。
{input_slide_data}
"""

# 目录页
CONTENTS_PAGE_PROMPT = """
目录页（type: "contents"）
你是PPT目录优化器,使用的语言是{language}。仅在需要时对 data.items[*] 的短语做轻微润色（可名词化或动宾化，使其更像目录条目），不得改变顺序与数量；每项不超过14个字；不添加或删除项目。
{input_slide_data}
"""

# 过渡页
TRANSITION_PAGE_PROMPT = """
过渡页（type: "transition"）
你是章节过渡文案撰写者,使用的语言是{language}。保持 data.title 原样不改；重写 data.text 为2～3句过渡语，每句12～24字，说明本章为何重要、将回答什么问题、读者可获得的收获。避免夸张或口号化表达。
{input_slide_data}
"""

# 内容页（带图表支持）
CONTENT_PAGE_PROMPT = """
内容页（type: "content"）
你是技术与产业结合的内容扩写器，使用的语言是{language}。保持 data.title 与各 items[*].title 原样不改；对 items[*].text 逐项扩写为 2～3 句、合计 60～120 字，采用"是什么→为何重要→如何落地/示例"的逻辑；不得删除已有 items；避免编造精确数据或过度承诺。

# 图表（严格防止编造）：
仅当本页主题涉及趋势/对比/占比/量化指标，且通过检索获得"可引用的权威来源数据"时，才允许在 data.items **末尾**新增 1 个 `{"kind":"chart", ...}` 项；否则**不要**新增图表。
- **来源要求**：使用的数据**必须来自工具返回的原文内容**。
- **数据要求**：所有数值必须与来源一致；不得估算/外推/上色演示。
- **类型选择**：时间趋势用 line，类目对比用 bar，占比用 pie。
- **找不到即拒绝**：若未找到可引用数据，保持原结构不变，并在本页末尾追加一句固定话术："未检索到可引用的数据，故不新增图表。"
- **字段限制**：不得新增chart 以外的其他字段。

# 输出结构（不得变更）：
- 原始结构（type、data）保持不变；
- 你可以在 data.items 中**最多新增 1 个**图表 item（不替换已存在文本 item）；
- 图表 item 的 JSON 结构**扩展为**（以下附加字段为必填）：
{
  "kind": "chart",                                    # 必填，固定字符串 "chart"
  "title": "图表标题",                                # 建议 ≤ 16 字，不要添加来源信息
  "text": "图表的描述信息",                             # 建议 ≤ 40 字，不要添加来源信息
  "chartType": "line" | "bar" | "pie" | "column" | "ring" | "area" | "radar",
  "labels": ["类目或时间刻度", ...],                    # 4~8 个，均为字符串
  "series": [                                           # 1~2 组数据
    { "name": "系列名", "data": [数值, ...] }         # data 长度与 labels 一致，均为数字
  ],
  "options": {
      "xAxis": { "name": "xxx" },
      "yAxis": { "name": "xxx" }
  },
}

# 检索与证据：
- 先检索再写作。
- 图表以外的内容若涉及定量描述，需加"区间/范围/定性词"，避免精确值。

# 何时应当新增图表：
- 仅当存在可视化价值且**找到了**可引用数据；否则不要新增图表。

# 原始结构
{input_slide_data}
"""

# 结束页
END_PAGE_PROMPT = """
结束页（type: "end"）
你是PPT结束页生成器,使用的语言是{language}。若无 data 字段则原样返回；若存在 data.text，则改写为10～16字的感谢语，语气真诚克制，可包含"感谢观看/欢迎交流"等，不添加多余字段。
{input_slide_data}
"""

# 页面类型到 Prompt 的映射
prompt_mapper = {
    "cover": COVER_PAGE_PROMPT,
    "contents": CONTENTS_PAGE_PROMPT,
    "transition": TRANSITION_PAGE_PROMPT,
    "content": CONTENT_PAGE_PROMPT,
    "end": END_PAGE_PROMPT,
}
```

---

## 3. PPT 模板打标 Prompt

文件名: template/qwen_vl_2dgrounding.py
用途: 使用视觉语言模型（Qwen-VL）对PPT模板进行自动打标，识别页面类型和元素角色

```python
PAGE_TYPES = [
    "cover",              # 封面：大标题 + 副标题/点缀
    "title-content",      # 标题 + 正文段落或要点
    "two-column",         # 左右双栏
    "image-caption",      # 大图 + 配图说明
    "section",            # 章节页
    "thankyou",           # 致谢/结束
    "list",               # 列表/要点
    "unknown"
]

ROLE_TEXT = ["title", "subtitle", "content", "caption"]
ROLE_NON_TEXT = ["image", "chart", "table", "logo", "decorative", "shape"]

PROMPT_TEMPLATE = """你是一个 PPT 版式与视觉元素分析器。请只输出 JSON，绝不输出解释或多余文字。
坐标系：使用相对坐标 0~1000。bbox_2d = [x1,y1,x2,y2]，x1<x2,y1<y2。

目标：识别该幻灯片的页面类型与各元素的角色与位置，用于把"普通 JSON"转换为"可复用 PPT 模版 JSON"。

页面类型（page_type）仅能取以下枚举之一：
{page_types}

元素角色（role）仅能取以下枚举之一：
- 文本：{role_text}
- 非文本：{role_non_text}

输出 JSON 的**唯一**合法结构如下（严格遵守键名与大小写）：
{
  "page_type": "cover|title-content|two-column|image-caption|section|thankyou|list|unknown",
  "elements": [
    {
      "role": "title|subtitle|content|caption|image|chart|table|logo|decorative|shape",
      "bbox_2d": [x1,y1,x2,y2]
    },
    ...
  ]]
}

约束与规则：
- 只检测版面中"信息承载"或"版式结构"的元素，背景花纹可标为 decorative 或忽略。
- 文本框只使用 role: title / subtitle / content / caption 四种之一。
- 如果是封面，通常有 title 与可选 subtitle；章节页可用 page_type=section。
- 不确定时使用最保守的 page_type=unknown，role=content。
- 仅输出一个 JSON，对齐示例结构并且是合法 JSON（不要 markdown 围栏）。
"""
```

---

## 4. Prompt 动态生成逻辑

### 4.1 大纲生成 Agent

文件名: backend/simpleOutline/agent.py

```python
def _get_dynamic_instruction(self, ctx: InvocationContext) -> str:
    """动态整合所有研究发现并生成指令"""
    metadata = ctx.state.get("metadata", {})
    language = metadata.get("language", "chinese")  # 默认中文

    user_input = self._get_user_content_from_context(ctx)
    # 根据不同的的输入长度，形成不同的prompt
    if len(user_input) > prompt.USER_INPUT_NUMBER:
        prompt_instruction = prompt.OUTLINE_INSTRUCTION_NO_SEARCH.format(language=language)
    else:
        prompt_instruction = prompt.OUTLINE_INSTRUCTION_WITH_SEARCH.format(language=language)
    return prompt_instruction
```

### 4.2 PPT 写作 Agent

文件名: backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py

```python
def _get_dynamic_instruction(self, ctx: InvocationContext) -> str:
    """动态整合所有研究发现并生成指令"""
    current_slide_index: int = ctx.state.get("current_slide_index", 0)
    outline_json: list = ctx.state.get("outline_json")
    current_slide_schema = outline_json[current_slide_index]
    metadata = ctx.state.get("metadata", {})
    search_engine = metadata.get("search_engine", [])
    language = metadata.get("language", "chinese")

    # 根据不同的搜索工具，使用不同的prefix的prompt
    if not search_engine:
        prefix_prompt = prompt.PREFIX_PAGE_PROMPT.format(language=language)
    elif search_engine == ["SearchImage"]:
        prefix_prompt = prompt.PREFIX_PAGE_PROMPT_WITH_IMAGE.format(language=language)
    else:
        prefix_prompt = prompt.PREFIX_PAGE_PROMPT_WITH_SEARCH.format(tool_names=search_engine, language=language)

    # 根据不同的类型，形成不同的prompt
    current_slide_type = current_slide_schema.get("type")
    slide_prompt = prompt.prompt_mapper[current_slide_type]
    current_slide_schema_json = json.dumps(current_slide_schema, ensure_ascii=False)
    prompt_instruction = prefix_prompt + slide_prompt.format(input_slide_data=current_slide_schema_json, language=language)

    return prompt_instruction
```

---

## 5. Prompt 系统架构总结

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  大纲生成阶段 (simpleOutline)                                │
│  ├─ 输入长度 > 1000: OUTLINE_INSTRUCTION_NO_SEARCH          │
│  └─ 输入长度 ≤ 1000: OUTLINE_INSTRUCTION_WITH_SEARCH        │
└─────────────────────────────────────────────────────────────┘
    │
    ▼ Markdown 大纲
    │
┌─────────────────────────────────────────────────────────────┐
│  PPT 内容生成阶段 (ppt_writer)                               │
│  ├─ 前缀选择:                                                │
│  │   ├─ 无搜索: PREFIX_PAGE_PROMPT                          │
│  │   ├─ 图片搜索: PREFIX_PAGE_PROMPT_WITH_IMAGE             │
│  │   └─ 文档搜索: PREFIX_PAGE_PROMPT_WITH_SEARCH            │
│  └─ 页面类型 Prompt:                                         │
│      ├─ cover → COVER_PAGE_PROMPT                           │
│      ├─ contents → CONTENTS_PAGE_PROMPT                     │
│      ├─ transition → TRANSITION_PAGE_PROMPT                 │
│      ├─ content → CONTENT_PAGE_PROMPT (支持图表)            │
│      └─ end → END_PAGE_PROMPT                               │
└─────────────────────────────────────────────────────────────┘
    │
    ▼ JSON 幻灯片数据
    │
┌─────────────────────────────────────────────────────────────┐
│  前端渲染阶段 (useAIPPT.ts)                                  │
│  ├─ 模板匹配: getUseableContentTemplates()                  │
│  ├─ 图表渲染: getNewChartElement() → ChartElement           │
│  └─ 文本渲染: getNewTextElement()                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 环境变量配置

文件名: env_template.txt

```bash
# 大纲生成主模型
OUTLINE_TYPE=openai
OUTLINE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OUTLINE_API_KEY=sk-your_outline_api_key
OUTLINE_MODEL=qwen-turbo-latest

# 幻灯片内容生成模型
PPT_WRITER_TYPE=openai
PPT_WRITER_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PPT_WRITER_API_KEY=sk-your_writer_api_key
PPT_WRITER_MODEL=qwen-turbo-latest

# 幻灯片内容校对模型
PPT_CHECKER_TYPE=openai
PPT_CHECKER_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PPT_CHECKER_API_KEY=sk-your_checker_api_key
PPT_CHECKER_MODEL=qwen-turbo-latest

# 是否启用图表生成（需要模型能力较强）
USE_CHART=true
```
