# TeachDo 项目架构（维护版）

> 最后更新：2026-02-28  
> 文档边界：本文描述 TeachDo 的稳定组件拆分与关键数据流；接口字段/示例以 `doc/backend/backend_api_reference.md` 为准；功能/路由到 API 映射见 `doc/architecture/FEATURE_API_OVERVIEW.md`。

## 1. 主链路（用户视角）

- 首页：`/`（教学资料选择/创建）
- 工作台：`/material/:materialId/:tab`（`outline` / `lesson` / `ppt` / `assistant`）
- 独立编辑器：`/material/:materialId/ppt/editor`（编辑与导出 PPTX）

## 2. 组件与职责

### 2.1 前端（`frontend/`）

- Vue 3 + Vite + TypeScript 单页应用（SPA）
- 路由：`frontend/src/router/index.ts`
- 状态：`frontend/src/stores/appStore.ts`（TeachingMaterial、kbFiles、主题/语言等）
- 服务层：`frontend/src/services/aiService.ts` 与 `frontend/src/services/ai/*`（统一封装 HTTP/SSE）
- SSE 解析：`frontend/src/utils/sse.ts`
- 编辑器运行时：`frontend/src/editor-runtime/**`（仅编辑器路由按需加载）

### 2.2 后端（`backend/`）

- `main_api`（6800）：对前端唯一入口（前端统一走 `/api/*`）
  - 编排：Outline/Lesson/PPT/Assistant 请求统一在此组装 prompt 与上下文
  - 网关：调用下游 Agent 服务与 personaldb
  - 静态资源：模板 `/templates`、`/data/*`
  - 产物持久化：Artifacts（DOCX/PPTX）落盘与 API
- `simpleOutline`（10001）：大纲生成 Agent（A2A）
- `slide_agent`（10011）：PPT 内容生成 Agent（A2A）
- `personaldb`（9100）：知识库（上传/解析/向量化/检索/导出全文）

### 2.3 系统调用关系（概览）

```mermaid
graph TB
  subgraph Frontend[Frontend (Vue SPA)]
    UI[TeachDo UI]
    Editor[PPT Editor Runtime]
  end

  subgraph MainAPI[main_api :6800]
    Gateway[HTTP/SSE Gateway]
    Artifacts[Artifacts Store]
  end

  subgraph Agents[Agent Services]
    Outline[simpleOutline :10001]
    Content[slide_agent :10011]
  end

  subgraph KB[Knowledge Base]
    PersonalDB[personaldb :9100]
  end

  UI -->|/api/*| Gateway
  Editor -->|/api/* (artifacts)| Gateway
  Gateway --> Outline
  Gateway --> Content
  Gateway --> PersonalDB
  Gateway --> Artifacts
```

## 3. KB 与上下文注入约定（高频）

TeachDo 的“知识库增强”由前端选择的 `kb_file_ids` 驱动，后端在 `main_api` 侧统一解析并拆分为两类上下文：

### 3.1 `folder_id` 语义（personaldb 维度）

- `folder_id=0`：上传素材（用于 RAG 检索；只注入片段）
- `folder_id=1`：生成产物（通常 `gen:`；全文注入，不经检索）
- `folder_id=2`：全文上传（通常 `full:`；全文注入，不经检索）

### 3.2 `file_id` 前缀约定（TeachDo 维度）

- `upload:*`：上传素材（RAG 检索片段）
- `gen:*`：生成产物（全文注入）
- `full:*`：全文上传（全文注入）

> 前端侧判定逻辑见：`frontend/src/utils/kbFileId.ts`。

### 3.3 `kb_file_ids` 拆分规则（main_api 维度）

- `full_ids`：`gen:` / `full:` 前缀 → 调 personaldb `GET /files/{user_id}/{file_id}/content` 拉取全文并拼入上下文
- `rag_ids`：其他前缀（典型 `upload:`）→ 调 personaldb `POST /search` 检索片段并拼入上下文

该规则会被复用到：大纲生成 / 教案生成 / PPT 生成 / 助教对话等端点（见 `doc/architecture/FEATURE_API_OVERVIEW.md`）。

## 4. 产物持久化（Artifacts）

TeachDo 将“导出的 DOCX/PPTX”作为可再次下载的课程产物进行存储：

- 默认目录：`var/artifacts/`（由 `TEACHDO_ARTIFACT_DIR` 控制）
- API（main_api）：`/artifacts/{user_id}/{material_id}`（list/upload/download/delete）
- 典型来源：
  - DOCX：`POST /lesson/export/docx` 可选 `persist=true`（边下载边保存）
  - PPTX：编辑器导出后在前端上传到 `/artifacts/...`（保持浏览器端导出体验）

## 5. 启动与部署入口

- 一键启动（推荐）：`cp env_template.txt .env && python start.py`
- 后端全服务：`cd backend && pip install -r requirements.txt && python start_backend.py`
- 前端开发：`cd frontend && npm i && npm run dev`
- Docker：`docker compose up --build`（见 `doc/DockerDeploy.md`）

环境变量统一约定见：`doc/dev/ENV_GUIDE.md`（根目录 `.env` + 优先级规则）。

## 6. 进一步阅读

- 功能/路由 → API：`doc/architecture/FEATURE_API_OVERVIEW.md`
- API 参考（以代码为准）：`doc/backend/backend_api_reference.md`
- 后端部署与运行：`doc/backend/backend_deployment.md`
- 前端 API 封装清单：`doc/dev/FRONTEND_API_CALLS.md`
- 模板制作与结构：`doc/Template.md`、`doc/PPT_Structure.md`
