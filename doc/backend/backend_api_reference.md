# 后端 API 参考（维护版，以代码为准）

> 最后更新：2026-02-28  
> 源码入口：`backend/main_api/main.py`（main_api） / `backend/personaldb/main.py`（personaldb）  
> 说明：前端默认通过 `/api` 代理访问 `main_api`。下文以「通过前端代理」写法为主，并在需要时补充「直连端口」写法。

---

## 0) Base URL

### main_api（FastAPI 网关，端口 6800）

- 直连：`http://127.0.0.1:6800`
- 通过前端代理（Vite/Nginx）：`http://127.0.0.1:5174/api`（或同域 `/api`）

### personaldb（知识库，端口 9100）

- 直连：`http://127.0.0.1:9100`

---

## 1) SSE（text/event-stream）约定

TeachDo 的流式端点统一使用 SSE：

- 响应头：`Content-Type: text/event-stream`
- 数据帧：`data: ...\n\n`
- 结束帧：`data: [DONE]\n\n`

---

## 2) main_api（端口 6800）

### 2.1 健康检查

- `GET /healthz` → `{"ok": true}`

### 2.2 模板与静态资源

- `GET /templates` → `{"data":[{"id","name","cover"}]}`
- `GET /data/{filename}` → 返回文件（模板 JSON、封面图等）

> 运行时静态资源目录：`backend/main_api/template/`（`start.py` 会以 `backend/main_api` 作为进程工作目录）。

### 2.3 大纲生成

#### `POST /tools/outline`（推荐，SSE Markdown）

> 兼容别名：`POST /tools/aippt_outline_unified`

请求：`multipart/form-data`（字段）

- `content`：必填（主题/上下文文本）
- `language`：可选，默认 `chinese`
- `user_id`：可选，默认 `default_user`
- `kb_file_ids`：可选，可重复传多次（限定 RAG/全文注入的文件集合）
- `file`：可选（上传文件；会先走 personaldb `/upload/` 解析后拼入 prompt）

响应：SSE Markdown（最终 `data: [DONE]`）

#### `POST /tools/aippt_outline`（legacy，SSE Markdown）

用途：历史兼容接口（仅主题），请求体为 JSON（需 `stream=true`）。

#### `POST /tools/outline_from_file`（legacy，SSE Markdown）

> 兼容别名：`POST /tools/aippt_outline_from_file`

用途：历史兼容接口（文件/URL），请求为 `multipart/form-data`。

### 2.4 PPT 内容生成

#### `POST /tools/ppt`（SSE，每条 data 为 JSON 字符串）

> 兼容别名：`POST /tools/aippt`

请求：JSON（字段）

- `content`：必填（Markdown 大纲）
- `language`：可选，默认 `zh`
- `sessionId`：可选（前端默认用教学资料 id；也可用固定用户 id）
- `generateFromWebSearch`：可选，默认 `true`
- `generateFromUploadedFile`：可选，默认 `false`
- `kb_folder_ids`：可选（仅对 RAG 生效的 folder 过滤）
- `kb_file_ids`：可选（更精确的文件过滤；同时用于全文注入/检索增强）

响应：SSE 数据流。每个 `data:` 典型为：

- Slide Schema：`{"type":"cover"|"contents"|"content"|"transition"|"reference"|"end", ...}`
- 错误：`{"type":"error","text":"..."}`
- 结束：`[DONE]`

### 2.5 教案生成与导出

#### `POST /tools/lesson_plan`（SSE，JSON events）

请求：JSON（字段）

- `title/subject/description/objectives`：教学资料信息
- `outlineContent`：必填（Markdown 大纲）
- `language`：可选，默认 `zh`
- `sessionId`：可选
- `user_id`：可选，默认 `default_user`
- `kb_file_ids`：可选（上下文增强）
- `templateId`：可选（教案导出版式选择）

响应：SSE 数据流。每个 `data:` 典型为：

- 分节：`{"type":"section","section":"objectives|materials|procedure|homework","data":...}`
- 最终：`{"type":"final","data":{...LessonPlan...}}`
- 错误：`{"type":"error","text":"..."}`
- 结束：`[DONE]`

#### `GET /lesson/templates`

响应：`{"data":[{"id","name","description"}]}`

#### `POST /lesson/export/docx`（附件下载）

请求：JSON（字段）

- `lessonPlan`：必填（结构化教案）
- `style`：必填（LessonStyle）
- `language`：可选，默认 `zh`
- `templateId`：可选
- `persist`：可选（`true` 时保存到 artifacts）
- `userId/materialId`：可选（persist 时用于归档路径；前端默认传 `default_user` + 当前 materialId）

