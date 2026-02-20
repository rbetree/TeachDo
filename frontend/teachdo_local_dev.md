# TeachDo 本地开发工作流与规范（Vue + Vite 版本）

## 1. 背景与目标
TeachDo 目前以前端 **Vite + Vue 3 + TypeScript** 为主工程形态，目标是保证：
- 前端可独立运行（路由、构建、静态检查均可稳定通过）
- 与后端服务联调顺畅
- 代码与文档保持一致，避免遗留 React/旧脚手架描述导致误用

---

## 2. 环境准备
- **Node.js ≥ 18.18**（建议配合 `npm ci` 使用 `package-lock.json` 保障可复现）
- **Python/后端服务**：按后端仓库说明创建虚拟环境并启动后端（默认 `http://localhost:6800`）
- **前端依赖**：仓库根目录执行 `npm install` 或 `npm ci`
- **接口代理**：前端统一通过相对路径 `/api` 访问后端（开发环境由 `vite.config.ts` 代理到 `http://127.0.0.1:6800`）
  - 若后端端口/地址不同：修改 `vite.config.ts` 的 `server.proxy['/api'].target`

---

## 3. 依赖与资源管理
1. **统一使用 npm**：第三方库必须写入 `package.json` 并通过 npm 安装，避免临时引入或手动拷贝。
2. **锁定可复现**：依赖变更优先使用 `npm install`，CI/联调环境优先使用 `npm ci`。
3. **资源清理**：删除未使用的组件/工具/样式（例如脚手架残留），减少维护成本与误导。

---

## 4. 路由与运行模式
- 使用 **Vue Router** 的 `createWebHistory`（干净路径，无 `#/`）
- Vite DevServer 默认监听 `http://localhost:5174`（见 `vite.config.ts`）
- 生产部署通过 `npm run build` 生成 `dist/`
- 部署到静态服务器/网关时需开启 `historyApiFallback`（未知路径回退到 `index.html`），避免刷新 404

---

## 5. 日常开发流程
1. 安装依赖：`npm ci`
2. 启动前端：`npm run dev`
3. 并行启动后端：确保后端可访问（例如 `GET http://127.0.0.1:6800/healthz`，或你在 `vite.config.ts` 中配置的 proxy target）
4. 分层约束：视图组件不得直接 `fetch`，统一通过 `src/services/*`
5. 提交前至少执行：`npm run lint && npm run typecheck && npm run build`

---

## 6. 验证与质量保障
- **构建校验**：`npm run build` 必须通过（避免仅在 dev 可运行）
- **联调记录**：后端接口调整需同步更新 `src/services/aiService.ts`，并在 PR 中记录联调步骤与关键截图/日志
- **安全检查**：避免提交 `.env.local`、临时凭据或调试脚本；确保仓库内无敏感硬编码

---

## 7. 常见问题与处理
1. **刷新后 404**：检查部署环境是否启用 `historyApiFallback`（回退到 `index.html`）
2. **后端不可用**：确认 `vite.config.ts` 的 `server.proxy['/api'].target` 是否正确、后端 `/healthz` 是否可访问；如绕过 `/api` 直连后端再检查 CORS
3. **本地存储不兼容**：若调整 `CourseGroup/CourseUnit` 结构，需提供兼容/迁移逻辑，或提醒清空 localStorage
