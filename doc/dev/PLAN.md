# TeachDo 开发计划（当前）

> 更新：2026-02-16  
> 历史迁移计划（ai2ppt → TeachDo，阶段 A–G）已归档：`doc/dev/history/PLAN_AI2PPT_TO_TEACHDO_2026-02.md`

## 0. 文档说明
- 本文件作为 TeachDo 后续开发计划（Roadmap）的唯一入口文件，面向“接下来做什么 / 为什么 / 验收标准（DoD）”。
- 约定：
1. 每次更新请同步「更新日期」并记录必要的 commit/PR。
2. 对外发布前的发布清理/工程校验清单：参考历史计划的“阶段 G”。
3. Docker/部署（历史阶段 H）：确认“功能开发稳定后”再启动，不阻塞当前迭代。

## 1. 当前状态（简述）
- 迁移链路已可用：Outline → PPT 生成 → 预览 → 编辑器 → 导出闭环已打通（阶段 A–G 已完成并归档）。
- 当前工作重点从“迁移实施”切换为“前端产品化/架构收敛 + 连贯性体验打磨 + 性能与可维护性提升”。

## 2. 后续里程碑（建议）

### 阶段 I：前端架构收敛与稳定性（P0）
目标：先解决结构性风险与边界问题，避免后续优化在“脆弱地基”上叠加。

- [ ] I1. 持久化分层（LocalStorage 轻量化 + 大对象 IndexedDB）
  - 背景：当前 `appStore` 将整个 state `JSON.stringify` 写入 localStorage，且无写入失败兜底；`editorDocument.slides` 可能巨大，容易触发配额/卡顿/异常。
  - 方案：
    1. LocalStorage 仅持久化“轻量元数据”（currentCourseId/currentUnitId、theme、language、课程与单元的轻量字段）。
    2. `editorDocument`、大纲/生成产物等“大文本/大数组”统一走 IndexedDB（可复用 editor-runtime Dexie 或单独建表），并提供迁移与降级策略。
  - DoD：
    1. 无论 slides 体量多大，刷新/切换路由不出现 localStorage 配额错误与明显卡顿。
    2. “预览回显/编辑器回显”稳定（支持加载失败降级到 `presentation`）。

- [ ] I2. 依赖边界与首屏瘦身（避免 editor-runtime 侵入工作台首屏）
  - 方案：
    1. 工作台 Tab（Outline/Lesson/PPT）改为懒加载（async component 或子路由 code-splitting）。
    2. PPT 预览页避免静态引用 editor-runtime 的重依赖（按需加载缩略图/渲染器）。
  - DoD：
    1. 首屏（课程选择/工作台）不加载 editor-runtime 相关大 chunk。
    2. 进入 `/ppt/editor` 时再加载编辑器相关资源。

- [ ] I3. Service 层收敛（aiService 拆分与去重）
  - 方案：按领域拆分 `ppt/outline/kb`，统一错误模型（超时/取消/后端不可用提示），清理“已不再使用但仍保留的旧实现”。
  - DoD：同一类错误在所有页面表现一致（文案、toast、重试策略一致）。

- [ ] I4. PPTView 组件拆分（可维护、可测试）
  - 方案：拆为“模板选择/高级选项/生成状态/预览渲染/入库”等子组件 + composable（如 `usePptGeneration`）。
  - DoD：核心生成逻辑可被单测覆盖（SSE 解析与生成状态机至少覆盖关键分支）。

### 阶段 J：连贯性设计（Coherence）/无缝用户体验（Seamless UX）（P0）
目标：解决“割裂感”，让用户从工作台到编辑器、从生成到编辑到导出形成顺滑、可预期的体验闭环。

> 本阶段按 4 个维度审查并落地：一致性（视觉/行为/概念）→ 用户路径（User Flow）→ 交互设计（IxD）→ 信息架构（IA）。  
> 参考规范来源：`ui-ux-pro-max`（可访问性、交互、性能、布局等检查清单）。

#### J0. 审查范围（页面/入口）
1. 课程选择页（`/`）
2. 工作台（`/course/:courseId[/unit/:unitId/:tab]`）：Outline / Lesson / PPT
3. 课程级页面：KB / Assistant
4. 独立编辑器（`/course/:courseId/unit/:unitId/ppt/editor`）
5. 通用组件：Sidebar、Header Tabs、Toast、弹窗/表单、Loading/Empty State

