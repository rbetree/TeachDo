# 前端未使用页面和结构审查报告（维护版）

> **审查日期**：2026-03-20  
> **审查范围**：`frontend/src`  
> **审查目的**：对齐 TeachDo 当前路由/页面入口，识别明确“未引用/可清理”的遗留文件，避免文档与实现口径长期漂移。

---

## 1. 当前路由与入口（以代码为准）

- 路由配置：`frontend/src/router/index.ts`
- 工作台路由（TeachingMaterial）：
  - `/`：教学资料选择页（`TeachingMaterialSelectionView.vue`）
  - `/material/:materialId`：工作台容器（会自动归一化到 `outline` tab）
  - `/material/:materialId/:tab`：工作台四个 tab（`outline/lesson/ppt/assistant`）
  - `/material/:materialId/ppt/editor`：独立 PPT 编辑器

> 说明：旧版 `/outline`、`/ppt`、`/editor`、`/app/:id?` 等路由不属于 TeachDo 当前路由结构，应以历史文档为准（通常位于 `doc/dev/history/**`）。

---

## 2. 当前在用的 View 文件

TeachDo 当前 `frontend/src/views/` 仅保留以下入口（其余能力通过组件/按需加载提供）：

- `frontend/src/views/TeachingMaterialSelectionView.vue`
- `frontend/src/views/TeachingMaterialWorkspaceView.vue`
- `frontend/src/views/PPTEditorView.vue`（内部按需加载 `frontend/src/views/pptEditor/PPTEditorRuntime.vue`）
- `frontend/src/views/AboutView.vue`
- `frontend/src/views/SettingsView.vue`

---

## 3. 已清理项（变更记录）

- ✅ 已清理：`frontend/src/editor-runtime/components/OutlineEditor.vue`
  - 原因：全仓未发现引用，且仅出现在旧文档的过期路径引用中。
- ✅ 已清理：`frontend/src/i18n/index.ts` 中历史遗留的 `assistant/lesson in_progress` 文案
  - 目的：避免“功能建设中”的误导，与代码实现口径保持一致。

---

## 4. 验收（建议每次清理都跑）

- 路由无断链：`frontend/src/router/index.ts` 中不存在指向不存在 view 的 import。
- 前端基础校验通过：`cd frontend && npm run typecheck && npm run build`。
- 如涉及后端联调：`python3 scripts/verify_endpoints.py --base-url http://127.0.0.1:6800`。
