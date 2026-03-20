# TeachDo 项目沿革与历史命名（维护版）

> 更新：2026-03-20  
> 目的：解释仓库中仍可能出现的历史命名（旧项目名/旧端点名/旧类型名），避免对接与协作时产生误解。

---

## 1) 沿革概述

TeachDo 的部分能力（尤其是“从大纲生成 PPT 内容”的链路与编辑器运行时）来自早期项目的演进与复用。为了降低迁移成本，仓库中保留了少量历史命名与兼容入口，但 **对外的事实口径以现行代码与维护文档为准**。

---

## 2) 常见历史命名（仍可能遇到）

### 2.1 `AI2PPT`

历史项目名，主要出现在：
- `doc/dev/history/**`、`doc/legacy/**`（归档文档/抓包记录/研究资料）
- 少量服务文档的“沿革说明”

建议：对接与实现阅读优先看维护版文档，不依赖归档口径。

### 2.2 `AIPPT`（Slide JSON Schema 的历史命名）

`AIPPT` 在本仓库中通常指“PPT 生成链路产出的 Slide JSON 数据结构”（而不是产品名）。它作为历史命名仍存在于：
- `frontend/src/editor-runtime/types/AIPPT.ts`
- `frontend/src/editor-runtime/aippt/**`

为了对外口径更清晰，前端已提供中性别名：
- `frontend/src/editor-runtime/types/SlideSchema.ts`

### 2.3 `/tools/aippt*`（后端端点的历史命名）

`main_api` 早期端点以 `/tools/aippt*` 命名。现行推荐端点为：
- `POST /tools/outline`（大纲生成；兼容别名：`/tools/aippt_outline_unified`）
- `POST /tools/ppt`（PPT 内容生成；兼容别名：`/tools/aippt`）

兼容端点会在可预见周期内保留，便于渐进迁移。

---

## 3) 现行对接入口（建议以此为准）

- 后端接口契约：`doc/backend/backend_api_reference.md`
- 功能 → API / 页面映射：`doc/architecture/FEATURE_API_OVERVIEW.md`
- 前端路由与入口：`frontend/src/router/index.ts`

