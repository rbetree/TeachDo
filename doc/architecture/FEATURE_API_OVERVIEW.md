# TeachDo 功能与 API / 页面映射（维护版）

> 文档版本：3.1  
> 最后更新：2026-02-28  
> 说明：本文件只保留「稳定不易过时」的功能/路由到 API 映射；详细请求/响应（字段/示例）以 `doc/backend/backend_api_reference.md` 为准。

---

## 1. 系统组件与端口

- 前端（TeachDo）：Vue 3 + Vite（默认端口 5174）
- `main_api`：6800（对前端唯一入口，提供 `/tools/*`、`/lesson/*`、`/kb/*`、`/artifacts/*`、`/templates`、`/data/*`、`/proxy` 等）
- `simpleOutline`：10001（大纲 Agent，A2A 服务）
- `slide_agent`：10011（内容 Agent，A2A 服务）
- `personaldb`：9100（知识库：上传/解析/向量化/检索）

---

## 2. 核心流程（从教学资料到可编辑 PPT）

1. 进入首页（`/`）：选择/创建教学资料（TeachingMaterial）
2. 大纲（`/material/:materialId/outline`）：`POST /tools/outline`（SSE；兼容别名 `/tools/aippt_outline_unified`）生成 Markdown → 保存到 `TeachingMaterial.outlineContent` → `POST /kb/vectorize/text` 入库（产物）
3. 教案（`/material/:materialId/lesson`）：`POST /tools/lesson_plan`（SSE）生成结构化教案 → 保存到 `TeachingMaterial.lessonPlan` → `POST /kb/vectorize/text` 入库（产物）
4. PPT（`/material/:materialId/ppt`）：`GET /templates` + `GET /data/{templateId}.json` → `POST /tools/ppt`（SSE；兼容别名 `/tools/aippt`）生成逐页 Slide Schema → 保存到 `TeachingMaterial.presentation/editorDocument` → `POST /kb/vectorize/text` 入库（产物）
5. 独立编辑器（`/material/:materialId/ppt/editor`）：纯前端编辑/导出；导出 PPTX 后可调用 `POST /artifacts/{user_id}/{material_id}` 持久化保存（用于「课程产出」二次下载）
6. 助教（`/material/:materialId/assistant`）：`POST /tools/assistant_chat`（SSE）基于当前教学资料 + 选中文件上下文做问答

> 关键约定：前端会把用户当前选中的 `kb_file_ids`（`TeachingMaterial.kbFileIds`）透传给大纲/教案/PPT/助教端点，`main_api` 会按 `file_id` 前缀拆分为：
> - `gen:` / `full:` → 全文注入（不经检索）
> - 其他（典型 `upload:`）→ 仅用于 personaldb `/search` 检索片段（RAG）

---

## 3. 功能 → API 映射

> 前端统一使用 `/api` 代理访问后端（开发环境由 Vite 代理；Docker/生产环境由 Nginx 反向代理）。

### 3.1 大纲生成

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 统一接口生成大纲（推荐） | `/material/:materialId/outline` | `POST /tools/outline` | SSE Markdown；兼容别名：`/tools/aippt_outline_unified`；支持透传 `kb_file_ids` 增强 |
| 主题生成大纲（兼容接口） | 同上 | `POST /tools/aippt_outline` | legacy/兼容接口 |
| 文件/URL 生成大纲（legacy） | 同上 | `POST /tools/outline_from_file` | legacy/兼容接口（兼容别名：`/tools/aippt_outline_from_file`） |

### 3.2 教案生成与导出

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 生成教案（SSE） | `/material/:materialId/lesson` | `POST /tools/lesson_plan` | SSE JSON events（section/final）；支持 `kb_file_ids` |
| 教案模板列表 | 同上 | `GET /lesson/templates` | 后端不可用时前端有 mock 兜底 |
| 导出教案为 DOCX | 同上 | `POST /lesson/export/docx` | 以附件下载返回；可选 `persist=true` 自动入库 artifacts |

