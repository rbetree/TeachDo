# TeachDo 开发计划（当前）

> 更新：2026-02-17  
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

- [x] I1. 持久化分层（LocalStorage 轻量化 + 大对象 IndexedDB）
  - 背景：当前 `appStore` 将整个 state `JSON.stringify` 写入 localStorage，且无写入失败兜底；`editorDocument.slides` 可能巨大，容易触发配额/卡顿/异常。
  - 进展（2026-02-17）：已完成 localStorage v2 轻量持久化 + IndexedDB(Dexie) 存储大字段 + legacy 自动迁移与启动回填；localStorage 写入增加失败兜底。
  - 方案：
    1. LocalStorage 仅持久化“轻量元数据”（currentCourseId/currentUnitId、theme、language、课程与单元的轻量字段）。
    2. `editorDocument`、大纲/生成产物等“大文本/大数组”统一走 IndexedDB（可复用 editor-runtime Dexie 或单独建表），并提供迁移与降级策略。
  - DoD：
    1. 无论 slides 体量多大，刷新/切换路由不出现 localStorage 配额错误与明显卡顿。
    2. “预览回显/编辑器回显”稳定（支持加载失败降级到 `presentation`）。

- [x] I2. 依赖边界与首屏瘦身（避免 editor-runtime 侵入工作台首屏）
  - 背景：当前 `teachdo-frontend/src/main.ts` 全局 `app.use(EditorIconPlugin/EditorDirectivePlugin)`，且工作台 `teachdo-frontend/src/components/workspace/PPTView.vue` 直接 import `@editor/*`，会把 editor-runtime 依赖链带进首屏/工作台。
  - 进展（2026-02-17）：已完成方案 1/2/3（插件按编辑器路由加载 + 工作台 Tab 懒加载 + PPT 预览解除 `@editor/*` 静态依赖，改为按需加载缩略图/生成器/Store）。
  - 方案：
    1. 将 editor-runtime 相关插件/依赖改为“仅在编辑器路由按需加载与注册”（进入编辑器再 import/use）。
    2. 工作台 Tab（Outline/Lesson/PPT）改为懒加载（async component 或子路由 code-splitting）。
    3. PPT 预览页避免静态引用 editor-runtime 的重依赖（按需加载缩略图/渲染器）。
  - DoD：
    1. 首屏（课程选择/工作台）不加载 editor-runtime 相关 chunk（以 `vite build` 产物/Network 验证）。
    2. 进入 `/course/:courseId/unit/:unitId/ppt/editor` 后再加载编辑器相关资源。

- [x] I3. Service 层收敛（aiService 拆分与去重）
  - 进展（2026-02-17）：已按领域拆分 `ppt/outline/kb` 服务模块；抽出统一 `apiClient`（超时/取消/HTTP/后端错误模型）；清理未使用的 legacy `generatePPT`。
  - 方案：按领域拆分 `ppt/outline/kb`，统一错误模型（超时/取消/后端不可用提示），清理“已不再使用但仍保留的旧实现”。
  - DoD：同一类错误在所有页面表现一致（文案、toast、重试策略一致）。

- [x] I4. PPTView 组件拆分（可维护、可测试）
  - 进展（2026-02-17）：已完成拆分（模板选择/预览渲染/高级选项弹窗）+ `usePptGeneration` composable + 纯函数工具（slide 映射/Markdown 产物构建），PPTView 仅保留路由与胶水逻辑。
  - 方案：拆为“模板选择/高级选项/生成状态/预览渲染/入库”等子组件 + composable（如 `usePptGeneration`）。
  - DoD：
    1. 生成逻辑从组件中抽离（composable + 状态机/纯函数），不依赖 DOM 也能验证。
    2. 在 K2 引入前端单测基座后，补齐 SSE 解析与生成状态机关键分支单测。

### 阶段 J：连贯性/无缝体验（P0）
目标：减少“像跳到另一个系统”的割裂感，让主链路（Outline → PPT → Editor → Export）连续、可预期、可回溯。

- 范围（页面/入口）：
  1. 课程选择页（`/`）
  2. 工作台（`/course/:courseId[/unit/:unitId/:tab]`）：Outline / Lesson / PPT
  3. 课程级页面：KB / Assistant
  4. 独立编辑器（`/course/:courseId/unit/:unitId/ppt/editor`）
  5. 通用组件：Sidebar、Header Tabs、Toast、弹窗/表单、Loading/Empty State
