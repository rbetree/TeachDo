# AI2PPT 功能与 API / 页面映射（维护版）

> 文档版本：2.0  
> 最后更新：2026-02-10  
> 说明：本文件只保留「稳定不易过时」的功能/路由到 API 映射；详细请求/响应以 `../backend/backend_api_reference.md` 为准。

---

## 1. 系统组件与端口

- 前端：Vue 3 + Vite（默认端口 5173）
- `main_api`：6800（对前端唯一入口，提供 `/tools/*`、`/templates`、`/data/*`、`/proxy` 等）
- `simpleOutline`：10001（大纲 Agent，A2A 服务）
- `slide_agent`：10011（内容 Agent，A2A 服务）
- `personaldb`：9100（知识库：上传/解析/向量化/检索）

---

## 2. 核心流程（从主题/文档到可编辑 PPT）

1. 首页输入 `topic`（必填），可选上传文件
2. `/outline` 调用 `POST /tools/aippt_outline_unified`（SSE）获取 Markdown 大纲
3. `/ppt` 拉取模板列表：`GET /templates`，并按选中模板拉取模板 JSON：`GET /data/{template_id}.json`
4. `/ppt` 调用 `POST /tools/aippt`（SSE）获取逐页 Slide Schema（后端输出）
5. **前端模板引擎**将 Slide Schema 套用模板，生成可渲染的 Slide JSON，进入 `/editor` 编辑/导出
6. 导出如遇外链图片：使用 `GET /proxy?url=...` 走同源代理下载

---

## 3. 功能 → API 映射

> 前端统一使用 `/api` 代理访问后端（开发环境由 Vite 代理；Docker 环境由 Nginx 反向代理）。

### 3.1 大纲生成

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 统一接口生成大纲（推荐） | `/outline` | `POST /tools/aippt_outline_unified` | 主题必填，可选上传文件 → SSE Markdown |
| 主题生成大纲（兼容接口） | `/outline` | `POST /tools/aippt_outline` | 主题文本 → SSE Markdown |
| 文件/URL 生成大纲（legacy） | `/outline` | `POST /tools/aippt_outline_from_file` | file/url → SSE Markdown（如需“主题+文件”请用 unified） |

### 3.2 内容生成

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 根据大纲生成内容 | `/ppt` | `POST /tools/aippt` | 大纲 → SSE Slide Schema（模板映射在前端完成） |
| 根据 ID 生成内容（实验） | `/app/:id?` | `POST /tools/aippt_by_id` | 实验接口，当前未完成；字段名为 `id` |

### 3.3 模板与静态资源

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 获取模板列表 | `/ppt` | `GET /templates` | 返回模板元数据（`name/id/cover`） |
| 获取模板 JSON/封面等 | 多处 | `GET /data/{filename}` | 典型：`/data/{id}.json`、`/data/{id}.jpg` |

### 3.4 知识库

| 功能 | 服务 | API | 说明 |
|---|---|---|---|
| 上传并向量化 | personaldb | `POST /upload/` | 返回 `id(fileId)` 与 `markdown_content` 等 |
| 语义检索 | personaldb | `POST /search` | 以 `userId + query` 检索 |
| 纯文本向量化 | personaldb | `POST /vectorize/text` | 对任意文本向量化并落库 |
| 获取文件列表 | personaldb | `GET /files/{user_id}` | 返回文件列表 |
| 获取文件列表（代理） | main_api | `GET /files/{user_id}` | 代理到 personaldb |

### 3.5 工具/运维

| 功能 | 服务 | API | 说明 |
|---|---|---|---|
| 代理外部资源 | main_api | `GET /proxy` | 代理图片等资源，解决跨域/导出问题 |
| 健康检查 | main_api | `GET /healthz` | 返回 `{"ok": true}` |

---

## 4. 路由 → API（当前前端实现概览）

- `/` Home：收集主题/文件等输入，跳转到 `/outline`
- `/outline` Outline：调用 `POST /tools/aippt_outline_unified` 流式生成大纲
- `/ppt` PPT：`GET /templates`、`GET /data/{id}.json`、`POST /tools/aippt` 流式生成内容
- `/editor` Editor：纯前端编辑/导出（不新增后端 API）
- `/app/:id?` APP：调用 `POST /tools/aippt_by_id`（实验接口）

---

## 5. 进一步阅读

- API 参考（维护版）：`../backend/backend_api_reference.md`
- 环境变量：`../dev/ENV_GUIDE.md`
- Docker 部署：`../DockerDeploy.md`
- 模板制作与结构：`../Template.md`、`../PPT_Structure.md`
- 抓包/历史记录（可能过时）：`../legacy/API_OUTLINE.md`、`../legacy/API_CONTENT.md`、`../legacy/API_TEMPLATE.md`、`../legacy/API_IMAGE.md`
