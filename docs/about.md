# 文档索引

TeachDo 采用双目录文档结构：

- `docs/`：用户文档与 VitePress 站点页面
- `doc/`：开发者维护文档与历史资料，不进入 VitePress

## 用户文档

- [快速开始](/guide/getting-started)：环境准备、启动方式与常用校验命令。
- [功能介绍](/guide/features)：主链路能力、系统模块与核心特性。
- [截图展示](/guide/screenshots)：平台主要界面与操作场景截图。
- [项目架构](/dev/architecture)：对外公开的稳定架构说明页。
- [更新日志](/changelog)：会影响使用、对接与迁移的关键变更。

## 开发者文档

开发者维护文档已从站点源码中拆回仓库根目录的 `doc/`，用于保存：

- AI 与 Prompt 文档：`doc/ai/`
- 架构维护文档：`doc/architecture/`
- 后端文档：`doc/backend/`
- 开发计划与历史记录：`doc/dev/`
- 历史归档资料：`doc/legacy/`
- 模板、部署与变更记录：`doc/Template.md`、`doc/PPT_Structure.md`、`doc/DockerDeploy.md`、`doc/CHANGES.md`

如果你在本地仓库内查阅开发文档，请直接从 `doc/` 目录进入，而不是从 VitePress 站点导航。
