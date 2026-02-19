# TeachDo 前端 UI/UX 深度审查与优化方案（不含 `editor-runtime`）

> 更新：2026-02-18  
> 已整理为正式文档：`doc/dev/UI_UX_OPTIMIZATION_PLAN.md`（本文件保留为草稿/历史版本）

## 摘要
目标是在**不改变信息架构（仍通过“返回列表”切换教学资料）**、**不深入 PPT 编辑器实现**的前提下，系统性提升 TeachDo 工作台链路的：
- **可访问性（A11y）与可操作性**：键盘/读屏可用、触控目标合规、弹窗可正确聚焦与循环。
- **心流与可控性**：Outline / PPT / Assistant 的流式生成可**取消/停止**，错误与离线反馈一致。
- **一致性与专业感**：去硬编码文案，中英一致；动效与视觉细节更稳更轻。

最终产出已整理为：`doc/dev/UI_UX_OPTIMIZATION_PLAN.md`（包含问题证据、优先级、DoD、验收清单）。

---

## 范围 / 不做
**范围（TeachDo Frontend）**
- 页面：`/` 教学资料列表、`/material/:id/:tab` 工作台（Outline/Lesson/PPT）、About、Settings
- 侧栏模块：知识库（KB）、AI 助教（Assistant）
- 通用：TopBar、Toast、全局样式（Tailwind + `style.css`）

**不做（明确排除）**
- 不审查/不改造 `teachdo-frontend/src/editor-runtime/**` 的控件可访问性与交互（仅允许“入口衔接”层面的轻改动，如必要）。
- 不引入新的重型 UI 框架；默认不新增运行时依赖（可新增少量 dev-only lint 规则属于 P2 可选）。

---

## 关键问题清单（含证据定位）
### A11y / 交互一致性
1) **小屏 icon-only 导航按钮缺少可访问名称**
- `teachdo-frontend/src/components/layout/AppTopBar.vue:126`（workspace 按钮在 <lg 无文字）
- `teachdo-frontend/src/components/layout/AppTopBar.vue:136`
- `teachdo-frontend/src/components/layout/AppTopBar.vue:146`
- `teachdo-frontend/src/components/layout/AppTopBar.vue:156`
- `teachdo-frontend/src/components/layout/AppTopBar.vue:175`（主题切换按钮）
- `teachdo-frontend/src/components/layout/AppTopBar.vue:70`（Logo 回到 workspace 小屏也无文字）

2) **Assistant 输入框无法 Shift+Enter 换行（.prevent 导致默认行为被阻止）**
- `teachdo-frontend/src/components/workspace/AssistantView.vue:279`–`288`

3) **KB 列表操作按钮触控目标不足 44×44**
- `teachdo-frontend/src/components/workspace/KnowledgeBaseView.vue:584`–`603`（`w-7 h-7`）

4) **弹窗缺少 focus trap（Tab 可逃逸到页面底层）**
- `teachdo-frontend/src/components/workspace/TeachingMaterialCreateDialog.vue`（现仅 focus 到 panel）
- `teachdo-frontend/src/components/workspace/TeachingMaterialDeleteDialog.vue`

### 心流 / 可控性
5) **Outline / PPT 生成不可取消；Assistant 生成不可显式停止**
- `teachdo-frontend/src/components/workspace/OutlineView.vue:50`–`86`（无 AbortController）
- `teachdo-frontend/src/components/workspace/ppt/usePptGeneration.ts:94`–`159`（`streamAipptSlides` 未透传 `signal`）
- `teachdo-frontend/src/components/workspace/PPTView.vue:136`–`205`（toolbar 无取消入口）
- Assistant 已有 `AbortController` 但 UI 无“停止”入口（`AssistantView.vue`）

### 文案 / 国际化
6) **TopBar 状态指示硬编码英文（且与 i18n 已存在 key 重复）**
- `teachdo-frontend/src/components/layout/AppTopBar.vue:111`–`121`

7) **Settings 的“演示”提示、confirm/toast 文案硬编码 + 眼睛按钮无 aria-label**
- `teachdo-frontend/src/views/SettingsView.vue:111`–`113`

