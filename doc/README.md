# AI2PPT 文档索引

> 约定：
> - `doc/`：官方文档（建议提交到 git，协作者 clone 后即可阅读）
> - `notes/`：个人资料/组会/毕设材料（默认不提交）
> - `var/`：运行期数据（缓存/临时文件，默认不提交）
> - `logs/`：运行日志（默认不提交）

## 1. 建议阅读路径（从快到全）

1. 先读：**架构与能力边界**（见第 2 节）
2. 再读：**后端接口/部署**（见第 3 节）
3. 然后：**前端实现**（见第 4 节）
4. 最后：**模板/结构**（见第 6 节）+ **部署与运行入口**（见第 7 节）
5. `legacy/` 仅在排查历史/对照抓包记录时使用（见第 10 节）

## 2. 架构与能力边界（维护版）

- 系统架构：`doc/architecture/PROJECT_ARCHITECTURE.md`
- 功能 → API / 页面映射：`doc/architecture/FEATURE_API_OVERVIEW.md`

## 3. 后端（接口 / 部署 / 服务拆分）

- 后端文档导航：`doc/backend/README.md`
- API 参考（以当前实现为准）：`doc/backend/backend_api_reference.md`
- 后端部署与运行：`doc/backend/backend_deployment.md`
- 后端架构概述：`doc/backend/backend_architecture.md`
- 后端架构评估与优化报告：`doc/backend/BACKEND_ARCH_REPORT.md`
- 各服务说明：
  - `doc/backend/main_api_service.md`
  - `doc/backend/simpleOutline_service.md`
  - `doc/backend/slide_agent_service.md`
  - `doc/backend/personaldb_service.md`

## 4. 前端（架构 / API 调用）

- 前端统一技术文档（维护版）：`doc/dev/FRONTEND_GUIDE.md`
- 前端 API 调用与封装（services 层）：`doc/dev/FRONTEND_API_CALLS.md`
- 前端未使用页面审计：`doc/dev/FRONTEND_UNUSED_PAGES_AUDIT.md`

## 5. 开发与配置（维护版）

- 前端重构计划（过程记录）：`doc/dev/DEVELOPMENT_PLAN.md`
- 环境变量与统一配置：`doc/dev/ENV_GUIDE.md`
- 深入巡检优化清单：`doc/dev/REPO_OPTIMIZATION_AUDIT.md`

## 6. 模板与数据结构

- 模板制作与导入：`doc/Template.md`
- Slide JSON 结构约定：`doc/PPT_Structure.md`

## 7. 部署与运行（入口）

- 根目录一键启动（本机）：`README.md`
- 生产部署说明：`README_PRODUCTION.md`
- Docker 部署说明：`doc/DockerDeploy.md`

## 8. Prompt / 模型（维护版）

- 提示词结构与数据流：`doc/ai/PROMPT_STRUCTURE.md`
- Prompt 示例/补充：`doc/ai/PROMPT_EXAMPLES.md`
- 自定义模型配置：`doc/ai/CUSTOM_MODEL.md`
- GRPO/训练笔记：`doc/ai/GRPO_TRAINING.md`

## 9. 变更记录

- 变更记录：`doc/CHANGES.md`

## 10. 临时/过时资料（legacy，仅供参考）

- 归档入口：`doc/legacy/README.md`
