# AI2PPT 前端统一技术文档（已归档）

> ⚠️ 已归档：本文件为历史 AI2PPT/早期 TeachDo 前端审计汇总，仅供对照与追溯。TeachDo 当前维护版前端指南见：`doc/dev/FRONTEND_GUIDE.md`。
>
> **文档版本**: 2.0.0
> **最后更新**: 2025-11-30
> **说明**: 本文档整合了前端审计、架构、组件、Hooks、类型及重构相关材料；当前仓库已按 `docs/`（用户文档）+ `doc/`（开发文档）双目录维护，本文仅作历史参考。
>
> 相关文档分工：
> - 前端 API 封装清单（services 层）：`doc/dev/FRONTEND_API_CALLS.md`
> - 后端 API 契约（以实现为准）：`doc/backend/backend_api_reference.md`

---

## 目录

1.  [执行摘要](#1-执行摘要)
2.  [技术栈与项目结构](#2-技术栈与项目结构)
3.  [路由系统](#3-路由系统)
4.  [状态管理 (Pinia)](#4-状态管理-pinia)
5.  [API 集成](#5-api-集成)
6.  [核心功能清单](#6-核心功能清单)
7.  [AI 生成引擎分析](#7-ai-生成引擎分析)
8.  [组件清单](#8-组件清单)
9.  [Hooks 功能模块](#9-hooks-功能模块)
10. [类型系统](#10-类型系统)
11. [重构建议与技术债务](#11-重构建议与技术债务)

---

## 1. 执行摘要

本文档是对 AI2PPT 现有前端的全面分析。项目基于 **Vue 3.5 + TypeScript 5.3 + Vite 5.3**，使用 **Pinia** 状态管理，集成了 **ProseMirror** 富文本编辑器和 **pptxgenjs** PPT生成能力。

### 1.1 关键指标

- **技术栈**: Vue 3 Composition API + TypeScript (严格模式)
- **代码规模**: 49,000+ 行代码, 50 组件, 32 Hooks
- **主要页面**: 5个
- **API集成**: 7个主要端点, SSE流式响应
- **状态管理**: 6个 Pinia Stores

### 1.2 核心发现

✅ **优势**:
- 现代化技术栈，架构清晰，模块化良好
- 完整的 TypeScript 类型系统覆盖
- 丰富的编辑器功能及 AI 生成能力
- 已有防抖节流等性能优化

⚠️ **风险与待改进**:
- 核心 Hooks (`useAIPPT.ts`) 过于复杂 (1043行)，需拆分
- 大纲编辑器等核心组件与业务逻辑耦合度高
- 缺少单元测试覆盖，重构风险高
- 硬编码配置分散，不利于维护

---

## 2. 技术栈与项目结构

### 2.1 技术栈

| 技术 | 版本 | 说明 |
|---|---|---|
| Vue | ^3.5.17 | Composition API |
| TypeScript | ~5.3.0 | 严格模式 |
| Vite | ^5.3.5 | 构建工具 |
| Pinia | ^3.0.2 | 状态管理 |
| Vue Router | ^4.5.1 | 路由管理 |
| **ProseMirror** | - | 富文本编辑器 |
| **pptxgenjs** | ^3.12.0 | PPT生成 |
| **ECharts** | ^5.5.1 | 图表 |
| **vuedraggable** | ^4.1.0 | 拖拽 |
| **lodash** | ^4.17.21 | 工具函数库 |

### 2.2 项目结构

```
frontend/src/
├── assets/         # 静态资源
├── components/     # 通用组件 (50个)
├── configs/        # 配置文件
├── plugins/        # Vue 插件
├── hooks/          # 业务Hooks (32个)
├── router/         # 路由配置
├── services/       # API服务层
├── store/          # Pinia Stores (6个)
├── types/          # TS类型定义
├── utils/          # 工具函数
├── views/          # 页面视图
│   ├── Home.vue      # 首页
│   ├── Outline/    # 大纲页
│   ├── Editor/     # 编辑器页
│   ├── Mobile/     # 移动端视图
├── App.vue
└── main.ts
```

---

## 3. 路由系统

| Path | Name | 关联组件 |
| --- | --- | --- |
| `/` | `Home` | `@/views/Home.vue` |
| `/about` | `About` | `@/views/About.vue` |
| `/outline` | `Outline` | `@/views/Outline/index.vue` |
| `/ppt` | `PPT` | `@/views/PPT/index.vue` |
| `/editor` | `Editor` | `@/views/Editor/index.vue` |
| `/app/:id?` | `APP` | `@/views/APP/index.vue` |

**核心流程**: `Home` → `Outline` → `PPT` → `Editor`（`/app/:id?` 为实验入口，不走主流程）

---

## 4. 状态管理 (Pinia)

项目共包含 5 个 Pinia Store，职责划分清晰：

| Store | 文件 | 职责 |
|---|---|---|
| **mainStore** | store/main.ts | 作为应用程序的主状态管理中心，负责管理UI交互、编辑器状态和全局配置。它包含了诸如当前选中的元素、画布缩放/拖动状态、工具栏状态、剪贴板功能（格式刷）、对话框状态以及各种面板（搜索、备注、符号等）的显示/隐藏逻辑。此外，它还管理与AI PPT生成相关的状态。 |
| **slidesStore** | store/slides.ts | 管理幻灯片的核心数据结构。这包括整个演示文稿的标题、主题（颜色、字体等）、所有幻灯片页面的集合（`slides` 数组）、当前页面的索引以及视口尺寸和比例。它还负责处理幻灯片和幻灯片内元素的增、删、改、查操作，以及管理模板和动画。 |
| **snapshotStore** | store/snapshot.ts | 实现撤销/重做功能。它通过 IndexedDB 存储幻灯片状态的快照。它管理一个快照指针，并提供 `undo` 和 `redo` 操作来恢复到历史状态。它还负责在添加新快照时管理快照的数量限制和清理旧的快照。 |
| **keyboardStore** | store/keyboard.ts | 管理键盘按键的状态，特别是 `ctrl`、`shift` 和 `space` 键。它跟踪这些键是否被按下，并提供一个 getter 来检查 `ctrl` 或 `shift` 键是否处于活动状态。这对于实现快捷键和组合键功能至关重要。 |
| **screenStore** | store/screen.ts | 管理演示文稿的放映模式。它只包含一个状态 `screening`，用于切换和跟踪应用程序是否处于全屏放映状态。 |

---

## 5. API 集成

### 5.1 API 端点

| 端点 | 方法 | 功能 | 响应 |
|---|---|---|---|
| `/api/tools/aippt_outline_unified` | POST | 统一大纲生成（主题必填，可选上传文件） | SSE |
| `/api/tools/aippt` | POST | 生成 PPT 内容 | SSE |
| `/api/templates` | GET | 获取模板列表 | JSON |
| `/api/data/{filename}` | GET | 获取模板 JSON/封面等静态资源 | File |
| `/api/proxy?url=...` | GET | 代理外链资源（导出用） | Stream |

备注：
- 兼容/legacy：`/api/tools/aippt_outline`、`/api/tools/aippt_outline_from_file`（当前前端路由页面未使用）

### 5.2 SSE 流式处理

通过 `fetch` API 获取流式响应，并使用 `TextDecoder` 实时解析服务端发送的事件数据，实现内容逐段生成的效果。

---

## 6. 核心功能清单

### 6.1 大纲页 (Outline)
- **输入**: 支持文本主题、文档上传（PDF/DOCX/MD）、语言和模型选择。
- **AI生成**: SSE流式生成大纲，支持中断。
- **编辑器**: 树形结构展示，支持拖拽排序、增删改节点、折叠展开。

### 6.2 模板选择页 (PPT)
- **展示**: 响应式网格布局展示模板卡片。
- **选项**: 提供“根据上传文件生成”、“使用网络搜索”等额外选项。
- **生成**: SSE流式接收幻灯片数据，实时生成并自动跳转至编辑器。

### 6.3 编辑器页 (Editor)
- **布局**: 经典的左中右布局（缩略图、画布、工具栏）。
- **画布**: 支持缩放、拖拽、框选、对齐线等辅助功能。
- **元素编辑**: 支持文本、图片、形状、图表等9种元素的完全编辑。
- **工具栏**: 根据选中元素动态显示不同样式面板（文本、形状、动画等）。
- **导出**: 支持导出为 PPTX, PNG, JPEG, JSON 格式。

### 6.4 大纲页面 (Outline) 流程（统一接口：主题必填 + 可选文件）

- **页面路径**: `/outline` (`@/views/Outline/index.vue`)
- **统一职责**:
  - 统一使用 `/tools/aippt_outline_unified` 在大纲页实时流式展示生成过程（主题必填；如有上传文件则会结合文档内容生成大纲）。
  - 生成完成后，提供编辑能力，并将最终大纲传递给 PPT 生成页。
- **入口约定**:
  - `Home` 负责收集输入并跳转：

    ```ts
    // 如有文件：先写入 mainStore
    mainStore.setUploadedFile(selectedFile.value)

    router.push({
      path: '/outline',
      query: {
        topic: topic.value.trim(), // 必填
        hasFile: selectedFile.value ? 'true' : undefined,
        fileName: selectedFile.value ? selectedFile.value.name : undefined,
        language: language.value,
        model: model.value,
      },
    })
    ```

- **Outline 页内部逻辑**:

  - 读取路由参数并调用 unified 接口：

    ```ts
    const language = ref((route.query.language as string) || '中文')
    const model = ref((route.query.model as string) || 'GLM-4.5-Air')
    const topic = ref((route.query.topic as string) || '')
    const hasFile = ref(route.query.hasFile === 'true')
    ```

  - 页面挂载时：

    ```ts
    onMounted(async () => {
      if (!topic.value.trim()) {
        message.warning('请先输入主题')
        router.push('/')
        return
      }

      await generateOutlineUnified()
    })
    ```

  - unified 模式 `generateOutlineUnified`：

    ```ts
    const file = mainStore.uploadedFile
    const response = await api.AIPPT_Outline_Unified({
      content: topic.value.trim(),
      file: file || undefined,
      language: language.value,
      userId: 'default_user',
    })

    await streamFromResponse(response)
    mainStore.setOutlineFromFile(!!file)
    ```

- **状态与后续流程**:
  - `mainStore.isOutlineFromFile`：
    - 主题模式：`false`
    - 文档模式：生成成功后置 `true`，PPT 页据此展示「根据上传文件生成 PPT」等选项。
  - 跳转到 PPT 页时，仍沿用原有约定：

    ```ts
    router.push({
      name: 'PPT',
      query: {
        outline: outline.value,
        language: language.value,
        model: model.value,
      },
    })
    ```

> 扩展建议：如果将来需要增加「从知识库检索结果生成大纲」或「从历史文档生成大纲」，可以沿用当前模式：在入口页只做参数收集与导航，把所有流式生成和编辑逻辑统一放在 `/outline`，避免跨页面复制流式实现。

---

## 7. AI 生成引擎分析

AI 生成的核心逻辑位于 `hooks/useAIPPT.ts`，这是一个高达1043行的复杂 Hook，是重构的最高风险点。

- **核心算法**: 使用 `Generator` 函数 `AIPPTGenerator` 逐页生成幻灯片。
- **模板匹配**: 通过 `getUseableContentTemplates` 等函数，根据AI返回内容的元素数量和类型（文本、图表、图片）动态选择最合适的模板。
- **自适应字体**: `getAdaptedFontsize` 算法通过二分查找，在给定区域内为文本找到最合适的字体大小。
- **图片处理**: `getNewImgElement` 负责管理图片池和图片裁剪。
- **分页逻辑**: 对目录、内容、引用页，当内容过多时自动进行分页处理。

---

## 8. 组件清单

### 8.1 基础组件
- **表单**: `Button`, `Input`, `TextArea`, `NumberInput`, `Checkbox`, `RadioButton`, `Select`, `Slider`, `Switch` 等。
- **布局**: `Modal`, `Drawer`, `Popover`, `Tabs`, `Divider`。
- **颜色**: `ColorPicker` (包含透明度、色相、饱和度、预设色板、吸管等完整功能)。

### 8.2 复杂业务组件
- **`Contextmenu`**: 右键菜单组件，支持动态配置、子菜单和自动定位。
- **`LaTeXEditor`**: LaTeX 公式编辑器，支持实时预览和符号库。
- **`OutlineEditor`**: 大纲编辑器，支持4级层级、右键操作和内联编辑。

### 8.3 Editor 页面核心组件
- **`EditableElement`**: 可编辑元素的集合，是画布的核心。为9种不同类型的元素（`ImageElement`, `TextElement`, `ShapeElement` 等）提供统一的编辑框和操作逻辑。
- **`MultiSelectOperate`**: 多选操作组件，负责处理多个元素的统一缩放、旋转、对齐和组合。
- **`Toolbar`**: 右侧工具栏，根据当前编辑上下文（如选中元素类型）动态切换显示不同的面板（`ElementStylePanel`, `ElementAnimationPanel` 等）。

---

## 9. Hooks 功能模块

项目包含 32 个 Composition API Hooks，是业务逻辑的核心。

### 9.1 核心业务 Hooks
| Hook | 行数 | 功能 |
|---|---|---|
| **`useAIPPT`** | 1043 | **AI生成PPT核心**，包含模板匹配、自适应字体、分页等复杂逻辑。 |
| **`useExport`** | 971 | **导出功能**，处理PPTX、图片、JSON的导出，包含跨域图片处理。 |
| **`useImport`** | 782 | **导入PPTX功能**，解析pptx文件并转换为内部数据结构。 |
| **`useHistorySnapshot`** | 27 | **撤销/重做**，基于IndexedDB和防抖/节流实现。 |

### 9.2 元素操作 Hooks
- `useCreateElement`: 创建9种不同类型的画布元素。
- `useDeleteElement`: 删除元素。
- `useAlignActiveElement`: 对齐选中元素。
- `useOrderElement`: 调整元素层级。
- `useCombineElement`: 组合/取消组合元素。
...以及其他10余个用于元素变换（拖拽、缩放、旋转）和选择的 Hooks。

### 9.3 编辑功能 Hooks
- `useGlobalHotkey`: 注册全局快捷键（如 Ctrl+C/V/Z）。
- `useCopyAndPasteElement`: 实现元素的复制粘贴。
- `useSearch`: 实现查找与替换功能。

### 9.4 大纲流式生成相关 Hooks

#### `useOutlineStream`（新增）

- **文件**: `frontend/src/hooks/useOutlineStream.ts`
- **职责**: 把后端返回的 `Response` 流式读取成前端大纲字符串，统一处理「主题模式」和「文档模式」的大纲生成。
- **签名**:

  ```ts
  interface UseOutlineStreamOptions {
    outline: Ref<string>
    outlineRef?: Ref<HTMLElement | undefined>
  }

  const { streamFromResponse } = useOutlineStream(options)
  ```

- **行为细节**:
  - 通过 `response.body.getReader()` + `TextDecoder` 按 chunk 读取后端 `text/plain` 流。
  - 将流式文本持续累加到 `outline.value`。
  - 如果传入了 `outlineRef`，每次更新后自动滚动父容器到底部，确保用户总是看到最新一行。
  - 流结束后统一做后处理：
    - 使用 `useAIPPT.getMdContent` 提取 ```markdown``` 代码块中的正文内容。
    - 清理 `<!-- ... -->` HTML 注释与 `<think>...</think>` 思维链痕迹，保证大纲内容干净。

> 设计原则：大纲流式读取是一个可以在多个页面复用的纯 UI 行为，抽成独立 Hook 既简化了 `Outline` 页，也避免了在 `Home` / `Outline` 中复制同样的 Reader 逻辑（DRY）。

---

## 10. 类型系统

类型定义是本项目的优势之一，提供了良好的代码提示和类型安全。

### 10.1 `PPTElement` - 元素类型体系
所有画布上的元素都继承自 `PPTBaseElement`，并联合为 `PPTElement` 类型。
```typescript
// 联合类型 (9种元素)
type PPTElement = 
  | PPTTextElement
  | PPTImageElement
  | PPTShapeElement
  // ... 其他元素

// 基类定义
interface PPTBaseElement {
  id: string;
  left: number;
  top: number;
  width: number;
  height: number;
  rotate: number;
  lock?: boolean;
  groupId?: string;
}
```
每个具体元素类型（如 `PPTImageElement`）都在基类上扩展自己的特有属性（如 `filters`, `clip`）。

### 10.2 `AIPPTSlide` - AI 数据结构
这是后端AI服务返回的数据结构，与前端的 `Slide` 类型相对应。
```typescript
// AI返回的幻灯片内容项
type AIPPTContentItem = 
  | { kind: 'text', title: string, text: string[] }
  | { kind: 'chart', chartType: string, data: any }
  | { kind: 'image', src: string };

// AI返回的幻灯片结构
type AIPPTSlide = 
  | { type: 'cover', title: string, subtitle?: string }
  | { type: 'content', title: string, items: AIPPTContentItem[] }
  // ... 其他页面类型
```
项目巧妙地使用了 `kind` 字段作为 **判别联合 (Discriminated Union)**，并提供了 `isChartItem` 等类型守卫函数，大大增强了处理AI数据时的类型安全性。
