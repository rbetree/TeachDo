# TeachDo 前端技术指南（维护版）

> 最后更新：2026-02-28  
> 文档边界：本文聚焦 TeachDo 前端工程的结构、路由、状态与对后端的调用方式；接口字段/示例以 `doc/backend/backend_api_reference.md` 为准；功能/路由到 API 的宏观映射见 `doc/architecture/FEATURE_API_OVERVIEW.md`。

## 1. 关键入口与目录结构

前端代码位于 `frontend/`，高频入口如下：

- 应用入口：`frontend/src/main.ts`
- 路由配置：`frontend/src/router/index.ts`
- 全局状态（教学资料/KB/主题语言）：`frontend/src/stores/appStore.ts`
- Service 统一出口：`frontend/src/services/aiService.ts`
  - 领域拆分：`frontend/src/services/ai/*`（outline/lesson/ppt/kb/assistant/artifacts）
- SSE 解析：`frontend/src/utils/sse.ts`
- 视图入口：
  - 教学资料选择页：`frontend/src/views/TeachingMaterialSelectionView.vue`
  - 工作台容器：`frontend/src/views/TeachingMaterialWorkspaceView.vue`
  - PPT 编辑器页：`frontend/src/views/PPTEditorView.vue`
- 编辑器运行时：`frontend/src/editor-runtime/**`（仅编辑器路由按需加载）

## 2. 路由与页面职责

TeachDo 前端的路由结构以“教学资料（TeachingMaterial）”为核心：

- `/`：教学资料列表（选择/创建），不依赖后端
- `/material/:materialId/:tab`：工作台（tab ∈ `outline/lesson/ppt/assistant`）
  - `outline`：大纲生成/编辑，产物可入库（KB）
  - `lesson`：教案生成/导出，产物可入库（KB + artifacts）
  - `ppt`：PPT 生成与预览，产物可入库（KB）
  - `assistant`：助教对话（SSE 流式）
- `/material/:materialId/ppt/editor`：独立 PPT 编辑器（导出 PPTX，并可上传到 artifacts）

路由守卫会校验 `materialId` 是否存在，不存在时回退到 `/`：见 `frontend/src/router/index.ts`。

## 3. 状态与持久化（TeachDo 约定）

- `appStore` 会在 localStorage 持久化“轻量字段”（列表/主题/语言等），并使用 IndexedDB 持久化“大对象”（outline/lesson/presentation/editorDocument 等）。实现见：
  - `frontend/src/stores/appStore.ts`
  - `frontend/src/utils/appStoreIdb.ts`
- 侧栏 UI 状态（展开/收起等）由 `workspaceUiStore` 管理：`frontend/src/stores/workspaceUiStore.ts`

## 4. 与后端交互（/api + services 层）

### 4.1 `/api` 代理

前端统一使用相对路径访问后端（同源 + `/api`）：

- 开发：Vite proxy（`frontend/vite.config.ts`）将 `/api/*` 转发到 `main_api`
- Docker/生产：Nginx 反代实现同样策略（见 `doc/DockerDeploy.md`）

### 4.2 aiService（统一出口）

前端调用后端的主要入口是 `frontend/src/services/aiService.ts`，按领域拆分：

- Outline：`POST /tools/aippt_outline_unified`（SSE）
- Lesson：`POST /tools/lesson_plan`（SSE）、`POST /lesson/export/docx`、`GET /lesson/templates`
- PPT：`POST /tools/aippt`（SSE）、`GET /templates`、`GET /data/{id}.json`
- Assistant：`POST /tools/assistant_chat`（SSE）
- KB（BFF）：`/kb/*`（upload/list/export/vectorize/delete）
- Artifacts：`/artifacts/*`（list/upload/download/delete）

详细方法清单见：`doc/dev/FRONTEND_API_CALLS.md`。

## 5. KB 文件选择与上下文注入（高频）

### 5.1 `TeachingMaterial.kbFileIds` 的语义

`TeachingMaterial.kbFileIds` 表示“当前教学资料被用户勾选、用于生成/问答的 KB 文件集合”。该集合会透传给：

- 大纲（`/tools/aippt_outline_unified`）
- 教案（`/tools/lesson_plan`）
- PPT（`/tools/aippt`）
- 助教（`/tools/assistant_chat`）

### 5.2 `file_id` 前缀约定（前后端共识）

- `upload:`：上传素材（RAG 检索，只注入片段）
- `gen:`：生成产物（全文注入，不经检索）
- `full:`：全文上传（全文注入，不经检索）

前端判定见 `frontend/src/utils/kbFileId.ts`，后端拆分规则见 `doc/architecture/PROJECT_ARCHITECTURE.md`。

## 6. 编辑器与导出（Artifacts）

- 编辑器导出 PPTX：浏览器端生成并下载；若存在 `teachdoUserId/materialId`，会额外上传到 artifacts 以便在工作台「课程产出」再次下载（见 `frontend/src/editor-runtime/hooks/useExport.ts`）。
- 教案导出 DOCX：`POST /lesson/export/docx` 返回附件；可选 `persist=true` 自动入库到 artifacts（见 `frontend/src/services/ai/lessonService.ts`）。

## 7. 开发命令（常用）

- 安装依赖：`npm i`
- 本地开发：`npm run dev`
- 发布前校验：`npm run typecheck && npm run lint && npm run build`

更完整的本地开发规范见：`frontend/teachdo_local_dev.md`。
