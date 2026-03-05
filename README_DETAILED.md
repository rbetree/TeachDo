# TeachDo 详细版 README

TeachDo 是面向教师的智能备课平台，围绕教学资料的全流程工作流构建：

- 大纲生成（Outline）
- 教案生成（Lesson Plan）
- PPT 内容生成与编辑（Slide + Editor）
- 知识库增强（KB / RAG）
- 导出与产物管理（DOCX / PPTX Artifacts）

当前仓库采用 **前后端分离 + FastAPI 多服务 + Vue 3 工作台 + 独立编辑器运行时** 的架构。

---

## 1. 项目目标与核心能力

### 1.1 目标

- 提供教师可落地使用的 AI 备课链路
- 用课程/单元（material）组织教学内容资产
- 将 AI 生成能力与可编辑、可导出、可复用的生产流程打通

### 1.2 核心能力

- 大纲流式生成（SSE）
- 基于大纲生成逐页 PPT 内容（含图片/图表场景）
- 教案生成与 DOCX 导出
- 知识库文件上传、向量化、检索增强
- 课程产出文件持久化（artifacts）
- 前端工作台管理 + 独立 PPT 编辑器导出

---

## 2. 技术栈

### 2.1 前端

- 框架：`Vue 3.5` + `TypeScript`
- 构建：`Vite 7`
- 路由：`vue-router 4`（`createWebHistory`）
- 状态管理：`Pinia`
- 样式：`Tailwind CSS` + `Sass`
- 图标/图形：`@icon-park/vue-next`、`echarts`
- 编辑器相关：`pptxgenjs`、`prosemirror` 系列、`docx-preview`
- 网络请求：`axios` + `fetch`（封装在 `services/`）

主要配置文件：

- `frontend/package.json`
- `frontend/vite.config.ts`

### 2.2 后端

- 框架：`FastAPI` + `Uvicorn`
- 语言：`Python`
- AI/Agent 相关：`google-adk`、`a2a-sdk`、`google-genai`、`litellm`
- 网络与协议：`httpx`、SSE（流式输出）
- 文档处理：`markitdown[all]`、`python-docx`、`docxtpl`
- 向量库：`chromadb`

主要配置文件：

- `backend/requirements.txt`
- `backend/start_backend.py`

### 2.3 基础设施与运行数据

- 容器编排：`docker-compose.yml`
- 日志目录：`logs/`
- 缓存目录：`var/cache`
- 临时目录：`var/tmp`
- 业务产物目录：`var/artifacts`（由 `main_api` artifacts API 管理）

---

## 3. 系统架构

### 3.1 服务拓扑

```text
┌──────────────────────────┐
│ Frontend (Vue + Vite)    │
│ /api/*                   │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│ main_api (FastAPI, 6800) │  统一入口 / 编排层(BFF)
└───────┬─────────┬────────┘
        │         │
        │         ├───────────────────────┐
        ▼         ▼                       ▼
┌──────────────┐ ┌────────────────┐ ┌──────────────────┐
│simpleOutline │ │slide_agent     │ │personaldb         │
│(10001)       │ │(10011)         │ │(9100)             │
│大纲 Agent     │ │内容 Agent       │ │知识库/向量检索服务   │
└──────────────┘ └────────────────┘ └──────────────────┘
```

### 3.2 各服务职责

- `main_api`（6800）
- 前端唯一后端入口
- 编排大纲、PPT、教案、助教、KB、Artifacts 等能力
- 封装对 `simpleOutline` / `slide_agent` / `personaldb` 的调用

- `simpleOutline`（10001）
- 根据主题或文本生成结构化 Markdown 大纲
- 支持基于输入长度的策略（纯内容生成 vs 搜索增强）

- `slide_agent`（10011）
- 将 Markdown 大纲扩写为逐页 Slide JSON
- 支持工具链（检索/图片/知识库）与流式输出

- `personaldb`（9100）
- 文件上传、格式转换、文本分块、向量化、检索
- 支持 `POST /upload/`、`POST /search`、`GET /files/{user_id}` 等能力

### 3.3 典型业务链路

#### A. 大纲生成

1. 前端提交主题或文件到 `main_api`
2. `main_api` 调用 `personaldb`（可选，文件解析/向量化）
3. `main_api` 调用 `simpleOutline`
4. 通过 SSE 返回大纲流

#### B. PPT 生成

