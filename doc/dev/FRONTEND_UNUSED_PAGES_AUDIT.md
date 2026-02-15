# 前端未使用页面和结构审查报告（修订版）

> **审查日期**: 2025-11-30  
> **审查范围**: `/frontend` 目录  
> **审查目的**: 识别流程中不使用的页面及结构

---

## 📋 执行摘要

根据对前端代码和开发计划文档的全面审查，并结合用户反馈，得出以下结论：

### 🔴 关键发现
1. **2个页面已被重构为组件** (`Loading` 和 `Share` 功能)
2. **3个目录用途已明确** (`APP`, `Mobile`, `Screen`)
3. **1个原型目录冗余** (`frontend-prototype`)

---

## 🎯 核心业务流程（已确认）

核心流程保持不变，但 `Loading` 页面已被 `Loading` 组件取代。

```
Home (/) 
  ↓ 主题输入或文档上传
Outline (/outline) 
  ↓ 生成和编辑大纲 (使用 Loading 组件)
PPT (/ppt) 
  ↓ 选择模板
Editor (/editor) 
  ↓ 编辑演示文稿
Screen (放映模式)
  ↓ 放映演示
```

---

## 🔍 详细审查结果

### 1. 路由配置 vs 实际文件

| 路由 | 文件路径 | 状态 | 说明 |
|------|---------|------|------|
| `/` | `views/Home.vue` | ✅ 存在 | 主页 |
| `/outline` | `views/Outline/index.vue` | ✅ 存在 | 大纲编辑页 |
| `/ppt` | `views/PPT/index.vue` | ✅ 存在 | 模板选择页 |
| `/editor` | `views/Editor/index.vue` | ✅ 存在 | 编辑器页面 |
| `/app/:id?` | `views/APP/index.vue` | ✅ 存在 | 分享/从ID生成入口 |

### 2. 用途已明确的页面/目录

#### ✅ APP 页面 (`/app/:id?`)

- **功能**: 一个特殊的PPT生成入口，通过URL中的 `id` 参数直接调用后端 `AIPPTByID` 接口生成PPT。
- **用途**: 用于“分享”或“从链接继续”的功能。

#### ✅ Mobile 目录 (`views/Mobile/`)

- **功能**: 移动端适配视图。`index.vue` 根据 `mode` 动态加载 `MobileEditor`, `MobilePlayer`, 或 `MobilePreview`。
- **用途**: 移动端体验。

#### ✅ Screen 目录 (`views/Screen/`)

- **功能**: 演示文稿的放映模式。
- **调用方式**: 在 `App.vue` 中通过 `v-if="screening"` 条件渲染。`screening` 状态由 `useScreening` hook 控制，并通过快捷键（F5）触发。

### 3. 已重构为组件的页面

#### ✅ Loading 页面

- **状态**: 独立的 `views/Loading.vue` 页面已不存在。
- **替代方案**: `frontend/src/components/common/Loading.vue` 组件。
- **使用场景**: 在 `Outline/index.vue` 中用于显示“正在生成大纲”的状态。

#### ✅ Share 页面

- **状态**: 独立的 `views/Share.vue` 页面已不存在。
- **替代方案**: 分享功能很可能已整合到 `views/APP/index.vue` 中。

### 4. 冗余目录

#### 📁 frontend-prototype/

- **位置**: 项目根目录 `archive/frontend-prototype/`
- **内容**: 设计原型参考文件。
- **状态**: 开发计划显示阶段1-4已完成，原型已被实现。
- **建议**: 移动到 `doc/prototypes/` 作为参考文档，或归档。

---

## 📊 统计数据

### 页面使用情况

| 类别 | 数量 | 说明 |
|------|------|------|
| 核心业务页面 | 5 | Home, Outline, PPT, Editor, APP |
| 已重构为组件 | 2 | Loading, Share |
| 活跃的功能目录 | 2 | Mobile, Screen |
| 原型文件目录 | 1 | frontend-prototype |

---

## 🎯 优先级建议

### 🟡 中期处理（1个月内）

1. **整理 frontend-prototype 目录**
   - 移动到 `doc/prototypes/` 或归档。

---

## ✅ 验收标准

- [ ] `frontend-prototype` 已整理或归档。
- [ ] 更新 `doc/dev/FRONTEND_UNUSED_PAGES_AUDIT.md` 为最终版本。

---

**报告生成时间**: 2025-11-30 13:50 (UTC+8)