#### J1. 连贯性与一致性（Coherence & Consistency）
- 视觉一致性（Visual Consistency）
  - 要点：布局栅格、间距、圆角、阴影、字体、图标体系、配色 token 统一；避免“工作台一套、编辑器一套”。
  - 重点审查：编辑器容器样式与工作台主题的统一（背景、按钮、边框、z-index、dark mode 行为）。
- 行为一致性（Behavior Consistency）
  - 要点：相似操作（生成/保存/返回/关闭）具备相同交互模式：按钮位置、快捷键、禁用与 loading 状态、反馈方式一致。
  - 重点审查：所有 async 操作（SSE 生成、上传、入库）是否有明确加载态、可取消、失败可重试、错误贴近来源。
- 概念连贯性（Conceptual Coherence）
  - 要点：用户心理模型保持一致（“我在哪 / 我下一步做什么 / 我的数据会保存吗”）。
  - 重点审查：术语与状态统一（课程/单元/大纲/模板/预览/编辑/导出），以及侧边栏进度点的含义与实际状态吻合。

#### J2. 用户路径/操作流（User Flow）
- 主链路（建议保持线性、最少步骤）：
1. 选择课程 → 选择/新建单元
2. 生成/编辑大纲（Outline）
3. 选择模板（PPT）→ 生成 → 预览
4. 进入编辑器（Edit）→ 导出（Export）→ 返回工作台
- 关键原则（奥卡姆剃刀）：
  - 默认路径最短；高级开关默认折叠且有“推荐默认值”提示。
  - 每一步都提供“下一步 CTA”，并清晰告知“当前状态/是否已保存”。
- DoD：
  - 用户在任意页面能在 1 次点击内回到工作台；不会出现死胡同。
  - 主链路每一步都有明确反馈（成功/失败/进行中），并能理解下一步。

#### J3. 交互设计（Interaction Design / IxD）
- 心流（Flow）
  - 生成过程避免“突然跳变”：骨架屏/进度提示、增量结果、稳定布局（避免 content jump）。
- 反馈回路（Feedback Loop）
  - 点击/提交后 150–300ms 内提供视觉反馈；按钮在请求中禁用并展示 loading。
  - 错误提示贴近触发点（表单/开关/网络请求），toast 只用于全局提醒。
- DoD：
  - SSE 生成支持“取消/中止”并恢复 UI 状态。
  - 关键操作（生成/保存/返回/导出）拥有一致的 loading/disabled/成功提示模式。

#### J4. 信息架构（Information Architecture / IA）
- 视觉层级（Visual Hierarchy）
  - 工作台头部：单元标题 + 状态 → Tab → 主内容；避免同权信息过多导致注意力分散。
- 接近原则（Proximity）
  - “课程级模块（KB/Assistant）”与“单元级模块（Outline/Lesson/PPT）”在导航与文案上明确区分。
- DoD：
  - 用户无需试错即可理解“当前是课程维度还是单元维度”。

#### J5. 可访问性与基础交互规范（来自 ui-ux-pro-max，P0 必做）
- [ ] 所有 icon-only 按钮补齐 `aria-label`；所有可点击元素都有清晰 hover/active/focus 样式。
- [ ] Touch target ≥ 44×44px；表单输入有 label；错误信息支持 `role=alert` 或 `aria-live`。
- [ ] 避免 emoji 作为 UI 图标（使用 Lucide/SVG）；如需插图，确保语义与风格一致。
- [ ] 支持 `prefers-reduced-motion`（动画可降级）。

### 阶段 K：性能与质量门槛（P1）
目标：把“可用”提升为“稳定、可迭代”，并为后续功能扩展留出空间。

- [ ] K1. 性能基线
  - 关注点：首屏资源、编辑器按需加载、长列表（缩略图）渲染成本、生成过程内存占用。
- [ ] K2. 自动化与回归保障
  - SSE 解析单测、持久化迁移单测、关键 store/路由守卫测试。
  - 保持 `typecheck/lint/build` 作为 PR 必过门槛。

## 3. 连贯性设计（Coherence）专项：详细审查清单（可执行）

> 目的：把“顺滑、不割裂”从抽象要求落到可检查、可验收的条目。

### 3.1 视觉一致性（Visual）
- [ ] 全局字体与字号层级一致（标题/正文/辅助信息有固定层级）。
- [ ] 颜色 token 统一（Primary/Success/Warning/Danger/Border/Surface），禁止页面私自引入“另一套灰度/圆角/阴影”。
- [ ] 组件圆角/阴影/边框风格一致（卡片、按钮、输入框、弹窗、toast）。
- [ ] 图标体系统一（Lucide 为主）；不使用 emoji 代替图标。

