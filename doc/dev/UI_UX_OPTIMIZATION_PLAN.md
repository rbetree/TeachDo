# TeachDo 前端 UI/UX 深度审查与优化方案（2026-02-19）

> 适用范围：`frontend/`（**不含** `frontend/src/editor-runtime/**` 的内部控件与交互细节）  
> 参考标准：Vercel Web Interface Guidelines（已抓取最新版：`/tmp/web-interface-guidelines-command.md`）+ 项目现有代码结构与约束  
> 更新：2026-02-19（P0/P1/P2 已全部落地，见第 3/5/6 节）

## 1. 摘要（要达成什么）
在**不改变信息架构（仍通过“返回列表”切换教学资料）**、**不深入 PPT 编辑器内部实现**的前提下，系统性提升 TeachDo 工作台链路的：
- **可访问性（A11y）与可操作性**：键盘/读屏可用、触控目标合规、弹窗聚焦正确且 Tab 不逃逸。
- **心流与可控性**：Outline / PPT / Assistant 的流式生成可取消/停止，错误与离线反馈一致。
- **一致性与专业感**：去硬编码文案，中英一致；动效与视觉细节更稳更轻。

最终交付物是一个可执行的任务清单（P0/P1/P2），每项都给出**证据定位（file:line）**、改动文件、实现要点与验收（DoD）。

---

## 1.1 执行状态（截至 2026-02-19）
> 下面列的是“落地证据定位”（修复后的代码位置），便于复查与回归。

- ✅ TopBar 语义化导航 + A11y + i18n：`frontend/src/components/layout/AppTopBar.vue:70`
- ✅ Skip Link：`frontend/src/layouts/MainLayout.vue:12`
- ✅ Assistant：Shift+Enter/Enter + Stop + A11y：`frontend/src/components/workspace/AssistantView.vue:300`
- ✅ Outline：可取消生成（AbortController）：`frontend/src/components/workspace/OutlineView.vue:54`
- ✅ PPT：可取消生成 + 取消后 banner/部分结果策略：`frontend/src/components/workspace/PPTView.vue:151`
- ✅ KB：触控目标 + 进度条动效 + 上传 dropzone 键盘可达：`frontend/src/components/workspace/KnowledgeBaseView.vue:586`
- ✅ Dialog：统一 focus trap + backdrop 键盘等价：`frontend/src/utils/focusTrap.ts:9`
- ✅ Settings：文案 i18n + Key 显隐按钮 A11y：`frontend/src/views/SettingsView.vue:48`
- ✅ LessonPlan：无大纲时明确引导；生成可取消（AbortController）+ 失败回滚：`frontend/src/components/workspace/LessonPlanView.vue:642`
- ✅ 动效治理：移除 `transition-all`/`transition: all`（范围内）：`frontend/src/components/common/ToastContainer.vue:76`
- ✅ 字体与暗色一致性：`frontend/index.html:7`、`frontend/src/style.css:33`

---

## 2. 设计系统方向（轻量约束，不引入重 UI 框架）
基于 `ui-ux-pro-max` 的检索结果（风格/颜色/字体）并结合现状（Tailwind + 现有配色）：

### 2.1 颜色（建议保持现状：Indigo 主色 + Emerald 行动色）
- Primary：`indigo`（建议锚定 `indigo-600` / `#4F46E5`–`#6366F1` 区间）
- CTA：`emerald`（建议锚定 `emerald-500` / `#10B981` 区间）
- 背景：浅色 `slate-50`，深色 `slate-900`
- 文本：浅色 `slate-900`，深色 `slate-100`

### 2.2 字体（建议保持现状）
- 中文：`Noto Sans SC`（可读性与覆盖面更稳）
- 英文/数字：`Inter`

### 2.3 版式/风格（Bento Grid + Inclusive Design）
- 列表页与工作台主要采用**Bento Box Grid**（卡片化、留白、层级清晰）。
- A11y 作为**设计系统硬约束**：focus ring、触控目标、语义化组件、减少动效等。

---

## 3. Web Interface Guidelines 审查结果（原问题与修复证据，已全部修复）
> 按文件分组，使用 `file:line`（VS Code 可点击）。以下定位均为“修复后的证据”。

## frontend/src/components/layout/AppTopBar.vue
- `frontend/src/components/layout/AppTopBar.vue:70` - 内部导航改用 `RouterLink`（支持 Cmd/Ctrl+Click / 中键），并为 icon-only 提供 `aria-label`
- `frontend/src/components/layout/AppTopBar.vue:22` - 状态文案改为 i18n（`nav.status.*`）
- `frontend/src/components/layout/AppTopBar.vue:170` - 主题/语言切换补 `aria-label`（`a11y.toggle_theme` / `a11y.toggle_language`）