### 动效 / 全局体验
8) **`transition-all` 与 `transition: all` 分散存在，可能触发布局相关动画**
- `transition-all`：`TeachingMaterialSelectionView.vue:171`、`OutlineView.vue:283/318`、`PPTView.vue:103`、`PptTemplateSelector.vue:44/68`、`PptPreviewPanel.vue:223/239/267/297/315`、`KnowledgeBaseView.vue:613` 等
- `transition: all`：`teachdo-frontend/src/components/common/ToastContainer.vue:76`

9) **字体通过 CSS `@import` 引入（可优化为 head link，提升加载与可控性）**
- `teachdo-frontend/src/style.css:1`

---

## 优化目标（DoD / 成功标准）
- **键盘可完成主链路**：创建教学资料 → 生成大纲（可取消）→ 生成 PPT（可取消）→ 打开 KB/Assistant（可键盘切换与关闭）。
- **icon-only 按钮 100% 有可访问名称**：`aria-label` +（建议）`title`；小屏隐藏文字不影响读屏。
- **触控目标合规**：主要操作按钮命中区域 ≥ 44×44（尤其 KB 导出/删除、侧栏折叠/切换、发送/停止）。
- **所有 Modal/Dialog 具备 focus trap**：Tab 循环、Esc 关闭、关闭后焦点回到触发按钮、打开时默认聚焦首个输入/主按钮。
- **流式生成可控**：Outline/PPT/Assistant 支持 Cancel/Stop；取消不弹“错误”，且 UI 状态可预测（保留/回滚策略明确）。
- **无硬编码异语言文案**：TopBar/Settings 等关键路径全面 i18n 化。
- **动效更安全**：不使用 `transition: all` 与 `transition-all`（在本次范围内的文件全部替换）。

---

## 实施计划（按优先级分阶段）
> 说明：P0 必须先落地；P1 为体验增强；P2 为可持续治理（可选）。

### P0（必须）A11y 基线 + 可取消/可停止
#### 1) TopBar：为小屏 icon-only 导航补齐可访问名称 + 状态文案 i18n
**改动文件**
- `teachdo-frontend/src/components/layout/AppTopBar.vue`
- `teachdo-frontend/src/i18n/index.ts`

**具体改法（决策已定）**
- 给以下按钮统一加 `:aria-label="t('...')"` 与 `:title="t('...')"`：
  - Logo 返回 workspace（`AppTopBar.vue:70`）
  - workspace/about/settings/website（`AppTopBar.vue:126/136/146/156`）
  - theme toggle（`AppTopBar.vue:175`）
- 状态 pill 文案替换为 i18n：
  - `Checking…/System/Online/Offline` → `t('nav.status.checking'|'nav.status.system'|'nav.status.online'|'nav.status.offline')`（`AppTopBar.vue:111`–`121`）
- 去掉 `LucideIcon` 上硬编码 `aria-label="checking backend status"`（`AppTopBar.vue:100`–`105`），改为：
  - 父按钮提供 `aria-label`（例如 `t('nav.status.checking')`），Icon 设 `aria-hidden="true"`。

**新增 i18n keys（中英都要补齐）**
- `nav.theme.to_light`: `切换到浅色` / `Switch to light`
- `nav.theme.to_dark`: `切换到深色` / `Switch to dark`

**验收**
- <lg 屏幕读屏仍能朗读每个导航按钮的名称。
- TopBar 状态文案随语言切换，无硬编码英文残留。

---

#### 2) Assistant：修复 Shift+Enter 换行 + 增加“停止生成”入口 + A11y 标签
**改动文件**
- `teachdo-frontend/src/components/workspace/AssistantView.vue`
- `teachdo-frontend/src/i18n/index.ts`

**具体改法**
- 把 `@keydown.enter.prevent`（`AssistantView.vue:287`）改为显式 keydown handler：
  - Enter（无 Shift）→ `event.preventDefault(); handleSend()`
  - Shift+Enter → 不阻止默认（允许换行）
- 发送按钮（`AssistantView.vue:289`）补齐：
  - `:aria-label="t('assistant.send')"`、`:title="t('assistant.send')"`
- 输入框 `<textarea>` 补齐：
  - `:aria-label="t('assistant.input_aria')"`（placeholder 不等价 label）
