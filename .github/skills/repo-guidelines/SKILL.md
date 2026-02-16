---
name: repo-guidelines
description: 当任务涉及 TeachDo 代码实现、测试验证、提交发布或环境配置时加载，获取仓库级工程规范与操作约束。
---

# TeachDo Repository Guidelines

TeachDo 仓库的详细工程规范与常用操作手册。

## 语言约定

- 默认中文沟通；用户明确指定其他语言时按用户要求执行。

## 开发与运行命令

- 一键启动：`cp env_template.txt .env && python start.py`
- 后端全服务：`cd backend && pip install -r requirements.txt && python start_backend.py`
- 单服务启动（示例）：`cd backend/main_api && cp env_template .env && uvicorn main:app --reload --port 6800`
- TeachDo 前端：`cd teachdo-frontend && npm i && npm run dev`
- 前端构建：`cd teachdo-frontend && npm run build`
- 前端静态检查：`cd teachdo-frontend && npm run lint`
- 前端类型检查：`cd teachdo-frontend && npm run typecheck`
- 后端测试：`pytest backend -q`
- 可选容器联调：`docker compose up`

## 目录与模块职责

- `backend/`
- `backend/main_api/`: HTTP API/BFF（前端统一入口）
- `backend/simpleOutline/`: 大纲生成服务
- `backend/slide_agent/`: PPT 内容生成服务
- `backend/personaldb/`: 知识库检索与向量化
- `backend/mock_api/`: mock/演示服务
- `teachdo-frontend/`: 当前主前端项目
- `frontend/`: legacy 前端（非 TeachDo 主链路）
- `doc/`: 设计与开发文档
- `scripts/`: 运维/校验脚本

## 代码风格

- Python
- 遵循 PEP 8，4 空格缩进，优先补充 type hints
- 命名：函数/模块 `snake_case`，类 `PascalCase`
- 测试命名：`test_*.py`
- Vue/TypeScript（`teachdo-frontend`）
- 2 空格缩进
- 组件文件 `PascalCase`，组合式函数 `useXxx.ts`，状态管理在 store 中集中维护
- API 请求集中在服务层，避免散落到视图组件

## 测试与质量门槛

- 后端：`pytest backend -q`
- 前端：`npm run typecheck && npm run lint && npm run build`
- 涉及 SSE 或跨服务链路时，优先验证：
- Outline 生成
- PPT 流式生成与状态回写
- 编辑器回显与导出链路
- 提交前至少完成一次与改动范围匹配的本地验证，并在变更说明中记录结果。

## 提交与 PR 规范

- 提交信息遵循 Conventional Commits，例如：
- `feat(frontend): add outline editor`
- `fix(backend): keep-alive for SSE`
- PR 需要包含：
- 变更摘要
- 验证步骤
- UI 变更截图（如适用）
- 涉及接口/环境变量/端口变化时同步更新文档。

## 安全与配置

- 使用 `env_template.txt` 生成 `.env`，禁止提交密钥到仓库。
- 关键变量：`HOST`、`MAIN_API_PORT`、`OUTLINE_API_PORT`、`CONTENT_API_PORT`、`PERSONAL_DB`。
- 默认端口以项目当前配置为准（常见为 `6800`、`10001`、`10011`，前端本地开发见 `teachdo-frontend` 配置）。

## 常见任务入口

- 开发计划：`doc/dev/PLAN.md`
- 环境变量说明：`doc/dev/ENV_GUIDE.md`
- 前端 API 映射：`doc/dev/FRONTEND_API_CALLS.md`
- 接口冒烟脚本：`scripts/verify_endpoints.py`