- 验收口径（DoD）：
  - 视觉：工作台与编辑器共用同一套 token/交互样式（含 dark mode）；UI 图标统一（不再用 emoji 充当图标）。
  - 行为：生成/上传/保存/返回/导出 loading/禁用/错误/重试/取消规则一致；toast 不遮挡关键操作且具备 `aria-live/role`。
  - 路径：每一步有“下一步 CTA”，不出现死胡同；任意页面 1 次点击内回到工作台。
  - A11y：icon-only 按钮强制 `aria-label`；触控目标 ≥44×44；焦点可见；交互点语义化（button/link）。
  - 安全：禁止直接 `v-html` 渲染未清洗内容（Markdown 渲染必须 sanitize）。
- 执行入口：第 3 节「问题清单与修复方案」按优先级逐项关闭。

### 阶段 K：性能与质量门槛（P1）
目标：把“可用”提升为“稳定、可迭代”，并为后续功能扩展留出空间。

- [ ] K1. 性能基线
  - 关注点：首屏资源、编辑器按需加载、长列表（缩略图）渲染成本、生成过程内存占用。
- [ ] K2. 自动化与回归保障
  - 先补齐前端单测基座（Vitest 或等价方案）+ `npm run test`，覆盖 SSE 解析、持久化迁移、Markdown sanitize 等关键纯逻辑。
  - 保持 `typecheck/lint/build` 作为 PR 必过门槛。

## 3. 连贯性专项：问题清单与修复方案（2026-02-16）

> 说明：本节是“现在的真实审查结论”，把问题落到具体代码位置，并给出可执行的修复方案与 DoD。  
> 审查目标：减少“像跳到另一个系统”的割裂感，让用户在主链路（Outline → PPT → Editor → Export）中保持可预期、可回溯、可操作的闭环体验。

### 3.1 视觉一致性（Visual Consistency）

#### 问题 3.1.1 工作台 vs 独立编辑器风格断层（含暗色模式不一致）
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

#### 问题 3.1.2 UI 中仍存在 emoji 作为图标/符号，破坏图标体系一致性
- 现象/影响：emoji 在不同平台渲染差异大，会显得“不专业/不统一”，也与 Lucide 图标体系冲突。
- 证据（代码位置，非穷举）：
  - 工作台空状态：`teachdo-frontend/src/views/CourseWorkspaceView.vue`
  - Outline 空状态与 CTA：`teachdo-frontend/src/components/workspace/OutlineView.vue`
  - PPT 生成按钮：`teachdo-frontend/src/components/workspace/ppt/PptTemplateSelector.vue`
  - Lesson 空状态：`teachdo-frontend/src/components/workspace/LessonPlanView.vue`
  - Toast 关闭按钮：`teachdo-frontend/src/components/common/ToastContainer.vue`
- 进展（2026-02-17）：已移除 Toast 关闭按钮与 PPT 生成按钮中的 UI emoji，改为 LucideIcon。
- 修复方案：
  1. 统一使用 LucideIcon（例如 `sparkles/file-text/x`）替换 emoji；
  2. 仅允许 emoji 作为“内容”（例如编辑器符号面板插入），禁止作为 UI 图标/按钮文案前缀。
- DoD：
  - `teachdo-frontend/src` 中不再出现用于 UI 的 emoji（编辑器符号库等“内容型 emoji”除外）。
  - 所有图标来自同一套 icon set（LucideIcon）。

### 3.2 行为一致性（Behavior Consistency）与可访问性（A11y，P0）

#### 问题 3.2.1 图标按钮缺少可访问名称（aria-label），键盘用户难以操作
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

#### 问题 3.2.2 存在“可点击但非语义化元素”（div/article）导致键盘不可达
- 现象/影响：鼠标可用，但键盘/读屏不可用；也会导致行为一致性差（同类“卡片”有的可聚焦有的不可聚焦）。
- 证据（代码位置，示例）：
  - 课程卡片用 `<article @click>`：`teachdo-frontend/src/views/CourseSelectionView.vue`
  - KB 上传区域用 `<div @click>`：`teachdo-frontend/src/components/workspace/KnowledgeBaseView.vue`
  - 模板选择卡片用 `<div @click>`：`teachdo-frontend/src/components/workspace/ppt/PptTemplateSelector.vue`