1. 前端提交 Markdown 大纲到 `main_api`
2. `main_api` 调用 `slide_agent`
3. `slide_agent` 逐页生成并流式返回 JSON
4. `main_api` 对图表/图片页做必要拆分后返回前端渲染

#### C. KB/RAG 增强

1. 文件上传到 `main_api /kb/upload`
2. `main_api` 转发至 `personaldb /upload/`
3. `personaldb` 完成转换、分块、向量化、入库
4. 后续请求通过 `kb_file_ids` 触发检索/上下文注入

#### D. 产物管理（Artifacts）

1. 教案 DOCX / PPTX 导出后写入 artifacts
2. 通过 `GET /artifacts/{user_id}/{material_id}` 查看列表
3. 支持下载与删除

---

## 4. 仓库结构与关键入口

### 4.1 顶层结构

```text
TeachDo/
├── backend/               # FastAPI 多服务与后端测试
├── frontend/              # Vue 3 前端（当前唯一前端入口）
├── doc/                   # 项目文档（开发计划、后端架构、环境说明）
├── scripts/               # 冒烟校验与辅助脚本
├── template/              # 模板资源
├── var/                   # 运行期数据（缓存/临时/产物）
├── logs/                  # 运行日志
├── start.py               # 一键启动脚本（推荐入口）
└── docker-compose.yml     # 容器部署入口
```

### 4.2 关键文件（高频）

- 启动编排：`start.py`
- 后端启动器：`backend/start_backend.py`
- 主 API：`backend/main_api/main.py`
- 大纲服务：`backend/simpleOutline/main_api.py`
- 内容服务：`backend/slide_agent/main_api.py`
- 知识库服务：`backend/personaldb/main.py`
- 前端入口：`frontend/src/main.ts`
- 前端路由：`frontend/src/router/index.ts`
- 当前开发计划：`doc/dev/PLAN.md`
- 环境变量说明：`doc/dev/ENV_GUIDE.md`

---

## 5. 环境配置

### 5.1 初始化

```bash
cp env_template.txt .env
```

### 5.2 环境变量加载优先级（后端约定）

- 系统环境变量
- 服务目录 `.env`（可选，本机临时覆盖）
- 项目根目录 `.env`（推荐统一维护）

### 5.3 重点配置项

- 模型配置
- `OUTLINE_TYPE` / `OUTLINE_MODEL` / `OUTLINE_API_KEY`
- `PPT_WRITER_TYPE` / `PPT_WRITER_MODEL` / `PPT_WRITER_API_KEY`
- `PPT_CHECKER_TYPE` / `PPT_CHECKER_MODEL` / `PPT_CHECKER_API_KEY`
- `EMBEDDING_TYPE` / `EMBEDDING_MODEL` / `EMBEDDING_API_KEY`

- 内部服务地址
- `OUTLINE_API`（默认 `http://127.0.0.1:10001`）
- `CONTENT_API`（默认 `http://127.0.0.1:10011`）
- `PERSONAL_DB`（默认 `http://127.0.0.1:9100`）

- 功能开关
- `OUTLINE_STREAMING`
- `CONTENT_STREAMING`
- `USE_CHART`
- `USE_MINERU`

- 运行目录
- `TEACHDO_CACHE_DIR`
- `TEACHDO_TMP_DIR`
- `TEACHDO_LOG_DIR`

---

## 6. 启动与开发流程

### 6.1 一键启动（推荐）

```bash
cp env_template.txt .env
python start.py
```

默认端口：

- 前端：`5174`
- `main_api`：`6800`
- `simpleOutline`：`10001`
- `slide_agent`：`10011`
- `personaldb`：`9100`

### 6.2 仅启动后端

```bash
cd backend
pip install -r requirements.txt
python start_backend.py
```

### 6.3 仅启动前端

```bash
cd frontend
npm install
npm run dev
```

### 6.4 Docker 启动

```bash
cp env_template.txt .env
docker compose up --build
```

---

## 7. API 概览（`main_api`）

以下端点来自 `backend/main_api/main.py` 当前代码：

### 7.1 生成链路

- `POST /tools/aippt_outline`
- `POST /tools/aippt_outline_unified`
- `POST /tools/aippt_outline_from_file`
- `POST /tools/aippt`
- `POST /tools/lesson_plan`
- `POST /tools/assistant_chat`

### 7.2 教案模板与导出

- `GET /lesson/templates`
- `POST /lesson/export/docx`

### 7.3 知识库（BFF）

