# TeachDo

TeachDo 是一套面向教师的智能备课平台：以“课程/单元”为工作流单元，支持大纲生成、PPT 流式生成、知识库（KB）引用与独立编辑器导出。

## ✨ 核心能力

- **大纲生成（SSE）**：基于主题输入流式生成大纲并保存
- **PPT 生成（SSE）**：支持模板选择、增量页生成、生成产物入库
- **知识库（KB）**：上传素材向量化、生成产物入库、生成时可选引用范围
- **独立编辑器**：工作台只读预览；跳转编辑器进行编辑与导出 PPTX

## 📦 项目结构（当前以 TeachDo 为准）

```
TeachDo/
├── backend/                 # FastAPI 多服务
│   ├── main_api/            # BFF/Gateway（前端统一走 /api）
│   ├── simpleOutline/       # 大纲服务
│   ├── slide_agent/         # PPT 内容生成服务
│   ├── personaldb/          # KB（向量化/检索）
│   └── mock_api/            # 可选：mock SSE 联调用
├── teachdo-frontend/        # ✅ TeachDo 唯一前端入口（Vue 3 + Vite + TS）
├── frontend/                # legacy 前端源码（不在 TeachDo 运行链路内）
├── scripts/                 # 验证脚本与工具
└── doc/                     # 项目文档（含迁移说明）
```

## 🚀 快速开始

### 方式一：一键启动（推荐）

```bash
cp env_template.txt .env
python start.py
```

默认端口：前端 `5174`，主 API `6800`，大纲 `10001`，内容 `10011`，KB `9100`。

### 方式二：分别启动（开发联调）

后端（全部服务）：

```bash
cd backend
pip install -r requirements.txt
python start_backend.py
```

前端：

```bash
cd teachdo-frontend
npm i
npm run dev
```

说明：前端统一请求相对路径 `/api/*`，开发环境由 `teachdo-frontend/vite.config.ts` 代理到 `http://127.0.0.1:6800/*`。

## 🧭 路由速查（TeachDo）

- 工作台：`/course/:courseId`
- 单元标签：`/course/:courseId/unit/:unitId/:tab`
- 独立编辑器：`/course/:courseId/unit/:unitId/ppt/editor`

## ✅ 工程校验（发布前必跑）

```bash
cd teachdo-frontend
npm run typecheck
npm run lint
npm run build
```

## 📚 文档与脚本

- 迁移与实施计划：`doc/dev/PLAN.md`
- 环境变量说明：`doc/dev/ENV_GUIDE.md`
- 前端 API 映射：`doc/dev/FRONTEND_API_CALLS.md`
- 接口冒烟校验：`scripts/verify_endpoints.py`

## ⚠️ 已知限制

- `lesson/assistant` 等非核心页当前以“可运行收敛”为目标，部分交互入口处于禁用状态
- `docker-compose.yml` 的前端服务仍指向 legacy `frontend/`（容器化切换在阶段 H 处理）
