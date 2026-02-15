# `main_api` 服务文档

## 1. 概述

`main_api` 服务是整个 AI-to-PPT 后端系统的核心入口和 API 网关。它基于 FastAPI 构建，负责接收来自前端应用的所有请求，并将这些请求路由到相应的下游微服务（Agent），最后将处理结果返回给前端。

## 2. 角色和职责

`main_api` 的主要职责包括：

-   **API 网关:** 作为所有后端功能的统一入口，为前端提供一个稳定的 API 接口。
-   **请求协调:** 根据请求类型，调用 `simpleOutline` 服务生成大纲，或调用 `slide_agent` 服务生成幻灯片内容。
-   **服务编排:** 编排从文件上传、知识库处理、大纲生成到最终内容生成的完整工作流。
-   **静态资源服务:** 提供对模板图片等静态资源的访问。
-   **代理服务:** 提供一个通用代理端点，用于安全地访问外部资源。

## 3. API 端点分析

以下是 `main.py` 中定义的核心 API 端点：

| 请求方法 | 路径                               | 功能描述                                                                                             | 下游服务/依赖                               |
| :------- | :--------------------------------- | :----------------------------------------------------------------------------------------------------- | :------------------------------------------ |
| `POST`   | `/tools/aippt_outline`             | 接收用户输入的文本主题，流式生成 PPT 大纲。                                                            | `outline_client` -> `simpleOutline` 服务    |
| `POST`   | `/tools/aippt_outline_unified`     | 统一的大纲生成接口：主题必填，可选上传文件；如有文件会先交给 personaldb 解析/向量化，再生成大纲。        | `personaldb` 服务, `outline_client`         |
| `POST`   | `/tools/aippt_outline_from_file`   | 接收用户上传的文件（或 URL），将其发送到知识库进行处理，并基于文件内容流式生成 PPT 大纲。                | `personaldb` 服务, `outline_client`         |
| `POST`   | `/tools/aippt`                     | 接收 Markdown 格式的大纲，流式生成完整的 PPT 幻灯片内容（JSON 格式）。                                 | `content_client` -> `slide_agent` 服务      |
| `POST`   | `/tools/aippt_by_id`               | (已部分实现) 根据知识库中已有的文件 ID 生成 PPT。                                                      | `personaldb` 服务, `content_client`         |
| `GET`    | `/templates`                       | 返回可用的 PPT 模板列表，包含模板名称、ID 和封面图片路径。                                             | 本地静态配置                                |
| `GET`    | `/data/{filename}`                 | 提供对 `template/` 目录下的静态文件（主要是模板封面图）的访问。                                        | 本地文件系统                                |
| `GET`    | `/files/{user_id}`                 | 列出指定用户在 `personaldb` 知识库中存储的所有文件。                                                   | `personaldb` 服务                           |
| `GET`    | `/proxy`                           | 一个通用的 HTTP 代理，用于从前端安全地请求外部 URL 资源（如图片）。                                    | `httpx` 外部请求                          |
| `GET`    | `/healthz`                         | 健康检查端点，用于监控服务是否正常运行。                                                               | -                                           |

## 4. 客户端通信

`main_api` 通过两个专门的客户端模块与下游 Agent 服务进行通信。这种设计将网络通信逻辑与业务逻辑解耦。

### 4.1 `outline_client.py`

-   **作用:** 封装了对 `simpleOutline` 服务（运行在 `10001` 端口）的 A2A (Agent-to-Agent) 调用。
-   **流程:**
    1.  初始化 `A2AOutlineClientWrapper`。
    2.  通过 `generate` 方法将用户问题（文本主题或从文件中提取的内容）和语言偏好发送给 `simpleOutline` 服务。
    3.  以异步生成器的方式，流式接收并返回大纲文本块。

### 4.2 `content_client.py`

-   **作用:** 封装了对 `slide_agent` 服务（运行在 `10011` 端口）的 A2A 调用。
-   **流程:**
    1.  初始化 `A2AContentClientWrapper`。
    2.  通过 `generate` 方法将 Markdown 大纲和元数据（如 `user_id`、搜索选项等）发送给 `slide_agent` 服务。
    3.  流式接收幻灯片内容。
-   **图表与图片处理:**
    `content_client` 包含一个重要的业务逻辑 `process_chart_part_text`。当它从 `slide_agent` 收到一个包含图表（`kind: chart`）或图片（`kind: image`）的幻灯片 JSON 时，它会自动将这张幻灯片拆分为多个独立的 slide 数据流返回。例如，一个包含标题、文本和一张图表的 slide 会被拆分成两条消息：一条包含标题和文本，另一条仅包含标题和图表。这确保了前端可以正确地将每个图表或图片渲染为单独的一页幻灯片。

## 5. 模板处理

-   **模板目录:** `backend/main_api/template/` 目录用于存放模板相关的静态资源。
-   **规则 (参考 `AGENTS.md`):**
    -   模板 JSON 文件（如 `template_1.json`）必须与同名的图片文件（如 `template_1.jpg`）成对存在。
    -   `/templates` 端点返回模板列表，其中 `cover` 字段的路径指向 `/api/data/{filename}`，由 `/data/{filename}` 端点提供实际的图片文件。
    -   这种设计使得模板的增删改变得简单，只需在 `template/` 目录中添加或删除对应的文件，并更新 `/templates` 端点的静态配置即可。