### 3.2 行为一致性（Behavior）
- [ ] 生成/上传/保存等 async 行为统一：
  - 触发后按钮禁用 + loading；
  - 可取消/可重试；
  - 失败提示明确原因与下一步操作（去 KB、检查后端、重试）。
- [ ] “返回/关闭”交互一致（位置、文案、是否二次确认）。
- [ ] Toast 规则一致：成功/失败提示不打断流程、不会遮挡关键操作（尤其编辑器）。

### 3.3 概念连贯性（Concept）
- [ ] 术语一致：课程/单元/大纲/模板/预览/编辑/导出/知识库/产物入库。
- [ ] 进度与状态可解释：侧边栏提示点与实际数据状态一致（不出现“看起来完成但实际没保存”）。
- [ ] 数据保存策略可预期：哪些自动保存、哪些需要显式保存，在 UI 上有明确提示。

### 3.4 用户路径（User Flow）
- [ ] 任一页面都能回答：
  - 我从哪来（入口）？
  - 我在哪（当前模块/单位）？
  - 我该去哪（下一步 CTA）？
- [ ] 主链路步骤尽可能少；高级能力可选但不打断主路径。

### 3.5 交互设计（IxD）
- [ ] 150–300ms 的微交互反馈（hover/press/focus）。
- [ ] Loading/Empty/Error 三态完整（不出现空白/静默失败）。
- [ ] 动画尊重 `prefers-reduced-motion`。

### 3.6 信息架构（IA）
- [ ] 导航结构清晰：课程级与单元级分层明确。
- [ ] 视觉层级清楚：主 CTA 明显、次要操作弱化但可达。

### 3.7 当前初步发现（基于代码快速审查，待阶段 J 逐项消除）
- 视觉一致性：
  - 工作台（Tailwind + slate/indigo）与独立编辑器容器（独立配色/按钮风格）存在风格断层，容易产生“跳到另一个系统”的感受。
  - 个别地方使用 emoji 作为视觉元素/按钮符号，破坏图标体系一致性（应统一为 Lucide/SVG）。
- 行为一致性 / 可访问性：
  - 部分 icon-only 按钮缺少可访问名称（`aria-label`），键盘 focus 样式不统一（需形成“默认可见 focus ring”规范）。
  - Toast 当前以视觉为主，需补齐 `aria-live`/`role` 以确保错误可被辅助技术读出。
- 概念连贯性：
  - “自动保存/退出保存/保存失败是否影响流程”的提示需要统一；用户需要明确知道数据是否已持久化以及回显来源（presentation vs editorDocument）。
- 架构支撑（与连贯性强相关）：
  - 当前全量 state 持久化到 localStorage 的策略存在配额与性能风险，会直接造成体验割裂（卡顿/白屏/数据丢失感），优先级需置顶（阶段 I1）。

## 4. 连贯性（Coherence）/无缝体验（Seamless UX）专项审查：问题清单与修复方案（2026-02-16）

> 说明：本节是“现在的真实审查结论”，把问题落到具体代码位置，并给出可执行的修复方案与 DoD。  
> 审查目标：减少“像跳到另一个系统”的割裂感，让用户在主链路（Outline → PPT → Editor → Export）中保持可预期、可回溯、可操作的闭环体验。

### 4.1 视觉一致性（Visual Consistency）

#### 问题 4.1.1 工作台 vs 独立编辑器风格断层（含暗色模式不一致）
- 现象/影响：
  - 编辑器页面不使用工作台的布局与 top bar，且背景/按钮风格独立，用户感知为“跳到另一个产品”。
  - 全局 dark mode 打开时，编辑器容器仍是固定浅色背景，割裂更明显。
- 证据（代码位置）：
  - 编辑器路由是独立顶层路由（不在 MainLayout children 内）：`teachdo-frontend/src/router/index.ts`
  - 编辑器容器背景/文本颜色固定：`teachdo-frontend/src/views/PPTEditorView.vue`
- 修复方案：
  1. 视觉层：为编辑器容器引入与工作台一致的设计 token（surface/bg/border/text），并在 `.dark` 下提供对应变量或样式覆盖，保证主题切换一致。
  2. 导航层（两种方案二选一）：
     - 方案 A：编辑器仍全屏，但顶部保留缩窄版 `AppTopBar`（仅返回/标题/导出）；
     - 方案 B：继续使用独立返回按钮，但统一按钮样式（大小、圆角、边框、hover/focus）与 top bar 一致，并补充“当前位置（课程/单元）”信息。
