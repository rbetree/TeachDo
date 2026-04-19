---
layout: home
title: TeachDo
titleTemplate: false

hero:
  name: TeachDo
  text: 教师备课工作台
  tagline: 以课程与单元为工作流单元，串联大纲、教案、PPT 的流式生成，并结合知识库增强、助教问答与独立编辑器导出能力。
  image:
    src: /images/01-workspace.png
    alt: TeachDo 工作台首页
  actions:
    - theme: brand
      text: 快速开始
      link: /guide/getting-started
    - theme: alt
      text: 功能介绍
      link: /guide/features
    - theme: alt
      text: 文档索引
      link: /about

features:
  - title: 主链路完整
    details: 围绕教师备课过程构建 Outline -> 教案 / PPT 生成 -> 编辑器导出的完整闭环。
  - title: 流式生成体验
    details: 大纲、教案、PPT 和助教问答均支持 SSE 流式返回，便于边生成边调整。
  - title: 知识库增强
    details: 支持上传教学素材、沉淀生成产物，并在生成过程中按范围注入上下文。
  - title: 编辑与导出分离
    details: 工作台负责只读预览与流程推进，独立编辑器负责精修内容并导出 PPTX。
---

## 平台概览

TeachDo 是教师备课工作台。系统以“课程 / 单元”为工作流单元，支持大纲、教案、PPT 的流式生成，以及知识库增强、助教问答和独立编辑器导出。

主链路聚焦在教师真实备课场景：

- 先围绕主题生成并编辑课程大纲
- 基于大纲继续生成教案并导出标准 `.docx`
- 基于同一份上下文继续生成 PPT 内容与页面
- 在独立编辑器内完成精修、预览和最终导出

## 核心能力

- **大纲生成**：基于主题输入流式生成大纲，并支持版本对比与保存。
- **教案生成**：基于课程大纲生成教案内容，并支持导出标准文档格式。
- **PPT 生成**：支持模板选择、增量页生成与工作台只读预览。
- **助教问答**：结合教学资料与知识库文件进行上下文问答。
- **知识库管理**：支持上传素材、向量化检索、生成产物归档与引用范围控制。
- **独立编辑器**：用于完成 PPT 精修、导出和产物落盘。

## 项目结构

```text
TeachDo/
├── backend/                 # FastAPI 多服务
│   ├── main_api/            # BFF / Gateway
│   ├── simpleOutline/       # 大纲生成服务
│   ├── slide_agent/         # PPT 内容生成服务
│   ├── personaldb/          # 知识库服务
│   └── mock_api/            # 联调与冒烟支持
├── frontend/                # Vue 3 + Vite + TypeScript 前端
├── docs/                    # 用户文档（VitePress 站点）
├── doc/                     # 开发者维护文档
└── scripts/                 # 校验脚本与工具
```

## 常用入口

- 新环境启动：前往 [快速开始](/guide/getting-started)
- 了解产品能力：前往 [功能介绍](/guide/features)
- 浏览完整用户文档：前往 [文档索引](/about)
- 查看界面截图：前往 [截图展示](/guide/screenshots)
- 理解系统拆分：前往 [项目架构](/dev/architecture)
- 查询对接变更：前往 [更新日志](/changelog)