响应：

- `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `Content-Disposition: attachment; filename*=UTF-8''...`
- 可选：`X-TeachDo-Artifact-Id: <artifact_id>`

### 2.6 助教问答

#### `POST /tools/assistant_chat`（SSE 文本 delta）

请求：JSON（字段）

- `messages`：必填（数组：`{role:"user"|"assistant", content:string}`）
- `user_id`：可选，默认 `default_user`
- `kb_file_ids`：可选（上下文增强）
- `material`：可选（教学资料摘要字段）
- `language`：可选，默认 `zh`

响应：SSE 文本 delta（多条 `data:`），并以 `data: [DONE]` 结束。

> 错误可能以结构化 JSON 形式返回：`{"type":"error","text":"..."}`。

### 2.7 知识库（KB，BFF）

> 本组接口统一返回 wrapper：成功为 `{"ok": true, "data": ...}`；失败为 `{"ok": false, "error": {"code","message"}}`。

#### `POST /kb/upload`（上传并向量化）

请求：`multipart/form-data`

- `user_id`：必填（前端默认 `default_user`）
- `folder_id`：可选，默认 `0`（0=上传素材；1=生成产物；2=全文上传）
- `file_id`：可选（不传则后端自动生成 `upload:{user_id}:{epochMs}:{rand3}`）
- `file_type`：可选（不传则尝试从文件名推断）
- `file`：必填

#### `GET /kb/files/{user_id}`（列出文件）

可选 query：`folder_id`

#### `GET /kb/files/{user_id}/{file_id}/export`（导出文件内容）

用途：按 file_id 聚合返回全文内容（Markdown/纯文本），以附件下载形式返回。

#### `POST /kb/vectorize/text`（纯文本入库）

请求：JSON（字段）

- `user_id/file_id/file_name/content`：必填
- `file_type`：可选，默认 `md`
- `folder_id`：可选，默认 `1`
- 可观测性元数据（可选）：`created_at/source_type/source_material_id/source_material_title`

#### `DELETE /kb/files/{user_id}/{file_id}`（删除向量）

### 2.8 导出产物（Artifacts）

> 本组接口同样使用 `{"ok": true, "data": ...}` wrapper。

- `GET /artifacts/{user_id}/{material_id}`：列表
- `POST /artifacts/{user_id}/{material_id}`：上传（`multipart/form-data`：`kind`=`pptx|docx`，`file`）
- `GET /artifacts/{user_id}/{material_id}/{artifact_id}`：下载（附件）
- `DELETE /artifacts/{user_id}/{material_id}/{artifact_id}`：删除

### 2.9 代理外部资源

- `GET /proxy?url=...`：透明代理二进制资源（导出/外链图片场景按需使用）

---

## 3) personaldb（端口 9100）

> 说明：前端不应直连 personaldb；建议统一通过 main_api 的 KB BFF（`/kb/*`）访问。

### 3.1 健康检查

- `GET /healthz`

### 3.2 `POST /upload/`（上传并解析/向量化）

支持 `multipart/form-data` / `application/x-www-form-urlencoded` / `application/json`。

字段（驼峰）：

- `userId`：必填（字符串/数字均可；建议用 `default_user`）
- `fileId`：必填（字符串/数字均可）
- `folderId`：可选，默认 `0`
- `fileType`：可选
- `url`：可选（与 `file` 互斥）
- `file`：可选（与 `url` 互斥）
- 可观测性元数据（可选）：`createdAt/sourceType/sourceMaterialId/sourceMaterialTitle`

### 3.3 `POST /search`（语义检索）

请求：JSON

- `userId`：必填
- `query`：必填
- `keyword`：可选
- `topk`：可选，默认 `3`
- `fileIds`：可选（仅在给定文件集合内检索）

### 3.4 `POST /vectorize/text`（纯文本向量化并落库）

请求：JSON（字段）

- `content/fileId/fileName`：必填
- `userId`：可选
- `fileType/url/folderId`：可选
- 可观测性元数据（可选）：`createdAt/sourceType/sourceMaterialId/sourceMaterialTitle`

### 3.5 文件列表/导出/删除

- `GET /files/{user_id}`：列出该用户文件（数组）
- `GET /files/{user_id}/{file_id}/content`：导出该文件的聚合全文（用于 BFF 导出/全文注入）
- `DELETE /files/{user_id}/{file_id}`：删除该文件对应的向量数据
