# TeachDo 本地开发工作流与规范（已归档）

> ⚠️ 本文件面向旧的 React/Vite 版本；当前 TeachDo 前端为 **Vue 3 + Vite**：
> - 维护版入口：`frontend/README.md`
> - 本地开发规范：`frontend/teachdo_local_dev.md`
>
> 本文仅用于历史对照与排查遗留问题。

## 1. 背景与目标
TeachDo 在仓库中提供了一套 **Vite + React 19 + TypeScript** 的现代工程化脚手架，用于本地高效迭代、联调和构建。该模式与 AI Studio 的无构建版本（React 18 + Importmap + HashRouter）存在显著差异，因此本规范用于指导在本地拉起完整工程、与后端联调、并与远程无构建版本保持同步。

---

## 2. 环境准备
- **Node.js ≥ 18.18**，推荐配合 `corepack` 管理包管理器，保持 `package-lock.json` 与 `package.json` 一致。
- **Python/后端服务**：`python3 -m venv venv && source venv/bin/activate` 后执行 `python start.py`，或进入 `backend` 使用 `python start_backend.py`。
- **前端依赖**：在 `teachdo/` 目录执行 `npm install`，所有运行时/构建依赖由 `package.json` 管理。
- **环境变量**：在 `teachdo/.env.local`（或 shell）中配置 `VITE_API_BASE=http://localhost:6800` 等变量，前端仅能读取 `VITE_` 前缀。

---

## 3. 依赖与资源管理
1. **统一 npm 管理**：任何第三方库（如 `lucide-react@0.344.0`、`pptxgenjs@3.12.0`）必须写入 `package.json` 并通过 `npm install` 安装，不允许继续引用远程 CDN。
2. **React 版本**：保持 `react@^19.2.1`、`react-dom@^19.2.1`，升级需同步 `vite.config.ts`、类型定义和测试。
3. **移植远程依赖**：当 AI Studio 中新增 Importmap 依赖时：
   - 将 CDN 地址中的包名与版本抄录到 `package.json`；
   - 运行 `npm install <package>@<version>`；
   - 检查是否需要 `npm install -D @types/<package>`；
   - 删除/忽略 `index.html` 中对应 CDN 引用。
4. **静态资源**：Tailwind CDN 与字体可共用（`teachdo/index.html` 中的 `tailwind.config` 需保持一致），但若在本地改动，请将配置同步回远程文件。

---

## 4. 路由与运行模式
- 本地必须使用 **`BrowserRouter`** 以支持真实路径、配合后端反向代理。请在 `teachdo/App.tsx` 中将 `HashRouter` 替换为 `BrowserRouter`，并确认环境切换不会被提交到远程 HashRouter 分支（详见同步章节）。
- Vite DevServer 默认监听 `http://localhost:5173`，通过 `vite.config.ts` 可指定 `server.host` 与 `server.port`。
- 生产部署通过 `npm run build` 得到 `dist/`，需要由网关或静态服务器配置 `historyApiFallback` 将 404 回退到 `index.html`。

---

## 5. 日常开发流程
1. `git pull`，确保获取最新远程（含 AI Studio）变更。
2. `npm install`（必要时 `npm ci`）与 `npm run dev`，确认本地页面可访问。
3. 启动后端：`python start.py` 或 `python start_backend.py`，校验 API 正常。
4. 编码时遵循 `components / views / services` 分层，不在视图中直接 `fetch`，统一走 `services/aiService.ts`。
5. 自测：`npm run lint`（若存在）、`npm run build`。构建完成后使用 `npm run preview` 复核。
6. 产生新依赖或 Tailwind 配置时，记录需要同步到 AI Studio 的操作（见第 6 节）。
7. 提交前确认 `App.tsx` 已切回 `HashRouter`（如果需要同时为远程服务），避免破坏远程预览。

---

## 6. 与 AI Studio 无构建版本的同步
> 目标：保持 `teachdo/index.html`（Importmap + HashRouter）与 `src` 目录的业务逻辑一致。

1. **远程 → 本地（拉取更改）**
   - 对比 AI Studio 提交的 `index.html`、`components/` 等文件；
   - 如果远程新增 CDN 依赖，按照第 3 节流程安装 npm 包，并在 `App.tsx` 中继续使用 BrowserRouter；
   - 检查 HashRouter 专属写法（如 `#/path` 链接），根据 Router 模式调整为 `BrowserRouter` 需要的路径；
   - 更新类型文件/工具函数，运行 `npm run build` 确认无误。

2. **本地 → 远程（推回更改）**
   - 保证业务逻辑文件兼容 HashRouter（避免 `useNavigate` 中出现 `basename` 依赖 BrowserRouter 才存在的逻辑）；
   - 在提交供 AI Studio 使用的版本前，将 `App.tsx` 中 Router 切回 `HashRouter`（可用 git stash/patch 管理）。
   - 若新增依赖，更新 `index.html` 的 Importmap：使用 `https://esm.sh/<package>@<version>?deps=react@18.2.0,react-dom@18.2.0` 并标注固定版本。
   - 确认 `index.tsx`、`metadata.json` 等文件未引入仅兼容 Vite 的语法。

3. **同步清单**
   - [ ] Router 模式已与目标环境匹配（本地：BrowserRouter；AI Studio：HashRouter）。
   - [ ] 第三方依赖已双向更新（npm vs Importmap）。
   - [ ] Tailwind 配置块保持一致。
   - [ ] `services/aiService.ts` 中的 API 变更两边一致，必要时提供 Mock。

---

## 7. 验证与质量保障
- 本地改动必须通过 `npm run build`，以确保打包流程仍可运行（AI Studio 仅能原生加载，无法帮你发现构建问题）。
- 对后端交互代码，建议使用 `jest`/`vitest`（可选）覆盖核心服务逻辑，或在 PR 中提供详细手动测试记录。
- 变更 Router/状态持久化时，至少验证以下场景：刷新课程详情页、SSE 流式接口、PPT 导出、深色模式切换。
- 与远程联调前，手动检查 `.env.local`、`vite.config.ts` 是否携带敏感信息，避免推送。

---

## 8. 常见问题与处理
1. **刷新报 404**：确认生产环境服务器启用了 `historyApiFallback`，或在本地构建阶段使用 `BrowserRouter` 的 `basename` 与后端路径对齐。
2. **双版本 React 冲突**：当远程引入 React 18 依赖时，本地需检测是否也被 npm 引入；若库暂不支持 React 19，则在本地使用 `react@18.2.0` 并记录风险。
3. **HashRouter 残留**：合并 AI Studio 代码后，若忘记切回 `BrowserRouter` 会导致前端部署路径带 `#`。请在 git diff 中专门检查 `App.tsx`。
4. **后端 CORS**：默认后端允许 `http://localhost:5173`，若修改端口需同步 `backend/.env` 或 `main_api` 配置。

遵循以上流程，即可确保本地 Vite 版本与 AI Studio 无构建版本长期保持一致，避免路由、依赖或构建差异带来的联调问题。