## frontend/src/layouts/MainLayout.vue
- `frontend/src/layouts/MainLayout.vue:12` - 增加 Skip Link
- `frontend/src/layouts/MainLayout.vue:18` - `<main id="main-content" tabindex="-1">`

## frontend/src/components/workspace/AssistantView.vue
- `frontend/src/components/workspace/AssistantView.vue:300` - Enter 发送、Shift+Enter 换行（不再 `.prevent`）
- `frontend/src/components/workspace/AssistantView.vue:306` - 生成中可 Stop（AbortController.abort），并补齐输入框/按钮的 A11y 标签

## frontend/src/components/workspace/OutlineView.vue
- `frontend/src/components/workspace/OutlineView.vue:54` - 生成链路引入 `AbortController` 并透传 `signal`
- `frontend/src/components/workspace/OutlineView.vue:115` - `cancelGenerate()` + abort 视为“用户取消”（toast.info）
- `frontend/src/components/workspace/OutlineView.vue:256` - 生成中显示“取消”按钮（`common.cancel`）
- `frontend/src/i18n/index.ts:205` - `outline.toast.canceled`

## frontend/src/components/workspace/ppt/usePptGeneration.ts
- `frontend/src/components/workspace/ppt/usePptGeneration.ts:24` - 透传 `signal` + `generationCanceled/draftPreviewActive` 状态（用于“取消后保留部分结果”策略）
- `frontend/src/components/workspace/ppt/usePptGeneration.ts:232` - `cancelGenerate()`

## frontend/src/components/workspace/PPTView.vue
- `frontend/src/components/workspace/PPTView.vue:151` - 生成中显示“取消”按钮（`common.cancel`）
- `frontend/src/components/workspace/PPTView.vue:228` - 取消后展示 banner（允许回到已保存版本/重新生成）
- `frontend/src/i18n/index.ts:243` - `ppt.toast.canceled` / `ppt.toast.canceled_empty`

## frontend/src/components/workspace/KnowledgeBaseView.vue
- `frontend/src/components/workspace/KnowledgeBaseView.vue:586` - 导出/删除按钮命中区提升到 44×44（`w-11 h-11`）
- `frontend/src/components/workspace/KnowledgeBaseView.vue:613` - 进度条仅对 width 动画（`transition-[width]`）
- `frontend/src/components/workspace/KnowledgeBaseView.vue:624` - 上传 dropzone 改为 `<button type="button">`（键盘可达 + focus-visible）

## frontend/src/utils/focusTrap.ts
- `frontend/src/utils/focusTrap.ts:9` - 统一 focus trap 工具（Dialog 的 Tab/Shift+Tab 循环）

## frontend/src/components/workspace/TeachingMaterialCreateDialog.vue
- `frontend/src/components/workspace/TeachingMaterialCreateDialog.vue:105` - backdrop 改为全屏 `<button>`（键盘等价）并提供 `aria-label`
- `frontend/src/components/workspace/TeachingMaterialCreateDialog.vue:65` - Tab focus trap（`trapTabKey`）

## frontend/src/components/workspace/TeachingMaterialDeleteDialog.vue
- `frontend/src/components/workspace/TeachingMaterialDeleteDialog.vue:91` - backdrop 改为全屏 `<button>`（键盘等价）并提供 `aria-label`
- `frontend/src/components/workspace/TeachingMaterialDeleteDialog.vue:46` - Tab focus trap（`trapTabKey`）

## frontend/src/components/workspace/ppt/PptAdvancedDialog.vue
- `frontend/src/components/workspace/ppt/PptAdvancedDialog.vue:88` - backdrop 改为全屏 `<button>`（键盘等价）并提供 `aria-label`
- `frontend/src/components/workspace/ppt/PptAdvancedDialog.vue:51` - Tab focus trap（`trapTabKey`）

## frontend/src/components/workspace/KbFilePickerDialog.vue
- `frontend/src/components/workspace/KbFilePickerDialog.vue:312` - backdrop 改为全屏 `<button>`（键盘等价）并提供 `aria-label`
- `frontend/src/components/workspace/KbFilePickerDialog.vue:269` - Tab focus trap（`trapTabKey`）

## frontend/src/views/SettingsView.vue
- `frontend/src/views/SettingsView.vue:48` - `toast/confirm` 文案改为 i18n
- `frontend/src/views/SettingsView.vue:118` - Key 显隐按钮补 `aria-label/title/aria-pressed`

## frontend/src/components/workspace/LessonPlanView.vue
- `frontend/src/components/workspace/LessonPlanView.vue:642` - 无大纲时显示引导态（CTA 跳转 Outline），避免误把“不可生成”理解为故障