- DoD：
  - dark mode 下编辑器背景/按钮/文字与工作台一致，不出现“亮屏刺眼/两套主题”。
  - 进入/退出编辑器时，用户能清晰感知同一应用内的连续体验（视觉与文案一致）。

#### 问题 4.1.2 UI 中仍存在 emoji 作为图标/符号，破坏图标体系一致性
- 现象/影响：emoji 在不同平台渲染差异大，会显得“不专业/不统一”，也与 Lucide 图标体系冲突。
- 证据（代码位置，非穷举）：
  - 工作台空状态：`teachdo-frontend/src/views/CourseWorkspaceView.vue`
  - Outline 空状态与 CTA：`teachdo-frontend/src/components/workspace/OutlineView.vue`
  - PPT 生成按钮：`teachdo-frontend/src/components/workspace/PPTView.vue`
  - Lesson 空状态：`teachdo-frontend/src/components/workspace/LessonPlanView.vue`
  - Toast 关闭按钮：`teachdo-frontend/src/components/common/ToastContainer.vue`
- 修复方案：
  1. 统一使用 LucideIcon（例如 `sparkles/file-text/x`）替换 emoji；
  2. 仅允许 emoji 作为“内容”（例如编辑器符号面板插入），禁止作为 UI 图标/按钮文案前缀。
- DoD：
  - `teachdo-frontend/src` 中不再出现用于 UI 的 emoji（编辑器符号库等“内容型 emoji”除外）。
  - 所有图标来自同一套 icon set（LucideIcon）。

### 4.2 行为一致性（Behavior Consistency）与可访问性（A11y，P0）

#### 问题 4.2.1 图标按钮缺少可访问名称（aria-label），键盘用户难以操作
- 现象/影响：
  - 当前 LucideIcon 默认 `aria-hidden=true`，若按钮只有 icon 且无文本，则屏幕阅读器无法读出按钮含义。
- 证据（代码位置，示例）：
  - 移动端打开侧边栏按钮（icon-only）：`teachdo-frontend/src/views/CourseWorkspaceView.vue`
  - 侧边栏关闭按钮（icon-only）：`teachdo-frontend/src/components/workspace/UnitSidebar.vue`
  - 顶部主题切换按钮（icon-only）：`teachdo-frontend/src/components/layout/AppTopBar.vue`
  - 发送按钮（icon-only）：`teachdo-frontend/src/components/workspace/AssistantView.vue`
- 修复方案：
  1. 新增 `IconButton`（或统一的 button wrapper）组件：强制要求 `aria-label`，并统一尺寸（≥44×44）、focus ring、disabled 样式；
  2. 全量替换项目内 icon-only 按钮为 `IconButton`，或在原按钮上补 `aria-label` + `focus-visible:*`。
- DoD：
  - 任意 icon-only 按钮都可被读屏正确读出含义；
  - 键盘 Tab 可遍历所有可交互元素，且焦点可见（focus ring 明确）。

#### 问题 4.2.2 存在“可点击但非语义化元素”（div/article）导致键盘不可达
- 现象/影响：鼠标可用，但键盘/读屏不可用；也会导致行为一致性差（同类“卡片”有的可聚焦有的不可聚焦）。
- 证据（代码位置，示例）：
  - 课程卡片用 `<article @click>`：`teachdo-frontend/src/views/CourseSelectionView.vue`
  - KB 上传区域用 `<div @click>`：`teachdo-frontend/src/components/workspace/KnowledgeBaseView.vue`
  - 模板选择卡片用 `<div @click>`：`teachdo-frontend/src/components/workspace/PPTView.vue`
- 修复方案：
  1. 将上述交互点改为语义化 `<button type="button">` 或 `<RouterLink>`；
  2. 若需保留容器结构，则补 `role="button"`、`tabindex="0"`、`@keydown.enter.space`，并加 focus-visible 样式（但优先语义化按钮/链接）。
- DoD：
  - 课程选择、KB 上传、模板选择都可全键盘完成；
  - 交互区域 hover/active/focus 行为一致，且不会造成布局跳动。

