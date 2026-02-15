# TeachDo AI Studio 无构建开发规范

## 1. 项目定位
**TeachDo** 是 ai2ppt 教学智能助手的前端子项目，本文件针对 AI Studio 远程开发形态。该环境用于“即写即看”的教学演示，需要在浏览器内直接加载 ES Modules（无 Vite/Vercel 构建），并与后端多服务联动展示集成状态。为保证与本地 Vite 工程共存，AI Studio 版本固定使用 **React 18 + HashRouter + Importmap**，所有依赖通过 CDN 拉取。

### 1.1 核心技术栈（必须遵循）
| 模块 | 版本/说明 | 备注 |
| --- | --- | --- |
| React | `18.2.0` | 通过 Importmap 引入，禁止升级到 19 |
| React DOM | `18.2.0` | `?deps=react@18.2.0` 锁定版本 |
| React Router DOM | `6.22.3` | `HashRouter` 模式 |
| TypeScript | ESNext | 由 AI Studio 转译，不需要打包 |
| UI/样式 | Tailwind CDN + 自定义 CSS | 配置存放在 `index.html` |
| Icon/PPT | `lucide-react@0.344.0`、`pptxgenjs@3.12.0` | 通过 CDN 加载 |

### 1.2 必须遵循的规范
- **前端职责**：此分支只负责 TeachDo 前端展示逻辑，必须与 ai2ppt 后端（`main_api`、`simpleOutline`、`slide_agent`、`personaldb`）保持接口契约一致。
- **HashRouter 约束**：所有路由、跳转、面包屑都基于 `#/path`，严禁引入依赖 `BrowserRouter` 的历史模式代码。
- **Importmap 唯一来源**：运行时依赖只能配置在 `index.html` 的 `importmap` 中，新增依赖需同步在此文档登记。
- **“集成说明”页面同步**：`TopBar` 中的 “集成说明” 链接指向 `/about`（实现于 `teachdo/views/AboutView.tsx`），用于展示服务诊断、接入流程和 API 参考。任何后端接口、端口、参数文案的更新都要**同时**更新 AboutView 与本规范的相关章节，保持 AI Studio 预览与仓库文档一致。

---

## 2. 开发环境与入口
1. **工作区要求**：打开 Google AI Studio 中的 TeachDo Workspace，确保启用 *No-Build + Importmap* 预览模式。
2. **文件入口**：`teachdo/index.html` 是唯一入口，预览面板会直接载入此文件；`index.tsx`、`App.tsx`、`components/*` 等源码可直接在浏览器解释（AI Studio 会自动转译 TS/JSX）。
3. **远程运行**：无需执行 `npm install` / `npm run dev`。如需获取类型提示，可在 AI Studio 配置 minimal language server（可选）。
4. **后端连接**：在预览器中将 API 指向公共/本地可访问的 ai2ppt 服务，必要时通过浏览器代理或公开测试接口。

---

## 3. 依赖管理（Importmap）
1. **统一入口**：所有第三方库必须写入 `index.html` 的 `<script type="importmap">`，不允许在 `package.json` 中添加运行时依赖。
2. **CDN 规则**：
   - 默认使用 `https://esm.sh`，必要时可增加镜像（如 `https://aistudiocdn.com`）。
   - **版本需锁定**：使用 `react@18.2.0`、`react-dom@18.2.0`、`react-router-dom@6.22.3` 等固定号段，禁止 `latest`。
   - 所有依赖 React 的库需要在 URL 上追加 `?deps=react@18.2.0,react-dom@18.2.0`，避免 React 版本漂移。
3. **新增依赖流程**：
   1. 查询目标库在 `esm.sh` 的可用版本；
   2. 将 importmap 中的 `"包名": "URL"` 项添加到 JSON，并在备注（HTML 注释或文档）中说明用途；
   3. 若库内部又依赖 React，必须确认 `deps` 参数已传递 React 18；
   4. 预览中手动刷新，观察是否有 `Minified React error` 或网络 404。
4. **类型/工具依赖**：仅在本地工程 `package.json` 中维护（例如 `@types/*`、`vite`）。AI Studio 无需安装。

---