- 增加 Stop 按钮（推荐放 header 右侧，与清除按钮同区）：
  - 仅当 `isTyping` 为 true 时显示
  - 点击执行 `pendingController.value?.abort()`，并 `toast.info(t('assistant.toast.stopped'))`

**新增 i18n keys**
- `assistant.send`: `发送` / `Send`
- `assistant.stop`: `停止` / `Stop`
- `assistant.input_aria`: `输入消息` / `Message input`
- `assistant.toast.stopped`: `已停止生成` / `Generation stopped`

**验收**
- Shift+Enter 可换行；Enter 发送。
- 生成中可停止；停止后保留已生成的部分文本，不显示“错误”toast。
- 发送按钮与输入框对读屏有明确名称。

---

#### 3) Outline：增加“取消生成” + AbortController 全链路
**改动文件**
- `teachdo-frontend/src/components/workspace/OutlineView.vue`
- `teachdo-frontend/src/services/ai/outlineService.ts`
- `teachdo-frontend/src/i18n/index.ts`

**具体改法**
- 在 `OutlineView.vue` 增加 `abortControllerRef`：
  - 每次开始生成前先 abort 旧的 controller
  - 调用 `aiService.generateOutline(material, onStream, { signal })`
- UI：
  - toolbar 在 `loading` 时显示 `取消`按钮（优先放在右侧 action 区，与 regenerate/save 同一组）
- 取消后的状态策略（必须固定下来）：
  - **DIRECT 模式（原本无大纲）**：取消 → `loading=false`，保持 `outlineText=''`，停留在空态 PREVIEW。
  - **COMPARE 模式（已有大纲）**：取消 → `loading=false`，`newOutlineText=''`，`mode='PREVIEW'`，保留旧 `outlineText`。
- 错误处理：
  - abort 视为“用户取消”，不走 `toast.error`，走 `toast.info(t('outline.toast.cancelled'))`

**新增 i18n keys**
- `common.cancel`: `取消` / `Cancel`
- `outline.toast.cancelled`: `已取消生成` / `Generation cancelled`

**验收**
- 大纲生成中可取消，取消不产生 error toast；UI 不卡死、不残留 compare banner。

---

#### 4) PPT 生成：增加“取消生成” + 部分结果保留策略
**改动文件**
- `teachdo-frontend/src/components/workspace/ppt/usePptGeneration.ts`
- `teachdo-frontend/src/components/workspace/PPTView.vue`
- `teachdo-frontend/src/services/ai/pptService.ts`（只需确认 `signal` 已支持；当前已支持）
- `teachdo-frontend/src/i18n/index.ts`

**具体改法**
- `usePptGeneration`：
  - 新增 `abortControllerRef`
  - `handleGenerate()` 内创建 controller，并把 `signal` 传给 `aiService.streamAipptSlides({ ..., signal })`
  - 新增 `cancelGenerate()`：abort controller，并把 `loading=false`
  - 新增 `generationState`（必须有状态机，避免 UI 猜测）：
    - `'idle' | 'generating' | 'cancelled' | 'done' | 'error'`
- `PPTView.vue` toolbar：
  - `loading` 时显示 `取消`按钮（使用 `common.cancel`）
  - 点击调用 `cancelGenerate()`
- **部分结果保留策略（固定）**
  - 取消后保留已生成的 slides（`presentation.slides` & `editorSlides` 已累积部分）
  - 在预览区域顶部显示 banner（例如 amber）：
    - 文案：`已取消生成（已保留 {count} 页），可重新生成补全。`
    - 操作：`重新生成`（已有）+ `返回模板选择`（已有）
- toast：
  - 取消 → `toast.info(t('ppt.toast.cancelled', { count }))`

**新增 i18n keys**
- `ppt.toast.cancelled`: `已取消生成（已保留 {count} 页）` / `Generation cancelled (kept {count} slides)`

**验收**
- 生成中可取消；取消后预览可用且提示明确；再次生成不会叠加脏状态（slideIndex、loading、viewState 正常）。

---

#### 5) KB：触控目标修正（导出/删除按钮 ≥44×44）+ 进度条避免 `transition-all`
**改动文件**
- `teachdo-frontend/src/components/workspace/KnowledgeBaseView.vue`

