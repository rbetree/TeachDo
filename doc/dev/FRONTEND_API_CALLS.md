# 前端 API 调用与封装（services 层）

本文件聚焦 **前端 `src/services/` 的 API 封装**：有哪些方法、分别请求哪些后端端点、开发/生产环境如何走 `/api` 代理。

不在本文档范围：
- **后端接口的完整请求/响应契约**：以 `doc/backend/backend_api_reference.md` 为准
- **功能/页面与 API 的宏观映射**：见 `doc/architecture/FEATURE_API_OVERVIEW.md`
- **前端整体架构与重构建议**：见 `doc/dev/FRONTEND_GUIDE.md`

---

## 1) Base URL 与代理（为什么前端统一用 `/api`）

前端在 `frontend/src/services/index.ts` 中固定：

- `SERVER_URL = '/api'`

开发环境下由 Vite 代理转发（`frontend/vite.config.ts`）：

- `http://127.0.0.1:5173/api/*` → 转发到 `http://127.0.0.1:6800/*`
- 并去掉路径前缀 `/api`（`rewrite: path.replace(/^\\/api/, '')`）

生产/Docker 环境通常由 Nginx 反向代理实现同样的「同源 + /api」策略，减少 CORS 成本（见 `doc/DockerDeploy.md`）。

---

## 2) `frontend/src/services/index.ts` 方法清单（方法 → 端点）

### 2.1 静态资源与模板

- `getTemplates()` → `GET /api/templates`
- `getFileData(filename)` → `GET /api/data/{filename}.json`
  - 注意：方法内部会自动拼接 `.json` 后缀

### 2.2 大纲生成（SSE）

- `AIPPT_Outline(payload)` → `POST /api/tools/aippt_outline`
  - `Content-Type: application/json`
  - `Accept: text/event-stream`
  - body 会带 `stream: true`
- `AIPPT_Outline_Unified({ content, file, language, userId })`（推荐）→ `POST /api/tools/aippt_outline_unified`
  - `multipart/form-data`
  - `Accept: text/event-stream`
- `AIPPT_Outline_From_File(file, user_id, language)`（legacy）→ `POST /api/tools/aippt_outline_from_file`
  - `multipart/form-data`
  - `Accept: text/event-stream`

备注：
- 当前前端页面（`frontend/src/views/Outline/index.vue`）使用的是 `AIPPT_Outline_Unified`；
- `AIPPT_Outline` / `AIPPT_Outline_From_File` 保留为兼容/备用调用方式，未在路由页面直接使用。

### 2.3 内容生成（SSE）

- `AIPPT_Content(payload)` → `POST /api/tools/aippt`
  - `Content-Type: application/json`
  - `Accept: text/event-stream`
  - body 会带 `stream: true`

### 2.4 其他

- `AIPPTByID({ id, language })` → `POST /api/tools/aippt_by_id`（实验接口，当前后端实现并非 SSE）
- `AI_Writing({ content, command })` → `POST /api/tools/ai_writing`（前端存在入口，但本仓库 `main_api` 未实现该端点；当前会返回 404）
- `getMockData(filename)` → 读取本地 `./mocks/{filename}.json`（仅用于前端 mock）
- `GET /api/proxy?url=...`：导出时代理外链资源（调用位置：`frontend/src/hooks/useExport.ts`）

---

## 3) SSE 流式响应：前端应该怎么读

对 `text/event-stream` 的端点，前端不能 `await response.json()`，而是需要：

1. `const reader = response.body.getReader()`
2. `TextDecoder` 解码 chunks
3. 按 `data: ...`（以及 `[DONE]`）协议逐段解析并更新 UI

项目里的典型实现位置：
- `frontend/src/hooks/useAIPPT.ts`
- `frontend/src/views/Outline/index.vue`

---

## 4) 常见问题（调用能通但生成失败）

- 现象：后端返回 `400`，提示 `The tool call is not supported`
- 含义：当前选择的模型/网关不支持工具调用（tool/function calling）
- 排查入口：优先检查根目录 `.env` 的模型配置（见 `doc/ai/CUSTOM_MODEL.md`）