- `POST /kb/upload`
- `GET /kb/files/{user_id}`
- `GET /kb/files/{user_id}/{file_id}/export`
- `POST /kb/vectorize/text`
- `DELETE /kb/files/{user_id}/{file_id}`

### 7.4 产物管理（Artifacts）

- `GET /artifacts/{user_id}/{material_id}`
- `POST /artifacts/{user_id}/{material_id}`
- `GET /artifacts/{user_id}/{material_id}/{artifact_id}`
- `DELETE /artifacts/{user_id}/{material_id}/{artifact_id}`

### 7.5 其他

- `GET /templates`
- `GET /data/{filename}`
- `GET /files/{user_id}`
- `GET /proxy`
- `GET /healthz`

---

## 8. 前端路由与页面结构

根据 `frontend/src/router/index.ts`：

- 资料选择页：`/`
- 工作台默认：`/material/:materialId`（自动归一化到 `outline`）
- 工作台分栏：`/material/:materialId/:tab`
- `tab` 支持：`outline` / `lesson` / `ppt` / `assistant`
- 独立编辑器：`/material/:materialId/ppt/editor`
- 其他页面：`/about`、`/settings`

关键点：

- 路由前置守卫会校验 `materialId` 是否存在
- 非法 `tab` 会回退到 `outline`
- 前端统一请求 `/api/*`，由 Vite 代理转发到 `http://127.0.0.1:6800`

---

## 9. 数据与状态设计（简述）

### 9.1 教学资料实体（Material）

- 以课程/单元为核心上下文
- 承载大纲、教案、PPT、助教等模块状态
- 关联 `kb_file_ids` 作为知识来源与上下文注入入口

### 9.2 知识文件分类（工程约定）

- 参考资料（RAG）
- 课程产出（全文注入）
- 全文上传（全文注入）

### 9.3 运行时数据落盘

- 缓存：`var/cache`
- 临时文件：`var/tmp`
- 导出产物：`var/artifacts`
- 日志：`logs`

---

## 10. 测试与质量保障

### 10.1 前端校验

```bash
cd frontend
npm run typecheck
npm run lint
npm run build
```

### 10.2 后端测试

```bash
pytest backend -q
```

### 10.3 接口冒烟

```bash
python scripts/verify_endpoints.py
```

### 10.4 典型后端测试文件

- `backend/test_artifacts_api.py`
- `backend/test_assistant_chat.py`
- `backend/test_kb_bff.py`
- `backend/test_lesson_plan.py`
- `backend/test_outline_kb_rag.py`
- `backend/test_personaldb_endpoints.py`

---

## 11. 部署与运维要点

- 前端使用 `createWebHistory`，部署网关需正确处理 history fallback
- 生产部署建议优先参考 `README_PRODUCTION.md`
- 修改 API 时需同步前端 `services/` 封装与文档
- 日志与缓存目录建议挂载持久卷（Docker 模式已提供挂载）

---

## 12. 常见问题排查

### 12.1 前端能打开但接口 404

- 检查 Vite 代理：`frontend/vite.config.ts`
- 检查 `main_api` 是否运行在 `6800`

### 12.2 大纲/PPT 无输出或超时

- 检查 `.env` 中模型配置是否完整
- 检查外部模型服务连通性（`*_BASE_URL`、`*_API_KEY`）
- 检查 `simpleOutline`、`slide_agent` 服务健康状态

### 12.3 KB 上传成功但检索为空

- 检查 `EMBEDDING_*` 配置是否有效
- 检查 `personaldb` 日志中分块/向量化是否报错
- 检查请求 `user_id` 与 `file_ids` 是否一致

### 12.4 导出文件看不到

- 检查 artifacts API 是否可用
- 检查 `var/artifacts` 写权限
- 检查 material/user 维度是否匹配

---

## 13. 文档导航

- 项目总览：`README.md`
- 生产部署：`README_PRODUCTION.md`
- 开发计划：`doc/dev/PLAN.md`
- 环境说明：`doc/dev/ENV_GUIDE.md`
- 后端文档索引：`doc/backend/README.md`
- 后端架构：`doc/backend/backend_architecture.md`

---

## 14. 贡献建议（团队协作）

- 新增能力优先落在 `services/` 与模块边界内，避免跨层耦合
- 变更接口时同步更新：后端代码、前端调用、文档、测试
- 提交前至少执行前端构建与后端关键测试/冒烟