**具体改法**
- 将 `w-7 h-7`（`KnowledgeBaseView.vue:584`、`:594`）调整为 `w-11 h-11 rounded-xl`（与工作台 header icon button 一致）
- 进度条 `transition-all`（`KnowledgeBaseView.vue:613`）改为 `transition-[width]` 或 `transition` + 明确只动画宽度（首选 `transition-[width] duration-300`）

**验收**
- 移动端可轻松点击导出/删除；键盘 focus ring 可见。

---

#### 6) Dialog：为创建/删除教学资料补 focus trap（Tab 循环）与初始聚焦
**改动文件**
- `teachdo-frontend/src/components/workspace/TeachingMaterialCreateDialog.vue`
- `teachdo-frontend/src/components/workspace/TeachingMaterialDeleteDialog.vue`
- 新增：`teachdo-frontend/src/utils/focusTrap.ts`（或 `src/utils/modalA11y.ts`，二选一，以下以 `focusTrap.ts` 为准）

**实现决策（统一方案）**
- 新增工具函数：
  - `getFocusable(container): HTMLElement[]`
  - `trapTabKey(event, container)`：在首/尾元素处循环
  - `focusFirst(container)`：打开时聚焦第一个可编辑输入（create）或确认按钮/checkbox（delete）
- 在 dialog panel 上绑定 `@keydown`：
  - `Escape` 走现有 close
  - `Tab` 调用 `trapTabKey`
- 打开时：
  - create dialog：聚焦标题 input（不是 panel）
  - delete dialog：聚焦“确认删除”按钮（或 checkbox，二选一；建议确认按钮）
- 继续保留：Esc 关闭、关闭后 restore focus、body scroll lock。

**验收**
- Tab/Shift+Tab 不会跳到弹窗外部。
- 关闭后焦点回到触发按钮（Create / Delete）。

---

### P1（高收益）产品化细节：Settings/Copy、Lesson“建设中”、KB 上传体验
#### 7) Settings：补齐 A11y + i18n（硬编码清零）
**改动文件**
- `teachdo-frontend/src/views/SettingsView.vue`
- `teachdo-frontend/src/i18n/index.ts`

**具体改法**
- 眼睛按钮补 `aria-label/title`（见 `SettingsView.vue:111`）
  - `aria-label = show ? t('common.hide') : t('common.show')`
- `confirm('确认恢复默认配置？')` 与 toast `'配置已保存（演示）'` i18n 化（明确标注演示）
- 新增 i18n keys：
  - `common.show`: `显示` / `Show`
  - `common.hide`: `隐藏` / `Hide`
  - `settings.toast.saved_demo`: `配置已保存（演示）` / `Config saved (demo)`
  - `settings.confirm.reset`: `确认恢复默认配置？` / `Reset to defaults?`

**验收**
- 设置页无硬编码中文/英文混杂；眼睛按钮可读屏识别。

---

#### 8) LessonPlan：把“建设中”体验做成“不可误解的禁用态”
**改动文件**
- `teachdo-frontend/src/components/workspace/LessonPlanView.vue`
- `teachdo-frontend/src/i18n/index.ts`（如需）

**具体改法**
- “教案生成（建设中）”按钮改为 disabled + 明确 tooltip/title，点击不再 toast（避免用户误以为失败）
- Copy/Download 仅在 `plan` 存在时显示（否则隐藏或 disabled）
- 空态 CTA 仍引导用户去 Outline（已存在）

**验收**
- 用户不会把“建设中”当成“故障”；界面动作与状态一致。

---

#### 9) KB 上传体验（多文件 + 明确支持格式）
**改动文件**
- `teachdo-frontend/src/components/workspace/KnowledgeBaseView.vue`
- `teachdo-frontend/src/i18n/index.ts`

**具体改法**
- `<input type="file">` 增加 `multiple`
- 拖拽 `drop` 支持批量：对 `dataTransfer.files` 全量入队上传（并发限制 2，队列顺序稳定）
- `accept`（从后端支持格式推导，来源：`backend/personaldb/core/document_processor.py:34`–`65`）：
  - 建议至少覆盖：`.pdf,.ppt,.pptx,.doc,.docx,.xls,.xlsx,.txt,.md,.csv,.json,.png,.jpg,.jpeg`
