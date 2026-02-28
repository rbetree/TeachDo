# TeachDo | 智能教学助手

![Status](https://img.shields.io/badge/Status-Active-success)
![Tech](https://img.shields.io/badge/Vue-3.5.24-brightgreen)
![Bundler](https://img.shields.io/badge/Vite-7.x-orange)
![License](https://img.shields.io/badge/License-MIT-green)

TeachDo 是一套面向教师的智能备课平台，当前仓库提供 **Vite + Vue 3 + TypeScript** 的完整本地工程，支持真实路由、构建与部署流程。React 版本已打 tag 归档，如需对照请按照迁移计划说明查阅，日常开发全部基于本 Vue 仓库。

---

## 📖 参考文档
- [teachdo_local_dev.md](./teachdo_local_dev.md)：本地开发流程、依赖管理与部署规范
- [../doc/dev/PLAN.md](../doc/dev/PLAN.md)：当前开发计划（入口）
- [../doc/dev/FRONTEND_API_CALLS.md](../doc/dev/FRONTEND_API_CALLS.md)：前端 API 调用与封装（services 层）

---

## 📌 项目现状
- ✅ 2025-12-10 完成 V1.1～V1.6：Vue 脚手架、Tailwind、Pinia、Router、i18n/Toast 已全部落地，`npm run lint && npm run typecheck && npm run build` 可稳定通过。
- ✅ 已移除登录/认证模块：当前默认免登录进入工作台，路由仅保留课程有效性校验与工作流能力。
- ⏳ 教学资料工作台（AI 大纲/教案/PPT/助教）仍在迭代：以 `../doc/dev/PLAN.md` 为准（过程性记录可参考 `../doc/dev/DEVELOPMENT_PLAN.md`）。
- 📌 React 旧仓库仅供参考，所有增量需求、Bug 修复与联调任务均以 Vue 工程为准；若需对照可通过 `git worktree` 拉取 `main` tag 版本。

---

## ✨ 核心功能
1. **课程工作台**：管理课程组、教学单元和知识库文件
2. **知识库 RAG**：上传教材/课标，驱动 LLM 检索增强生成
3. **AI 生成工作流**：大纲、教案、PPT 的端到端生成
4. **AI 助教**：面向具体课程上下文的智能问答

---

## 🧱 技术栈概览
- **构建工具**：Vite 7（DevServer 默认监听 5174）+ `vue-tsc` 构建前类型校验
- **框架**：Vue 3.5 + Vue Router（`createWebHistory`），Router 守卫用于课程有效性校验等前端导航约束
- **语言**：TypeScript，组件统一使用 `<script setup lang="ts">`
- **状态持久化**：Pinia + LocalStorage，同步主题、语言与课程上下文
- **UI 与交互**：Tailwind CSS 运行时模式、Lucide 图标、自定义 Toast/i18n
- **后端交互**：`services/` 封装 fetch/streaming 逻辑，统一通过相对路径 `/api` 访问（Dev：Vite proxy；Prod：Nginx 反代）

---

## 🚀 快速开始
1. **安装依赖**
   ```bash
   npm install
   ```
2. **配置环境变量**
   - 默认无需额外配置：前端统一走相对路径 `/api`，由 `vite.config.ts` 代理到后端 `http://127.0.0.1:6800`
   - 如需修改后端地址/端口，请调整 `vite.config.ts` 中的 `server.proxy['/api'].target`
3. **启动前端**
   ```bash
   npm run dev
   ```
   默认监听 `http://localhost:5174`（已在 `vite.config.ts` 配置，如需变更可自定义）。
4. **启动后端（TeachDo 后端服务，默认监听 `http://localhost:6800`）**
   - 建议按照 `teachdo_local_dev.md` 中的说明使用虚拟环境运行 `python start.py`
5. **构建/预览**
   ```bash
   npm run build
   npm run preview
   ```

---

## 🔧 部署与交付检查
- `npm run build` 产出 `dist/`，必要时 `npm run preview` 做最终验收
- 部署网关需开启 `historyApiFallback`，确保 Vue Router `createWebHistory` 刷新不 404
- 新增依赖、脚本或环境变量请同步在 README/teachdo_local_dev.md 记录
- 提交前检查 `services/*` 是否匹配最新后端 API

---

## ⚠️ 开发注意事项
1. **分层**：视图组件不得直接发起 `fetch`，统一走 `services/`
2. **依赖**：所有库通过 npm 安装并写入 `package.json`，禁止继续引用 CDN
3. **质量**：重要改动需自测（`npm run build`/lint），并在 PR 中记录后端联调状态
4. **路由**：统一使用 Vue Router `createWebHistory`，服务端需确保开启 `historyApiFallback`
5. **编辑器运行时**：`@editor` 相关全局插件仅在编辑器路由按需加载（见 `src/utils/editorRuntime.ts`）；如需在非编辑器页面使用 IconPark 组件/指令，请先确保已执行 `ensureEditorRuntimePlugins()`

---

## 📄 License
MIT License © TeachDo. 欢迎为开放教育社区贡献改进。