#### 问题 4.2.3 Toast 缺少 aria-live / role，关闭按钮过小且使用 emoji
- 现象/影响：错误提示对读屏用户不可达；关闭按钮命中区域小，不符合 touch target。
- 证据：`teachdo-frontend/src/components/common/ToastContainer.vue`
- 修复方案：
  1. Toast 容器增加 `aria-live="polite"`（成功/信息）与 `role="alert"`（错误）或按类型区分；
  2. 关闭按钮改为 LucideIcon `x`，并补 `aria-label`、`type="button"`、触控尺寸 ≥44×44；
  3. Toast 不遮挡关键操作（尤其编辑器左上角返回按钮），必要时在 editor 路由下调整位置。
- DoD：
  - 读屏可读出 toast 文本；移动端可轻松关闭；不会遮挡关键 UI。

### 4.3 用户路径（User Flow）与闭环（Closed-loop）

#### 问题 4.3.1 PPT 页面缺少“无大纲”时的下一步 CTA，且标题复用 lesson 文案不严谨
- 现象/影响：用户在 PPT Tab 遇到“需要大纲”后无明确入口跳转，操作流断裂；并且标题复用 `lesson.need_outline.title`，概念上不严谨。
- 证据：`teachdo-frontend/src/components/workspace/PPTView.vue`
- 修复方案：
  1. 增加 `ppt.need_outline.title/desc/cta` i18n 文案；
  2. 在 PPT 空状态加入 CTA（“前往大纲”按钮，跳转到 outline tab），并保持与 Lesson 空状态一致的布局与按钮层级。
- DoD：
  - 用户在 PPT 页无需思考即可完成下一步跳转（不出现死胡同）。

#### 问题 4.3.2 SSE 生成缺少“取消/中止”，中途出错/想停止会造成强割裂
- 现象/影响：生成过程只能等待完成；网络或模型异常会放大挫败感，破坏心流（Flow）。
- 证据：
  - Outline 生成：`teachdo-frontend/src/components/workspace/OutlineView.vue`
  - PPT 生成：`teachdo-frontend/src/components/workspace/PPTView.vue`
- 修复方案：
  1. aiService 支持 `AbortController`（为 fetch 透传 `signal`），并统一 cancellation 错误处理；
  2. UI 增加“取消生成”按钮，取消后恢复到可操作状态（保留已生成内容或明确回滚策略）；
  3. 取消/失败提示规则统一（toast + 局部提示）。
- DoD：
  - Outline 与 PPT 生成都可取消；取消不导致 UI 卡死/脏状态；用户知道发生了什么。

### 4.4 文案与国际化一致性（Copy & i18n）

#### 问题 4.4.1 顶部状态指示与设置页存在硬编码文案，导致语言与风格不一致
- 现象/影响：同一界面中中英混杂，降低专业感；也不利于后续国际化。
- 证据（示例）：
  - 顶部状态按钮硬编码 `Checking/System/Online/Offline`：`teachdo-frontend/src/components/layout/AppTopBar.vue`
  - 设置页 toast/confirm 硬编码：`teachdo-frontend/src/views/SettingsView.vue`
  - KB 页标题面包屑文案不准确（assistant/kb 组合）：`teachdo-frontend/src/components/workspace/KnowledgeBaseView.vue`
- 修复方案：
  1. 统一改为 i18n key（已有 `nav.status.*` 可复用）；
  2. 梳理“课程级/单元级”的面包屑/标题策略，避免概念混乱（KB 不应显示成 Assistant 子级）。
- DoD：
  - 同一语言模式下无硬编码异语言文案；KB/Assistant 标题与信息架构一致。

### 4.5 安全与渲染一致性（补充，P0 风险）

#### 问题 4.5.1 多处使用 `v-html` 渲染模型/用户输入，存在 XSS 风险与渲染不可控
- 现象/影响：一旦输入或模型输出包含 HTML，将直接注入 DOM；不仅是安全问题，也会造成样式与结构“不可预期”，破坏一致性。
- 证据：
  - Outline：`teachdo-frontend/src/components/workspace/OutlineView.vue`
  - Assistant：`teachdo-frontend/src/components/workspace/AssistantView.vue`
- 修复方案：
  1. 引入安全的渲染策略：要么使用可信 Markdown 渲染器并开启 sanitize，要么使用 DOMPurify 对输出做白名单清洗；
  2. 明确允许的标签集合（p/ul/li/strong/em/code/heading 等），禁用 script/style/事件属性；
  3. 补单测覆盖典型注入 payload（`<script>`、`onerror` 等）。
- DoD：
  - 用户输入/模型输出无法注入脚本；渲染结构稳定可控，样式一致。
