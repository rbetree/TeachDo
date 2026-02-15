# TeachDo 前端改进建议

本文档整理了对 `teachdo/` 前端代码的重点审查结果，用于指导后续迭代。所有建议均基于当前仓库（`/teachdo`）内源码。

## 1. 课程数据只存内存，刷新即丢
- 现状：`teachdo/App.tsx` 中课程组数据通过 `useState` 写死为示例数组，刷新页面或切换设备均无法保留成果。
- 风险：无法与后端知识库同步，用户生成的大纲/教案/课件均为临时态。
- 建议：尽快接入后端课程 API（若后端尚未准备，可临时落地到 `localStorage`/IndexedDB），并配合 React Query/SWR 做统一数据获取、缓存和乐观更新，避免在顶层组件到处传递 setState。

## 2. AI 助教缺少最新上下文
- 现状：`teachdo/views/AssistantView.tsx:40-45` 调用 `aiService.chatWithAssistant` 时传入的 `messages` 不包含刚输入的 `userMsg`，因为 `setMessages` 是异步执行。
- 风险：后端永远拿不到用户刚刚输入的问题，导致回答上下文错乱。
- 建议：组装 `const history = [...messages, userMsg];` 传入服务端，并把“模型占位消息”的创建与历史记录更新合并到一次 `setMessages`，以免流式响应时顺序错乱。

## 3. 构建链与运行时不一致
- 现状：`package.json` 依赖 React 18，但 `index.html` 又通过 importmap 引入 React 19 和 Tailwind CDN。
- 风险：同一页面可能加载两份 React，生产环境无法离线构建，也无法对 Tailwind 做 tree-shaking。
- 建议：移除 CDN/importmap，所有依赖统一走 npm；新增 `tailwind.config.cjs` 与 `postcss.config.cjs`，通过 Vite 插件完成样式构建，确保 bundle 可控、可缓存。

## 4. CourseWorkspace 体积巨大
- 现状：`teachdo/views/CourseWorkspace.tsx` 同时包含侧栏、单元增删、Tab 切换、AI 助手抽屉等，文件超 300 行，状态集中在一个组件里。
- 风险：任何局部输入都会触发整个工作区重渲染，难以单独测试或复用。
- 建议：拆分为 `UnitSidebar`、`WorkspaceTabs`、`AssistantDrawer` 等子组件，配合 `React.memo`/`useMemo` 控制渲染范围；单元列表建议增加虚拟滚动或最少确保 key 稳定，保证大课程序列下的性能。

## 5. 健康检查兼容性差
- 现状：`teachdo/components/TopBar.tsx` 依赖 `AbortSignal.timeout` 检查 6800 端口，该 API 在 Safari 与部分 Chromium 版本缺失；同时所有组件都会单独轮询健康接口。
- 风险：在非兼容浏览器上直接抛错；多组件轮询会导致重复请求、跨域问题。
- 建议：改为手动 `AbortController + setTimeout`，并把健康检查封装到 `aiService` 或 SWR，通过共享状态下发给需要的组件，减少轮询次数；同时在 UI 层缓存最近一次结果，失联时再触发即时重试。

---

以上建议优先级顺序：先修复 AI 助手上下文（功能性 bug），其次是课程持久化与构建一致性，再处理组件拆分与健康检查优化。
