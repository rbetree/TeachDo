# TeachDo 功能与 API / 页面映射（维护版）

> 文档版本：3.0  
> 最后更新：2026-02-16  
> 说明：本文件只保留「稳定不易过时」的功能/路由到 API 映射；详细请求/响应以 `doc/backend/backend_api_reference.md` 为准。

---

## 1. 系统组件与端口

- 前端（TeachDo）：Vue 3 + Vite（默认端口 5174）
- `main_api`：6800（对前端唯一入口，提供 `/tools/*`、`/templates`、`/data/*`、`/proxy` 等）
- `simpleOutline`：10001（大纲 Agent，A2A 服务）
- `slide_agent`：10011（内容 Agent，A2A 服务）
- `personaldb`：9100（知识库：上传/解析/向量化/检索）

---

## 2. 核心流程（从主题到可编辑 PPT）

1. 进入工作台：选择课程与单元（`/course/:courseId/...`）
2. 大纲页（`/course/:courseId/unit/:unitId/outline`）调用 `POST /tools/aippt_outline_unified`（SSE）生成 Markdown 大纲并保存
3. PPT 页（`/course/:courseId/unit/:unitId/ppt`）拉取模板列表：`GET /templates`，并按选中模板拉取模板 JSON：`GET /data/{template_id}.json`
4. PPT 页调用 `POST /tools/aippt`（SSE）获取逐页 Slide Schema（后端输出），前端映射为编辑器 `Slide[]` 并回写到 `CourseUnit.editorDocument`
5. 工作台预览仅只读渲染；点击「进行编辑」进入独立编辑器（`/course/:courseId/unit/:unitId/ppt/editor`）编辑/导出 PPTX
6. 导出如遇外链图片：使用 `GET /proxy?url=...` 走同源代理下载（按需）

---

## 3. 功能 → API 映射

> 前端统一使用 `/api` 代理访问后端（开发环境由 Vite 代理；Docker 环境由 Nginx 反向代理）。

### 3.1 大纲生成

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 统一接口生成大纲（推荐） | `/course/:courseId/unit/:unitId/outline` | `POST /tools/aippt_outline_unified` | 主题必填（V1）；SSE Markdown |
| 主题生成大纲（兼容接口） | 同上 | `POST /tools/aippt_outline` | legacy/兼容接口 |
| 文件/URL 生成大纲（legacy） | 同上 | `POST /tools/aippt_outline_from_file` | legacy/兼容接口 |

### 3.2 内容生成

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 根据大纲生成内容 | `/course/:courseId/unit/:unitId/ppt` | `POST /tools/aippt` | 大纲 → SSE Slide Schema（模板映射在前端完成） |

### 3.3 模板与静态资源

| 功能 | 前端入口 | API（main_api） | 说明 |
|---|---|---|---|
| 获取模板列表 | `/course/:courseId/unit/:unitId/ppt` | `GET /templates` | 返回模板元数据（`name/id/cover`） |
| 获取模板 JSON/封面等 | 多处 | `GET /data/{filename}` | 典型：`/data/{id}.json`、`/data/{id}.jpg` |

### 3.4 知识库（KB）

| 功能 | 服务 | API | 说明 |
|---|---|---|---|
| 上传素材并向量化（BFF） | main_api | `POST /kb/upload` | 统一入口，转发 personaldb |
| 列出 KB 文件（BFF） | main_api | `GET /kb/files/{user_id}` | `user_id = course.id`；可选 `folder_id` 过滤 |
| 删除 KB 文件（BFF） | main_api | `DELETE /kb/files/{user_id}/{file_id}` | 删除向量，避免检索命中旧数据 |
| 生成产物入库（BFF） | main_api | `POST /kb/vectorize/text` | 将大纲/slide 文本写入 KB 索引（`folder_id=1`） |

### 3.5 工具/运维

| 功能 | 服务 | API | 说明 |
|---|---|---|---|
| 代理外部资源 | main_api | `GET /proxy` | 代理图片等资源，解决跨域/导出问题 |
| 健康检查 | main_api | `GET /healthz` | 返回 `{"ok": true}` |

---

## 4. 路由 → API（当前前端实现概览）

- `/`：课程选择页（不调用后端）
- `/course/:courseId/unit/:unitId/outline`：`POST /tools/aippt_outline_unified`（SSE）+ 保存后 `POST /kb/vectorize/text`（入库）
- `/course/:courseId/unit/:unitId/ppt`：`GET /templates`、`GET /data/{id}.json`、`POST /tools/aippt`（SSE）+ 完成后 `POST /kb/vectorize/text`（入库）
- `/course/:courseId/unit/:unitId/ppt/editor`：纯前端编辑/导出（不新增后端 API）
- `/course/:courseId/kb`：`POST /kb/upload`、`GET /kb/files/*`、`DELETE /kb/files/*`
- `/course/:courseId/assistant`：当前为“可运行收敛”，交互入口默认禁用

---

## 5. 进一步阅读

- API 参考（以代码为准）：`doc/backend/backend_api_reference.md`
- 环境变量：`doc/dev/ENV_GUIDE.md`
- 前端 API 映射：`doc/dev/FRONTEND_API_CALLS.md`
- Docker 部署：`doc/DockerDeploy.md`
- 模板制作与结构：`doc/Template.md`、`doc/PPT_Structure.md`
- 开发计划（当前）：`doc/dev/PLAN.md`