## 4. 路由与预览限制
- 预览沙箱无法拦截浏览器 404，因此 **必须使用 `HashRouter`**。`teachdo/App.tsx` 中的顶层 Router 在 AI Studio 分支保持：
  ```tsx
  import { HashRouter } from 'react-router-dom';
  ...
  <HashRouter>
     <Routes>...</Routes>
  </HashRouter>
  ```
- 页面跳转统一使用 `#/path`（React Router 会自动处理），不要依赖 `historyApiFallback`。
- 外部链接如果需要返回 AI Studio 预览页，使用相对 `#/` 路径，并避免 `window.location.href` 直接刷新。
- 预览面板如需全屏，请使用 AI Studio 提供的 Preview URL（通常形如 `https://*.aistudio.google.com/preview/...`），不可直接访问静态服务器。

---

## 5. 日常开发流程（AI Studio）
1. **打开工作区**，拉取最新 Git 代码（或通过 AI Studio 的 Git 面板同步）。
2. **确认 importmap**：检查 React 版本仍为 18.2.0，若有 `react/`、`react-dom/` 额外配置，须保证不会被错误引用。
3. **启动预览**：在编辑器中打开 `index.html`，选择 “Preview” 即可加载，用 Chrome DevTools 观察网络请求。
4. **编码规范**：
   - 分层结构 (`components/`, `views/`, `services/`) 与本地工程一致；
   - Service 层请求 AI 后端时需考虑远程 URL（通常是公网网关），谨慎存储密钥；
   - 由于没有打包流程，避免引入仅 CommonJS 提供的库。
5. **调试与日志**：通过浏览器控制台查看错误，必要时在 `services/aiService.ts` 中添加临时日志（完成后删除）。
6. **变更记录**：每完成一个功能，更新 `doc/legacy/teachdo_aistudio_dev.md` 或 `notes/logs/note.md` 中的同步清单，提醒本地同事需要做的包管理/Router 改动。

---

## 6. 与本地 Vite 版本的同步
1. **AI Studio → 本地**
   - 提交前在描述中列出：新增/修改的 Importmap 条目、需要在本地 npm 安装的包、以及与 HashRouter 相关的逻辑；
   - 若修改了样式配置（Tailwind Config、字体链接等），同步更新 `teachdo/index.html`，确保本地构建同样生效；
   - 任何对 `App.tsx` Router 层的改动，须备注“本地版本需改回 BrowserRouter”提醒。
2. **本地 → AI Studio**
   - 合入本地代码前，先将 `BrowserRouter` 切换回 `HashRouter`；
   - 删除依赖于 Vite 的绝对路径导入（如 `@/components/...`）或配合 import alias，AI Studio 无法解析；
   - 如果本地新增了 service/utility，确保没有引入 Node-only API（`path`, `fs` 等）。
3. **同步清单模板**
   - [ ] 是否存在新的第三方包？（写明 Importmap URL）
   - [ ] 是否包含仅 BrowserRouter 支持的逻辑？需要提供 HashRouter 替代。
   - [ ] API Base URL 在云端是否可访问？若需代理请提供说明。
   - [ ] 是否引用了本地资源（如 `/src/assets/*`）？AI Studio 需保证相对路径可读。

---

## 7. 注意事项
1. **React 18 限制**：AI Studio 版本必须固定 React 18，否则部分 CDN 会回退到 React 19，引发 Hooks 校验错误。
2. **HashRouter 专属逻辑**：不要在 AI Studio 里写 `window.history.pushState` 等会破坏 `#/` 路由的代码。
3. **网络策略**：AI Studio 可能无法访问本地 `localhost`，需要通过 `ngrok`、云服务器或后端部署在公网环境。
4. **安全**：禁用任何硬编码密钥，必要时将敏感值放在浏览器 localStorage 的 Mock 中并标记“仅演示”。
5. **提交要求**：所有远程更改最终仍需通过 Git 合并回主仓库，提交信息注明“aistudio”方便区分。

通过以上流程，可以在 AI Studio 中获得快速预览体验的同时，确保与本地 Vite 版本保持一致，避免依赖、路由和构建模式的冲突。