## frontend/src/components/common/ToastContainer.vue
- `frontend/src/components/common/ToastContainer.vue:76` - 动效从 `transition: all` 改为仅 `opacity, transform`

## frontend/index.html
- `frontend/index.html:7` - 增加 `color-scheme` / `theme-color`，并将字体加载移到 `<head><link rel=\"stylesheet\">` + `preconnect`

## frontend/src/style.css
- `frontend/src/style.css:33` - `color-scheme`（浅/深）与暗色原生控件一致性

---

## 4. 优化目标（DoD / 成功标准）
- **键盘可完成主链路**：创建教学资料 → 生成大纲（可取消）→ 生成 PPT（可取消）→ 打开 KB/Assistant（可键盘切换与关闭）。
- **icon-only 按钮 100% 有可访问名称**：`aria-label` +（建议）`title`；小屏隐藏文字不影响读屏。
- **触控目标合规**：主要操作按钮命中区域 ≥ 44×44（尤其 KB 导出/删除、侧栏切换、发送/停止）。
- **所有 Dialog/Modal 具备 focus trap**：Tab 循环、Esc 关闭、关闭后焦点回到触发按钮、打开时默认聚焦首个输入/主按钮。
- **流式生成可控**：Outline/PPT/Assistant 支持 Cancel/Stop；取消不弹“错误”，且 UI 状态可预测（保留/回滚策略明确）。
- **无硬编码异语言文案**：TopBar/Settings 等关键路径全面 i18n 化。
- **动效更安全**：不使用 `transition: all` 与 `transition-all`（在本次范围内文件全部替换）。

---

## 5. 实施计划（按优先级分阶段）

### P0（必须）A11y 基线 + 可取消/可停止
#### 1) TopBar：icon-only 可访问名称 + 状态 i18n + 导航语义化
**状态**：✅ 已完成（2026-02-19）

**改动文件**
- `frontend/src/components/layout/AppTopBar.vue`
- `frontend/src/layouts/MainLayout.vue`
- `frontend/src/i18n/index.ts`

**要点**
- 对所有在小屏会变成“纯图标”的按钮：增加 `aria-label`（或 `sr-only` 文本）。
- 内部导航（workspace/about/settings）改用 `RouterLink`（支持 Cmd/Ctrl+Click / 中键）。
- 状态文案 `Checking…/System/Online/Offline` 全量 i18n 化。
- 补充 Skip Link：在 `MainLayout.vue` 顶部加入 “跳到主内容” 链接，`<main>` 增加 `id`。

**验收**
- <lg 屏幕读屏能读出每个导航按钮名称；键盘 Tab 可跳过导航直接到主内容。

---

#### 2) Assistant：修复 Shift+Enter + 增加 Stop 入口 + A11y 标签
**状态**：✅ 已完成（2026-02-19）

**改动文件**
- `frontend/src/components/workspace/AssistantView.vue`
- `frontend/src/i18n/index.ts`

**要点**
- 替换 `@keydown.enter.prevent`：Enter 发送、Shift+Enter 换行。
- 发送按钮补 `aria-label/title`；输入框补 `aria-label`。
- 增加 “Stop/停止生成” 按钮（只在生成中出现），调用现有 `AbortController`。

**验收**
- Shift+Enter 可换行；生成中可停止；停止不弹 error toast。

---

#### 3) Outline：增加取消生成（AbortController 全链路）
**状态**：✅ 已完成（2026-02-19）

**改动文件**
- `frontend/src/components/workspace/OutlineView.vue`
- `frontend/src/i18n/index.ts`

**要点**
- 每次生成前创建新的 `AbortController`，并把 `signal` 透传到 `aiService.generateOutline(...)`。
- UI 在 `loading` 时显示 “取消”。
- 将 abort 视为“用户取消”：不走 `toast.error`，改 `toast.info`。

**验收**
- 生成中可取消，取消后 UI 可继续操作且状态一致。

---

#### 4) PPT 生成：增加取消生成 + 部分结果保留策略
**状态**：✅ 已完成（2026-02-19）

**改动文件**
- `frontend/src/components/workspace/ppt/usePptGeneration.ts`
- `frontend/src/components/workspace/PPTView.vue`
- `frontend/src/i18n/index.ts`

**要点**
- `usePptGeneration.handleGenerate()` 内创建 controller，透传到 `aiService.streamAipptSlides({ ..., signal })`。
- 增加 `cancelGenerate()`，取消后保留已生成 slides，并展示明确 banner（可重新生成补全）。

**验收**
- 生成中可取消；取消后预览仍可用；再次生成不叠加脏状态。

---

