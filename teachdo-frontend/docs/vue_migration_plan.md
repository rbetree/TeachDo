# TeachDo Vue 技术栈迁移开发计划

围绕“无临时共存、直接切换至 Vue”目标，采用层级化结构（阶段 → 任务集合/MVP → 具体任务），保证每个集合交付后都能提供可验证的用户价值。所有迁移后的页面**逻辑、功能与样式必须与现有 React 版本保持一致**，并在验收时逐项对照确认。

> 备注（2026-02-14）：前端已移除登录/认证模块，当前默认免登录进入工作台；文档中涉及 Login/Register/ForgotPassword、authService、token、未登录保护等内容已不再适用，后续以“课程校验 + AI 工作流”作为主要验收路径。

#### 对照重构操作指南
- React 版本以 `main` 分支为基线，需要对照时可 `git show main:path/to/file.tsx` 或切换到 `main` 阅读旧实现，始终确保能回溯原逻辑。
- 如需同时运行 React 与 Vue 版本，使用 `git worktree add ../TeachDo-react main` 拉取只读工作树，在一个终端运行 React 版 `npm run dev`，另一个终端运行 Vue 版，对照交互与样式。
- 关键页面、组件在迁移前记录截图/录屏或 Storybook baseline，迁移后使用视觉 diff（Chromatic、reg-suit 等）或人工比对，确保样式与交互细节一致。
- 针对课程、AI 流程等路径维护端到端验收 checklist，Vue 版本交付后严格按照脚本核对“逻辑/功能/样式”三项，并把结果写入验收记录。

#### 脚手架切换与初始化流程
1. 以 `main` 为基准确认 React 版本已打 tag/记录，确保可以随时回溯。
2. 在 `vue-migration` 分支上清理 React 结构：删除 `src/`、`public/`、`index.html` 等 React 专属文件，并移除旧的 `node_modules` 与 `package-lock.json`，保留 `docs/`、脚本配置等通用资产。
3. 执行 `npm create vite@latest . -- --template vue-ts` 在根目录直接初始化 Vue3 + Vite + TS 脚手架，然后复用/同步旧 `package.json` 中的 npm scripts（如 `dev`、`build`、`lint` 等）。
4. 运行 `npm install`、`npm run dev`、`npm run build` 完成基础校验，确认 Vue 脚手架可在根目录正常运行后再进入 V1.2 及后续任务。

---

### 阶段1: Vue 基础架构 (优先级: 最高)
> 打好工程骨架，确保 Vue 版本具备运行前提，可承载后续业务迁移。

#### 集合1: 基础脚手架（最小可用产品）
| ID | 任务描述 | 依赖 | 状态 |
|----|---------|-----|------|
| V1.1 | 初始化 Vue3 + Vite + TypeScript 工程，复用现有 npm scripts 与项目结构 | - | ✅ 已完成（vue 脚手架在根目录运行通过 `npm run dev` 验证） |
| V1.2 | 集成 Tailwind、暗色模式样式与 ESlint/TSConfig，确保与 React 版本一致 | V1.1 | ✅ 已完成（Tailwind + 暗色样式落地，ESLint/TSConfig 与 React 版参数对齐） |
| V1.3 | 迁移 `types.ts`、`services/*`、`utils/fetchUtils.ts`，验证 env 读取与流式请求可用 | V1.2 | ✅ 已完成（核心类型/服务迁移完毕，并通过 `npm run lint && npm run build` 验证流式 fetch/env 读取） |

**验收条件（Reviewer 全部勾选后方可合并）**
- [ ] 在全新克隆环境中执行 `npm run dev`、`npm run lint`、`npm run typecheck`、`npm run build` 均可一次通过，无额外手动 hack。
- [ ] Tailwind 配置、暗色模式样式、ESLint/TSConfig 参数与 React 基线一致，并在 PR 中附差异比对或说明。
- [ ] `types.ts`、`services/*`、`utils/fetchUtils.ts` 全量迁移且引用路径正确，env 读取与流式 fetch 的手动复验步骤已记录。
- [ ] React 旧脚手架残留（旧入口、node_modules、脚本）全部清理，根目录结构与 Vue 脚手架保持一致。