- 进展（2026-02-17）：上述交互点已改为语义化 `RouterLink/button`，并补齐 focus-visible 样式，可全键盘操作。
- 修复方案：
  1. 将上述交互点改为语义化 `<button type="button">` 或 `<RouterLink>`；
  2. 若需保留容器结构，则补 `role="button"`、`tabindex="0"`、`@keydown.enter.space`，并加 focus-visible 样式（但优先语义化按钮/链接）。
- DoD：
  - 课程选择、KB 上传、模板选择都可全键盘完成；
  - 交互区域 hover/active/focus 行为一致，且不会造成布局跳动。

#### 问题 3.2.3 Toast 缺少 aria-live / role，关闭按钮过小且使用 emoji
- 现象/影响：错误提示对读屏用户不可达；关闭按钮命中区域小，不符合 touch target。
- 证据：`teachdo-frontend/src/components/common/ToastContainer.vue`
- 进展（2026-02-17）：Toast 已按类型补齐 `role/aria-live/aria-atomic`；关闭按钮改为 LucideIcon 并补 `aria-label`，触控目标 ≥44×44。
- 修复方案：
  1. Toast 容器增加 `aria-live="polite"`（成功/信息）与 `role="alert"`（错误）或按类型区分；
  2. 关闭按钮改为 LucideIcon `x`，并补 `aria-label`、`type="button"`、触控尺寸 ≥44×44；
  3. Toast 不遮挡关键操作（尤其编辑器左上角返回按钮），必要时在 editor 路由下调整位置。
- DoD：
  - 读屏可读出 toast 文本；移动端可轻松关闭；不会遮挡关键 UI。

### 3.3 用户路径（User Flow）与闭环（Closed-loop）

#### 问题 3.3.1 PPT 页面缺少“无大纲”时的下一步 CTA，且标题复用 lesson 文案不严谨
- 现象/影响：用户在 PPT Tab 遇到“需要大纲”后无明确入口跳转，操作流断裂；并且标题复用 `lesson.need_outline.title`，概念上不严谨。
- 证据：`teachdo-frontend/src/components/workspace/PPTView.vue`
- 进展（2026-02-17）：已补齐 `ppt.need_outline.*` i18n，并在 PPT 空状态加入“前往大纲”CTA。
- 修复方案：
  1. 增加 `ppt.need_outline.title/desc/cta` i18n 文案；
  2. 在 PPT 空状态加入 CTA（“前往大纲”按钮，跳转到 outline tab），并保持与 Lesson 空状态一致的布局与按钮层级。
- DoD：
  - 用户在 PPT 页无需思考即可完成下一步跳转（不出现死胡同）。

#### 问题 3.3.2 SSE 生成缺少“取消/中止”，中途出错/想停止会造成强割裂
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

### 3.4 文案与国际化一致性（Copy & i18n）

#### 问题 3.4.1 顶部状态指示与设置页存在硬编码文案，导致语言与风格不一致
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

### 3.5 安全与渲染一致性（补充，P0 风险）

#### 问题 3.5.1 多处使用 `v-html` 渲染模型/用户输入，存在 XSS 风险与渲染不可控
- 现象/影响：一旦输入或模型输出包含 HTML，将直接注入 DOM；不仅是安全问题，也会造成样式与结构“不可预期”，破坏一致性。
- 证据：
  - Outline：`teachdo-frontend/src/components/workspace/OutlineView.vue`
  - Assistant：`teachdo-frontend/src/components/workspace/AssistantView.vue`
- 进展（2026-02-17）：已对渲染内容做 HTML 转义（确保 `v-html` 仅输出受控标签），避免注入脚本/事件属性。
- 修复方案：
  1. 引入安全的渲染策略：要么使用可信 Markdown 渲染器并开启 sanitize，要么使用 DOMPurify 对输出做白名单清洗；
  2. 明确允许的标签集合（p/ul/li/strong/em/code/heading 等），禁用 script/style/事件属性；
  3. 补单测覆盖典型注入 payload（`<script>`、`onerror` 等）。
- DoD：
  - 用户输入/模型输出无法注入脚本；渲染结构稳定可控，样式一致。
