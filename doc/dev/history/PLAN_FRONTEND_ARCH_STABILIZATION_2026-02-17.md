# TeachDo 阶段 I：前端架构收敛与稳定性（P0）

> 状态：DONE（2026-02-17）
> 来源：从 `doc/dev/PLAN.md` 拆出归档（避免入口计划过长）
> 当前入口：`doc/dev/PLAN.md`

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
  - 背景：当前 `frontend/src/main.ts` 全局 `app.use(EditorIconPlugin/EditorDirectivePlugin)`，且工作台 `frontend/src/components/workspace/PPTView.vue` 直接 import `@editor/*`，会把 editor-runtime 依赖链带进首屏/工作台。
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