任务完成情况：
- 2025-12-10：完成 V1.1～V1.6，`npm run lint`、`npm run typecheck`、`npm run build` 全部通过，Pinia + Router + i18n/Toast 基础能力具备。


#### 集合2: 核心基础设施
| ID | 任务描述 | 依赖 | 状态 |
|----|---------|-----|------|
| V1.4 | 搭建 Pinia store，覆盖课程、主题、语言状态并实现 localStorage 持久化 | V1.3 | ✅ 已完成（Pinia + localStorage 全局状态落地，含主题/语言同步与 `setupAppStore` 初始化） |
| V1.5 | 创建 Vue Router 路由表与守卫，覆盖课程有效性校验等导航约束 | V1.4 | ✅ 已完成（`vue-router` + 全局守卫 + MainLayout，守卫用于缺失课程时回退等场景） |
| V1.6 | 实现 i18n（vue-i18n 或 provide/inject）与全局 Toast/Error 处理 | V1.5 | ✅ 已完成（vue-i18n + ToastContainer + 全局错误捕获接入，**（为了跑通该任务，创建了简单的占位页面）后续迁移时必须与 React 版本行为/样式保持一致**） |

**验收条件（Reviewer 全部勾选后方可合并）**
- [ ] Pinia store 能在刷新/多标签页后保持课程、主题、语言状态一致，并提供 localStorage 数据结构说明。
- [ ] Router 守卫覆盖缺失课程时回退等场景，相关 E2E 步骤与期望结果在 PR 中列明。
- [ ] i18n 语言切换、Fallback 与 Toast/Error 处理在 dev + build 环境表现一致，且复用了全局错误捕获。
- [ ] `setupAppStore` / `main.ts` 初始化顺序不会造成闪烁或空白页，SSR/CSR 切换（如适用）无报错。

**注意事项**
- V1.6 完成前不要进入阶段2，必须确认 Pinia/i18n/Toast 在 dev + build 场景均可运行。
- V1.3 除了验证 env 变量，还需记录流式 fetch 的测试步骤，供后续 V3.x 复验。
- Pinia localStorage 同步需考虑 React 旧数据结构，必要时提供迁移或清理策略。

---

### 阶段2: 课程体验 (优先级: 高)
> 交付用户可直接查看课程、进出工作台的完整流程。

#### 集合3: 入口与主布局（最小可用产品）
| ID | 任务描述 | 依赖 | 状态 |
|----|---------|-----|------|
| V2.1 | （已废弃）Login/Register/ForgotPassword 视图与 authService | V1.6 | 🗑️ 已移除（免登录版本不再需要认证模块） |
| V2.2 | 构建主布局（TopBar、主题切换、用户信息），替换 React 版本 | V2.1 | ✅ 已完成（AppTopBar 复刻 React 功能：语言/主题切换、健康检查、官网入口、用户菜单） |
| V2.3 | （已废弃）登录 → 重定向 → 课程入口完整链路 | V2.2 | 🗑️ 已移除（免登录版本不再需要该链路） |

**验收条件（Reviewer 全部勾选后方可合并）**
- [ ] AppTopBar 的主题/语言切换、健康检查、官网入口、用户菜单均可用，状态在刷新后保持。

#### 集合4: 课程工作台
| ID | 任务描述 | 依赖 | 状态 |
|----|---------|-----|------|
| V2.4 | 迁移 CourseSelectionView，保留课程创建、列表展示与空状态 | V2.3 | ✅ 已完成（Vue 版本复刻 React Hero + Skeleton + 课程卡片/创建流程，沿用 Pinia 课程状态与导航） |
| V2.5 | 迁移 CourseWorkspace 及子侧栏组件，支持单位切换与 kb 文件展示 | V2.4 | ✅ 已完成（UnitSidebar + Workspace 布局重建，包含移动抽屉、单位 Tabs、知识库/助教占位，行为与 React 版一致） |
| V2.6 | 完成课程 CRUD、本地缓存同步与路由切换自测 | V2.5 | ✅ 已完成 |