### 3.3 PPT 内容生成

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 根据大纲生成内容（SSE） | `/material/:materialId/ppt` | `POST /tools/ppt` | SSE Slide Schema；兼容别名：`/tools/aippt`；支持 `kb_folder_ids/kb_file_ids` |

### 3.4 助教问答

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 助教对话（SSE） | `/material/:materialId/assistant` | `POST /tools/assistant_chat` | SSE 文本 delta；支持 `kb_file_ids` |

### 3.5 模板与静态资源

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 获取模板列表 | `/material/:materialId/ppt` | `GET /templates` | 返回模板元数据（`name/id/cover`） |
| 获取模板 JSON/封面等 | 多处 | `GET /data/{filename}` | 典型：`/data/{id}.json`、`/data/{id}.jpg` |

### 3.6 知识库（KB，BFF）

| 功能 | API（main_api） | 说明 |
|---|---|---|
| 上传文件并向量化 | `POST /kb/upload` | `folder_id`：0=上传素材（RAG），1=生成产物（`gen:`），2=全文上传（`full:`） |
| 列出文件 | `GET /kb/files/{user_id}` | `user_id` 前端默认传 `default_user`；可选 `folder_id` 过滤 |
| 导出文件内容 | `GET /kb/files/{user_id}/{file_id}/export` | 以附件下载返回（Markdown/纯文本） |
| 纯文本入库（产物入库） | `POST /kb/vectorize/text` | 写入 personaldb 索引；支持 `created_at/source_*` 元数据 |
| 删除文件向量 | `DELETE /kb/files/{user_id}/{file_id}` | 删除后避免检索命中旧数据 |

### 3.7 导出产物（Artifacts）

| 功能 | API（main_api） | 说明 |
|---|---|---|
| 列表 | `GET /artifacts/{user_id}/{material_id}` | 返回 `pptx/docx` 元数据数组 |
| 上传 | `POST /artifacts/{user_id}/{material_id}` | `multipart/form-data`：`kind` + `file` |
| 下载 | `GET /artifacts/{user_id}/{material_id}/{artifact_id}` | 以附件下载返回 |
| 删除 | `DELETE /artifacts/{user_id}/{material_id}/{artifact_id}` | 删除落盘文件与索引 |

### 3.8 工具/运维

| 功能 | API（main_api） | 说明 |
|---|---|---|
| 代理外部资源 | `GET /proxy` | 代理图片等资源，解决跨域/导出问题 |
| 健康检查 | `GET /healthz` | 返回 `{"ok": true}` |

---

## 4. 路由 → API（前端实现概览）

- `/`：教学资料选择页（不调用后端）
- `/material/:materialId/:tab`（工作台，`tab` ∈ `outline/lesson/ppt/assistant`）：
  - `outline`：`POST /tools/outline`（SSE）+ `POST /kb/vectorize/text`（产物入库）
  - `lesson`：`POST /tools/lesson_plan`（SSE）+ `POST /lesson/export/docx`（导出）+ `POST /kb/vectorize/text`（产物入库）
  - `ppt`：`GET /templates`、`GET /data/{id}.json`、`POST /tools/ppt`（SSE）+ `POST /kb/vectorize/text`（产物入库）
  - `assistant`：`POST /tools/assistant_chat`（SSE）
  - 侧栏（参考资料/课程产出）：按需调用 `POST /kb/upload`、`GET /kb/files/*`、`DELETE /kb/files/*`、`GET /kb/files/*/export`、`GET/POST /artifacts/*`
- `/material/:materialId/ppt/editor`：编辑器路由；导出 PPTX 后可调用 `POST /artifacts/{user_id}/{material_id}` 入库

---

## 5. 进一步阅读

- API 参考（以代码为准）：`doc/backend/backend_api_reference.md`
- 环境变量：`doc/dev/ENV_GUIDE.md`
- 前端 API 映射：`doc/dev/FRONTEND_API_CALLS.md`
- Docker 部署：`doc/DockerDeploy.md`
- 模板制作与结构：`doc/Template.md`、`doc/PPT_Structure.md`
- 开发计划（当前）：`doc/dev/PLAN.md`
