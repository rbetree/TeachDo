# TeachDo Agent Context

TeachDo 是面向教师的智能备课平台，主链路为 Outline -> 教案/PPT 生成 -> 编辑器导出。

## Essential Commands

- 一键启动（推荐）：`cp env_template.txt .env && python3 start.py`
- 后端全服务：`cd backend && pip install -r requirements.txt && python3 start_backend.py`
- TeachDo 前端开发：`cd frontend && npm i && npm run dev`
- 前端质量校验：`cd frontend && npm run typecheck && npm run lint && npm run build`
- 后端测试：`venv/bin/python -m pytest backend -q`（或激活 venv 后执行 `pytest backend -q`）
- 接口冒烟：`python3 scripts/verify_endpoints.py`

## Repository Structure

- `backend/`: FastAPI 多服务（`main_api`、`simpleOutline`、`slide_agent`、`personaldb`、`mock_api`）
- `frontend/`: TeachDo 唯一前端入口（Vue 3 + Vite + TS）
- `docs/`: 用户文档（VitePress 站点）
- `doc/`: 开发者文档（原始维护文档）
- `scripts/`: 校验与辅助脚本
- `template/`: PPT 模板资源
- `var/`、`logs/`、`notes/`: 运行时数据与本地记录（含 gitignore）

## Skills

| Skill | When to use |
|-------|-------------|
| [repo-guidelines](.github/skills/repo-guidelines/SKILL.md) | 需要具体代码规范、测试约束、提交/PR 规则、环境与安全配置细节时加载 |
| ui-ux-pro-max | 进行 UI/UX 相关设计与前端体验优化、页面/组件开发时加载 |

## Key Entry Points

- 启动编排：`start.py`
- 主 API（BFF）：`backend/main_api/main.py`
- 大纲服务：`backend/simpleOutline/main_api.py`
- PPT 内容服务：`backend/slide_agent/main_api.py`
- KB 服务：`backend/personaldb/main.py`
- 前端入口：`frontend/src/main.ts`
- 前端路由：`frontend/src/router/index.ts`
- 开发计划：`doc/dev/PLAN.md`