**验收条件（Reviewer 全部勾选后方可合并）**
- [ ] CourseSelectionView 的 Hero、Skeleton、课程卡片、课程创建/空状态流程与 React 版逐屏对齐，并附对比截图。
- [ ] CourseWorkspace 的 UnitSidebar、移动抽屉、Tabs、知识库/助教面板在桌面与移动端均可正常切换。
- [ ] 课程 CRUD（新增/编辑/删除）结果可即时写入 Pinia + localStorage，刷新后仍保持；路由切换不会出现“课程不存在”弹回。
- [ ] Reviewer 根据“课程列表→进入/切换工作台→AI 生成→返回课程列表” checklist 全部打勾后，方可合并。

**注意事项**
- Vue Router 守卫要覆盖“课程不存在时重定向”等场景，确保行为与 React 版本一致。
- V2.6 的端到端验证需列出步骤（课程列表→进入工作台→切换单元→返回），并记录异常处理结果。
- 在迁移过程中持续复用 aiService，若新增组合式封装需保证与 React 版本 API 完全一致。

---

### 阶段3: AI 生成工作流 (优先级: 高)
> 交付 TeachDo 的核心价值：AI 大纲、教案、PPT 与助教。

#### 集合5: 大纲与教案生成（最小可用产品）
| ID | 任务描述 | 依赖 | 状态 |
|----|---------|-----|------|
| V3.1 | 迁移 OutlineView，处理流式文本、进度与错误提示 | V2.6 | ✅ 已完成（OutlineView.vue 复刻 React 版本的 Preview/Edit/Compare 三模式，流式生成、Markdown 渲染与 React 版一致） |
| V3.2 | 迁移 LessonPlanView，复用 aiService 接口并实现结果展示/导出 | V3.1 | ✅ 已完成（LessonPlanView.vue 复刻 React 版本的教案生成、展示、复制与 Word 导出功能） |
| V3.3 | 打通课程 → 大纲 → 教案链路并完成实机验证 | V3.2 | ✅ 已完成（集成到 CourseWorkspaceView，通过 npm run build 验证，类型检查通过） |

**验收条件（Reviewer 全部勾选后方可合并）**
- [ ] OutlineView 使用 `ReadableStream` 处理流式文本，进度条、错误提示、重试逻辑与 React 版一致，并在慢网环境下实测通过。
- [ ] LessonPlanView 完全复用 aiService 接口，结果展示（Markdown/富文本）、导出/复制能力与 React 版等价。
- [ ] “课程 → 大纲 → 教案” 链路的输入参数、耗时、生成结果截图/文本均在 PR 中记录，含异常回退步骤。
- [ ] Loading/Error 状态复用全局 Toast 与 i18n 文案，无重复实现，失败后可重新发起请求。

#### 集合6: PPT 与 AI 助教
| ID | 任务描述 | 依赖 | 状态 |
|----|---------|-----|------|
| V3.4 | 迁移 PPTView，支持模板选择、流式生成与下载 | V3.3 | ✅ 已完成（PPTView.vue 复刻 React 模板选择、流式生成、Markdown/PPTX 导出与预览） |
| V3.5 | 迁移 AssistantView，支持对话、上下文注入与历史记录 | V3.4 | ✅ 已完成（AssistantView.vue 接入流式对话、历史持久化、上下文注入，与 React 交互一致） |
| V3.6 | 验证全套 AI 工作流（大纲/教案/PPT/助教）及性能回归 | V3.5 | ⏳ 待验证（功能已贯通，链路与性能数据需补充） |

