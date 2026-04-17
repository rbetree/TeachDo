# 项目架构

本页概述 TeachDo 的稳定组件拆分、主链路数据流，以及知识库与产物的关键约定。

## 用户主链路

- 首页：`/`
- 工作台：`/material/:materialId/:tab`
- 独立编辑器：`/material/:materialId/ppt/editor`

备课流程可以概括为：主题输入 -> 大纲生成 -> 教案 / PPT 生成 -> 编辑器精修与导出。

## 系统拆分

### 前端 `frontend/`

- Vue 3 + Vite + TypeScript 单页应用。
- 路由入口位于 `frontend/src/router/index.ts`。
- 服务层集中在 `frontend/src/services/`，统一处理 HTTP 与 SSE 请求。
- 编辑器运行时位于 `frontend/src/editor-runtime/`，仅在编辑器路由按需加载。

### 后端 `backend/`

- `main_api`：前端统一入口，负责聚合、编排与产物 API。
- `simpleOutline`：大纲生成服务。
- `slide_agent`：PPT 内容生成服务。
- `personaldb`：知识库上传、解析、向量化与检索服务。
- `mock_api`：用于联调与冒烟的可选服务。

## 调用关系

```text
Frontend UI / Editor
        |
        |  /api/*
        v
main_api (BFF / Gateway)
  |        |         |
  |        |         +--> Artifacts Store
  |        |
  |        +------------> personaldb
  |
  +---------------------> simpleOutline
  |
  +---------------------> slide_agent
```

前端所有核心请求统一进入 `main_api`，由其根据业务场景转发到 Agent 服务或知识库服务，并负责最终的产物保存与下载能力。

## 知识库上下文注入

TeachDo 的知识库增强由前端传入的 `kb_file_ids` 驱动，后端会拆分成全文注入与检索注入两种路径。

### `folder_id` 约定

- `0`：上传素材，通常只参与检索片段注入。
- `1`：生成产物，通常以全文形式注入。
- `2`：全文上传文件，通常以全文形式注入。

### `file_id` 前缀约定

- `upload:*`：上传素材，走 RAG 检索。
- `gen:*`：生成产物，走全文注入。
- `full:*`：全文上传文件，走全文注入。

### `kb_file_ids` 拆分规则

- `full_ids`：`gen:` / `full:` 前缀，对应读取全文内容并拼接到上下文。
- `rag_ids`：其他前缀，典型是 `upload:`，对应走 `personaldb` 检索片段。

这套规则会复用到大纲生成、教案生成、PPT 生成和助教对话等高频功能中。

## 产物持久化

TeachDo 将导出的 DOCX 与 PPTX 视为课程产物统一管理。

- 默认目录：`var/artifacts/`
- 可通过环境变量 `TEACHDO_ARTIFACT_DIR` 调整
- 主要 API：`/artifacts/{user_id}/{material_id}`

典型场景：

- 教案导出可在服务端边生成边持久化 DOCX。
- PPT 编辑器导出后会由前端上传到产物 API，保持浏览器侧导出体验。

## 启动与验证入口

- 一键启动：`cp env_template.txt .env && python3 start.py`
- 后端全服务：`cd backend && pip install -r requirements.txt && python3 start_backend.py`
- 前端开发：`cd frontend && npm i && npm run dev`
- 前端校验：`cd frontend && npm run typecheck && npm run lint && npm run build`
- 后端测试：`venv/bin/python -m pytest backend -q`

## 关键入口文件

- 启动编排：`start.py`
- 主 API：`backend/main_api/main.py`
- 大纲服务：`backend/simpleOutline/main_api.py`
- PPT 内容服务：`backend/slide_agent/main_api.py`
- KB 服务：`backend/personaldb/main.py`
- 前端入口：`frontend/src/main.ts`
- 前端路由：`frontend/src/router/index.ts`