- UI：在 dropzone desc 增加简短提示（例：`支持 PDF / PPT / Word / 图片 / Markdown …`）

**验收**
- 一次性拖拽 3–5 个文件可全部进入上传队列，进度与错误可见；不再只上传第一个文件。

---

### P2（可选）可持续治理：动效/字体/性能告警收敛
#### 10) 动效：彻底替换范围内的 `transition-all` 与 `transition: all`
**改动文件（本次范围内出现点全改）**
- `teachdo-frontend/src/views/TeachingMaterialSelectionView.vue`（`transition-all` → `transition-shadow transition-transform` 或 `transition`)
- `teachdo-frontend/src/components/workspace/OutlineView.vue`
- `teachdo-frontend/src/components/workspace/PPTView.vue`
- `teachdo-frontend/src/components/workspace/ppt/PptTemplateSelector.vue`
- `teachdo-frontend/src/components/workspace/ppt/PptPreviewPanel.vue`
- `teachdo-frontend/src/components/workspace/KnowledgeBaseView.vue`
- `teachdo-frontend/src/components/common/ToastContainer.vue`（`transition: all` → `transition: opacity, transform`）

**验收**
- `rg -n "transition-all|transition:\\s*all" teachdo-frontend/src` 在非 `editor-runtime` 范围内无命中。

---

#### 11) 字体加载与色彩方案
**改动文件**
- `teachdo-frontend/index.html`
- `teachdo-frontend/src/style.css`

**具体改法**
- 把 `src/style.css` 中 Google Fonts `@import` 移到 `index.html` `<link rel="stylesheet">`，并加 `preconnect`。
- 增加 color-scheme：
  - `html { color-scheme: light; }`
  - `html.dark { color-scheme: dark; }`

**验收**
- 表单控件/滚动条在暗色模式更一致；字体加载更稳定（无阻塞式 @import）。

---

## 公共接口 / 类型变更（需要在计划中标明）
- i18n 新增 key（P0/P1 已列出，需中英双语补齐）
- 新增工具模块：`teachdo-frontend/src/utils/focusTrap.ts`
- `aiService.generateOutline` / `aiService.streamAipptSlides` 调用侧新增 `AbortController` 使用（对外 API 不变，仅新增可选参数透传）

---

## 验证与测试（自动化 + 手工验收）
### 自动化（每个阶段都要跑）
- `cd teachdo-frontend && npm run typecheck`
- `cd teachdo-frontend && npm run lint`
- `cd teachdo-frontend && npm run build`

### 手工验收场景（按主链路）
1) **TopBar**
- <lg 下逐个用键盘 Tab 聚焦导航按钮：读屏能读出名称；Enter 可触发导航；主题切换按钮有正确 aria-label。
2) **创建教学资料 Dialog**
- 打开后默认聚焦标题输入；Tab 循环不逃逸；Esc 关闭；焦点回到触发按钮。
3) **Outline**
- 生成→取消（direct 模式）回到空态；已有大纲时 regenerate→取消（compare 模式）保留旧版本并回到预览。
4) **PPT**
- 生成→取消：预览保留已生成页，banner 提示明确；可再次“重新生成”且状态正确。
5) **Assistant**
- Shift+Enter 换行；Enter 发送；生成中可 Stop；Stop 不弹 error toast。
6) **KB**
- 导出/删除按钮移动端易点；拖拽多文件全部上传；单个失败不影响其它；取消/关闭侧栏不破坏上传状态。

---

## 假设与默认（已按你选择定死）
- 不审查/不改 `teachdo-frontend/src/editor-runtime/**`（PPT 编辑器内部）。
- 工作台内不增加“教学资料快速切换”侧栏/下拉；仍以“返回列表”切换。
- 输出文档已整理为 `doc/dev/UI_UX_OPTIMIZATION_PLAN.md`；建议在 `doc/dev/PLAN.md` 增加一条链接（可选）。
- 默认不引入新的运行时依赖；如需 lint 强化（如 vue-a11y 插件）放在 P2 可选。
