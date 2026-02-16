# 后端 API 参考（以当前实现为准）

> 本文档以源码为准：
> - `backend/main_api/main.py`
> - `backend/personaldb/main.py`
>
> 说明：前端通常通过 `/api/` 代理访问 `main_api`，因此文档会同时给出「直连后端」与「通过前端代理」两种写法。

---

## 0. Base URL

### main_api（FastAPI 网关）

- 直连后端：`http://127.0.0.1:6800`
- 通过前端代理（Vite/Nginx）：`http://127.0.0.1:5174/api`（或同域 `/api`）

### personaldb（知识库）

- 直连：`http://127.0.0.1:9100`

---

## 1. main_api（端口 6800）

### 1.1 `POST /tools/aippt_outline`（主题生成大纲，SSE）

用途：输入主题，流式返回 Markdown 大纲（SSE）。

请求（JSON）：

```json
{
  "content": "2025 科技前沿动态",
  "language": "chinese",
  "model": "任意字符串（兼容字段）",
  "stream": true
}
```

要点：
- `stream` 必须为 `true`（后端会断言）。
- `model` 当前实现未参与路由层逻辑，但由于前端请求里包含该字段，仍然保留为必填字段。

响应：
- `Content-Type: text/event-stream`
- 每条消息形如 `data: ...\n\n`
- 结束会发送：`data: [DONE]\n\n`

cURL（直连 6800）：

```bash
curl -N -X POST 'http://127.0.0.1:6800/tools/aippt_outline' \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"content":"2025 科技前沿动态","language":"chinese","model":"unused","stream":true}'
```

---

### 1.2 `POST /tools/aippt_outline_unified`（推荐：主题 + 可选文件，SSE）

用途：统一的大纲生成接口，支持：
- 主题模式：只传 `content`
- 混合模式：`content + file`（以文件为主，主题作为补充上下文）

请求（`multipart/form-data`）字段：
- `content`：必填（主题）
- `file`：可选（上传文件）
- `language`：可选，默认 `chinese`
- `user_id`：可选，默认 `default_user`
- `folder_id`：可选，默认 `0`
- `file_type`：可选（未填时会尝试从文件名推断）

要点：
- 若提供 `file`，`main_api` 会先调用 `personaldb POST /upload/` 做解析与向量化，再把 `markdown_content` 拼到 prompt 里。
- 该接口不会把 `fileId` 直接返回给调用方；如需查看入库文件，可再调用 `GET /files/{user_id}` 查询。

响应：同 `POST /tools/aippt_outline`（SSE，最后 `data: [DONE]`）。

cURL（通过前端代理 `/api`）：

```bash
	curl -N -X POST 'http://127.0.0.1:5174/api/tools/aippt_outline_unified' \
	  -H 'Accept: text/event-stream' \
	  -F 'content=AI 在医疗的应用' \
  -F 'language=chinese' \
  -F 'user_id=123' \
  -F 'file=@/path/to/doc.pdf'
```

---

### 1.3 `POST /tools/aippt_outline_from_file`（文件/URL 生成大纲，SSE）

用途：只基于文件内容生成大纲（legacy 接口）；如需「主题 + 文件」，优先用 `POST /tools/aippt_outline_unified`。

请求（`multipart/form-data`）字段：
- `user_id`：必填
- `file`：可选（上传文件）
- `url`：可选（文件 URL）
- `folder_id`：可选，默认 `0`
- `file_type`：可选
- `language`：可选，默认 `chinese`

约束：
- `file` 与 `url` 互斥，且至少提供一个。

响应：SSE（最后 `data: [DONE]`）。

---

### 1.4 `POST /tools/aippt`（根据大纲生成逐页内容，SSE）

用途：输入 Markdown 大纲，流式返回逐页的 Slide Schema（通常是一段 JSON 字符串）。

请求（JSON，实际读取字段）：

```json
{
  "content": "# 标题\\n\\n## 章节\\n### 小节\\n- 要点",
  "language": "zh",
  "sessionId": "user_123",
  "generateFromUploadedFile": false,
  "generateFromWebSearch": true
}
```

要点：
- 当前实现只读取上面这些字段。
- 前端请求里可能会附带 `model/style/stream/template` 等字段；在默认 Pydantic 行为下，这些字段会被忽略，不影响结果。