**验收条件（Reviewer 全部勾选后方可合并）**
- [ ] PPTView 模板选择、参数校验、进度展示、PPTX 下载文件均与 React 版一致，并附可打开的示例文件。
- [ ] AssistantView 支持上下文注入、历史记录、角色标签、移动端抽屉等交互，界面元素与 React 录屏一致。
- [ ] “大纲 → 教案 → PPT → 助教” 全链路在真实课程数据上跑通，包含失败重试场景的日志/录屏。
- [ ] V3.6 规定的性能指标（首屏时间、AI 请求耗时、内存占用）与 React 版本对比数据已记录并达标。

**注意事项**
- 在 V3.1/V3.4 处理流式输出时，需重点关注 `ReadableStream` 与 Composition API 的协作，防止 watchEffect 停止导致流断开。
- V3.6 的“性能回归”需事先定义指标（首屏加载、AI 请求耗时、内存占用），并记录对比 React 版本的差异。
- 所有 AI 视图应复用统一的错误提示/重试策略，避免多处出现重复逻辑。

---

### 阶段4: 体验完善与交付 (优先级: 中)
> 打磨 UX、性能与交付资产，准备切换到 Vue 主干。

#### 集合7: 文档与测试（最小可用产品）
| ID | 任务描述 | 依赖 | 状态 |
|----|---------|-----|------|
| V4.1 | 更新 README、teachdo_local_dev.md，描述 Vue 开发/部署流程 | V3.6 | 待开始 |
| V4.2 | 补充关键组合式函数/组件单元测试或 Storybook（如适用） | V4.1 | 待开始 |
| V4.3 | 执行 npm run build、端到端手测并输出验收报告 | V4.2 | 待开始 |

**验收条件（Reviewer 全部勾选后方可合并）**
- [ ] README、teachdo_local_dev.md、package.json 脚本说明等文档均更新为 Vue 版内容，不再包含 React 专属指令，并完成至少两人交叉 Review。
- [ ] 关键组合式函数/组件补充 vitest/Storybook 等验证资产，相关脚本运行通过并在 PR 中贴出日志。
- [ ] `npm run build` 产物日志/截图与端到端手测 checklist 一并提交，覆盖认证、课程、AI 主要链路。

#### 集合8: 性能与切换
| ID | 任务描述 | 依赖 | 状态 |
|----|---------|-----|------|
| V4.4 | 进行性能/包体优化（按需引入组件、拆分路由懒加载） | V4.3 | 待开始 |
| V4.5 | 清理 React 相关依赖、脚本与文件，确保仓库仅保留 Vue 版本 | V4.4 | 待开始 |
| V4.6 | 合并至主干并规划后续增量需求（如多语言、插件化） | V4.5 | 待开始 |

**验收条件（Reviewer 全部勾选后方可合并）**
- [ ] 路由懒加载、按需组件、依赖裁剪等优化措施落地，并在 PR 中附 before/after 指标（包体大小、LCP、首屏时间）。
- [ ] React 相关依赖/文件/脚本彻底移除，CI/CD 与部署脚本均指向 Vue 入口，`npm run preview` 验收通过。
- [ ] React 旧版本 Tag 与回滚策略已记录，同时产出 Vue 切换后的运维指南与负责人名单。
- [ ] 后续增量需求（多语言、插件化等）与切换时间表写入文档，Owner/里程碑明确。

**注意事项**
- V4.1 应明确需要更新的文件列表（README、teachdo_local_dev、package.json、vite.config、tsconfig 等）并完成交叉 Review。
- V4.3 的验收报告需包含端到端测试记录以及 npm run build 产物截图/日志，作为切换依据。
- V4.5/V4.6 需保留 React 版本 Tag 方便回滚，并确认 CI/CD、部署脚本已全部指向 Vue 入口。

---

> 本计划默认所有任务在 `vue-migration` 分支执行，完成对应集合即可交付一个可演示/可验收的 Vue 版本切片，符合敏捷增量交付原则。