#### 5) KB：触控目标修正 + 进度条避免 `transition-all`
**状态**：✅ 已完成（2026-02-19）

**改动文件**
- `frontend/src/components/workspace/KnowledgeBaseView.vue`

**要点**
- 导出/删除按钮由 `w-7 h-7` 提升到 ≥44×44（如 `w-11 h-11`）。
- 进度条动画仅对 width 生效（`transition-[width]`）。
- 上传 dropzone 从 clickable `<div>` 改为 `<button>` 或 `<label for=file>`，并保证键盘可达。

**验收**
- 移动端易点；键盘可操作；进度动画不触发布局属性。

---

#### 6) Dialog：统一 focus trap + 初始聚焦
**状态**：✅ 已完成（2026-02-19）

**改动文件**
- `frontend/src/components/workspace/TeachingMaterialCreateDialog.vue`
- `frontend/src/components/workspace/TeachingMaterialDeleteDialog.vue`
- `frontend/src/components/workspace/ppt/PptAdvancedDialog.vue`
- `frontend/src/components/workspace/KbFilePickerDialog.vue`
- 新增：`frontend/src/utils/focusTrap.ts`

**要点**
- `trapTabKey()`：Tab/Shift+Tab 循环。
- 打开时聚焦首个输入或主要操作按钮；关闭后 restore focus（现已有）。
- backdrop 改为全屏 `<button type="button" :aria-label="t('common.close')">`（并阻止冒泡）。

**验收**
- Tab 不逃逸；Esc 可关；关闭后焦点回到触发按钮。

---

### P1（高收益）产品化细节：文案、禁用态、emoji 清理
#### 7) Settings：补齐 A11y + i18n（硬编码清零）
**状态**：✅ 已完成（2026-02-19）

**改动文件**
- `frontend/src/views/SettingsView.vue`
- `frontend/src/i18n/index.ts`

**要点**
- 眼睛按钮补 `aria-label/title`（show/hide）。
- `confirm(...)` 与 toast 文案改 i18n（明确标注 demo）。

---

#### 8) LessonPlan：无大纲时不可误解的引导态
**状态**：✅ 已完成（2026-02-19）

**改动文件**
- `frontend/src/components/workspace/LessonPlanView.vue`
- `frontend/src/i18n/index.ts`

---

#### 9) Emoji 图标清理（统一为 LucideIcon / SVG）
**状态**：✅ 已完成（2026-02-19）

**改动文件**
- `frontend/src/components/workspace/OutlineView.vue`（空态 icon、CTA 前缀等）

**验收**
- UI 不再使用 emoji 作为功能性图标（符合统一风格与可控性）。

---

### P2（可选）可持续治理：动效/字体/暗色一致性
#### 10) 动效：彻底替换范围内的 `transition-all` 与 `transition: all`
**状态**：✅ 已完成（2026-02-19）

**验收**
- `rg -n "transition-all|transition:\\s*all" frontend/src --glob '!editor-runtime/**'` 无命中。

---

#### 11) 字体加载与暗色原生控件一致性
**状态**：✅ 已完成（2026-02-19）

**改动文件**
- `frontend/index.html`
- `frontend/src/style.css`

**要点**
- 将 Google Fonts 从 `@import` 移到 `<head><link rel="stylesheet">`，并加入 `preconnect`。
- 增加 `color-scheme`（浅/深）以改善原生控件与滚动条。
- 增加 `<meta name="theme-color">`（至少提供与背景匹配的默认值；如需动态切换可后续增强）。

---

## 6. 验证与测试（每阶段都要跑）
### 自动化（已执行：2026-02-19）
- ✅ `cd frontend && npm run typecheck`
- ✅ `cd frontend && npm run lint`
- ✅ `cd frontend && npm run build`
- ✅ `cd frontend/src && rg -n "transition-all|transition:\\s*all" . --glob '!editor-runtime/**'`（范围内无命中）

备注：
- `npm run build` 可能仍会出现 Sass `@import` deprecation 警告与 chunk-size 警告，来源集中在 `editor-runtime` 相关 chunk，本方案范围明确排除该目录的深度改造。

### 手工验收（按主链路）
1) TopBar：小屏读屏可读、跳过导航可用、主题切换有 aria-label。  
2) 创建/删除 Dialog：初始聚焦正确、Tab 循环、Esc 关闭、关闭后恢复焦点。  
3) Outline：生成→取消不报错、状态可继续操作。  
4) PPT：生成→取消保留部分结果、提示明确、可再次生成。  
5) Assistant：Shift+Enter 换行、Enter 发送、生成中可 Stop。  
6) KB：导出/删除可轻松点击、上传 dropzone 键盘可达、进度条动效稳定。  