响应：
- `Content-Type: text/event-stream`
- 心跳：约每 10 秒发送一次注释行 `: keep-alive\n\n`
- 数据：`data: <payload>\n\n`
  - `payload` 通常为一段 JSON 字符串（可由前端再 `JSON.parse`）
- 结束：`data: [DONE]\n\n`

cURL（直连 6800）：

```bash
curl -N -X POST 'http://127.0.0.1:6800/tools/aippt' \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"content":"# 标题\\n\\n## 章节\\n### 小节\\n- 要点","language":"zh","generateFromUploadedFile":false,"generateFromWebSearch":true,"sessionId":"123"}'
```

---

### 1.5 `POST /tools/aippt_by_id`（实验接口，当前未完成）

请求（JSON）：

```json
{
  "id": "xxx",
  "language": "chinese"
}
```

响应：
- `Content-Type: application/json; charset=utf-8`
- 当前实现会逐行输出 JSON 字符串/文本（非 SSE）。

注意：该接口在当前代码中没有接入真实的数据源，可能直接返回“没有找到该文章”等状态信息。

---

### 1.6 `GET /templates`（模板列表）

响应示例：

```json
{
  "data": [
    { "name": "红色通用", "id": "template_1", "cover": "/api/data/template_1.jpg" }
  ]
}
```

要点：
- `cover` 字段目前**硬编码带 `/api/` 前缀**，用于前端同源访问。
- 如果你直接访问 `http://127.0.0.1:6800`（不经过 `/api` 代理），请求图片时需要将 `/api` 前缀去掉，即访问 `/data/template_1.jpg`。

---

### 1.7 `GET /data/{filename}`（模板静态资源）

用途：读取 `backend/main_api/template/` 下的静态文件（模板 JSON、封面图等）。

示例：
- `GET /data/template_1.json`
- `GET /data/template_1.jpg`

---

### 1.8 `GET /files/{user_id}`（列出用户入库文件，代理 personaldb）

用途：`main_api` 代理调用 `personaldb GET /files/{user_id}`。

响应：文件列表（数组），元素包含：
- `file_id`
- `file_name`
- `file_type`
- `url`
- `folder_id`
- `user_id`

---

### 1.9 `GET /proxy?url=...`（透明代理外部资源）

用途：代理外部资源（主要用于图片等二进制内容），解决前端跨域与导出时的外链访问问题。

要点：
- 支持转发 `Range` / `User-Agent` 等部分请求头
- 以流式方式返回上游 bytes

---

### 1.10 `GET /healthz`（健康检查）

响应：

```json
{ "ok": true }
```

---

## 2. personaldb（端口 9100）

### 2.1 `POST /upload/`（上传并解析/向量化）

支持 `multipart/form-data` / `application/x-www-form-urlencoded` / `application/json`。

字段（注意命名为驼峰）：
- `userId`：必填
- `fileId`：必填
- `folderId`：可选，默认 `0`
- `fileType`：可选
- `url`：可选（与 `file` 互斥）
- `file`：可选（与 `url` 互斥）

成功响应包含（示例字段）：
- `id`（即 `fileId`）
- `file_name`
- `userId`
- `fileType`
- `url`
- `folderId`
- `embedding_result`
- `markdown_content`

---

### 2.2 `POST /search`（语义检索）

请求（JSON）：

```json
{
  "userId": 123,
  "query": "深度学习的应用",
  "keyword": "",
  "topk": 3
}
```

响应：Chroma `query` 的结果结构（典型包含 `ids/documents/metadatas/distances` 等字段）。

---

### 2.3 `POST /vectorize/text`（纯文本向量化并落库）

请求（JSON，必填字段最少为 `content/fileId/fileName`）：

```json
{
  "content": "要向量化的文本",
  "fileId": 1001,
  "fileName": "note.txt",
  "userId": 123
}
```

---

### 2.4 `GET /files/{user_id}`（列出用户文件）

响应：文件列表（数组），元素字段同上。

---

## 3. 相关文档

- 部署与运行：`doc/backend/backend_deployment.md`、`doc/DockerDeploy.md`
- 环境变量：`doc/dev/ENV_GUIDE.md`
- 模板制作：`doc/Template.md`
- 历史抓包记录：`doc/legacy/API_OUTLINE.md`、`doc/legacy/API_CONTENT.md` 等
