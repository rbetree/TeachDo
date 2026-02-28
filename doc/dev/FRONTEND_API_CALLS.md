# 前端 API 调用与封装（services 层）

本文件聚焦 **TeachDo 前端 `frontend/src/services/aiService.ts` 的 API 封装**：有哪些方法、分别请求哪些后端端点、开发/生产环境如何走 `/api` 代理。

不在本文档范围：
- **后端接口的完整请求/响应契约**：以 `doc/backend/backend_api_reference.md` 为准
- **功能/页面与 API 的宏观映射**：见 `doc/architecture/FEATURE_API_OVERVIEW.md`
- **前端整体架构与重构建议**：见 `doc/dev/FRONTEND_GUIDE.md`

---

## 1) Base URL 与代理（为什么前端统一用 `/api`）

前端在 `frontend/src/services/apiClient.ts` 中固定：

- `BASE_API = '/api'`

开发环境下由 Vite 代理转发（`frontend/vite.config.ts`）：

- `http://127.0.0.1:5174/api/*` → 转发到 `http://127.0.0.1:6800/*`
- 并去掉路径前缀 `/api`（`rewrite: path.replace(/^\\/api/, '')`）

生产/Docker 环境通常由 Nginx 反向代理实现同样的「同源 + /api」策略，减少 CORS 成本（见 `doc/DockerDeploy.md`）。

---

## 2) `frontend/src/services/aiService.ts` 方法清单（方法 → 端点）

### 2.1 静态资源与模板

- `getTemplates()` → `GET /api/templates`
- `getTemplateFileData(templateId)` → `GET /api/data/{templateId}.json`

### 2.2 大纲生成（SSE）

- `generateOutline(material, onStream?)` → `POST /api/tools/aippt_outline_unified`
  - `multipart/form-data`
  - `Accept: text/event-stream`
  - 备注：会透传 `kb_file_ids`（来自 `TeachingMaterial.kbFileIds`）

### 2.3 教案生成/导出

- `streamLessonPlan({ material, templateId?, onEvent? })` → `POST /api/tools/lesson_plan`（SSE）
  - `Content-Type: application/json`
  - `Accept: text/event-stream`
- `getLessonTemplates()` → `GET /api/lesson/templates`
- `exportLessonDocx({ lessonPlan, style, templateId?, persist?, userId?, materialId? })` → `POST /api/lesson/export/docx`
  - `Content-Type: application/json`
  - 响应：二进制附件（DOCX）；可读取 `x-teachdo-artifact-id`（若后端启用持久化）

### 2.4 PPT 内容生成（SSE）

- `streamAipptSlides(payload)` → `POST /api/tools/aippt`
  - `Content-Type: application/json`
  - `Accept: text/event-stream`
  - 备注：支持透传 `kb_folder_ids` / `kb_file_ids`

### 2.5 助教问答（SSE）

- `streamAssistantReply({ messages, material?, kbFileIds?, onDelta? })` → `POST /api/tools/assistant_chat`
  - `Content-Type: application/json`
  - `Accept: text/event-stream`

### 2.6 知识库（KB，BFF）

- `kbUpload({ userId, file, folderId? })` → `POST /api/kb/upload`（`multipart/form-data`）
- `kbListFiles({ userId, folderId? })` → `GET /api/kb/files/{userId}`（可选 query：`folder_id`）
- `kbDeleteFile({ userId, fileId })` → `DELETE /api/kb/files/{userId}/{fileId}`
- `kbExportFile({ userId, fileId })` → `GET /api/kb/files/{userId}/{fileId}/export`（附件下载）
- `vectorizeTextToKb({ userId, fileId, folderId, fileName, content })` → `POST /api/kb/vectorize/text`

### 2.7 导出产物（Artifacts）

- `listArtifacts({ userId, materialId })` → `GET /api/artifacts/{userId}/{materialId}`
- `uploadArtifact({ userId, materialId, kind, file })` → `POST /api/artifacts/{userId}/{materialId}`（`multipart/form-data`）
- `downloadArtifact({ userId, materialId, artifactId })` → `GET /api/artifacts/{userId}/{materialId}/{artifactId}`（附件下载）
- `deleteArtifact({ userId, materialId, artifactId })` → `DELETE /api/artifacts/{userId}/{materialId}/{artifactId}`

---

## 3) SSE 流式响应：前端应该怎么读

对 `text/event-stream` 的端点，前端不能 `await response.json()`，而是需要：

1. `const reader = response.body.getReader()`
2. `TextDecoder` 解码 chunks
3. 按 `data: ...`（以及 `[DONE]`）协议逐段解析并更新 UI

项目里的典型实现位置：
- `frontend/src/utils/sse.ts`
- `frontend/src/services/ai/*.ts`（各领域服务内读流并上抛事件/增量）

---

## 4) 常见问题（调用能通但生成失败）

- 现象：后端返回 `400`，提示 `The tool call is not supported`
- 含义：当前选择的模型/网关不支持工具调用（tool/function calling）
- 排查入口：优先检查根目录 `.env` 的模型配置（见 `doc/ai/CUSTOM_MODEL.md`）
