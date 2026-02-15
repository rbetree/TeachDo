# slide_agent 服务文档

## 概述

[`slide_agent`](../../backend/slide_agent/) 是 AI2PPT 项目中负责**幻灯片内容生成**的核心服务。它接收由 [`simpleOutline`](../../backend/simpleOutline/) 生成的 Markdown 大纲，将其解析为结构化的幻灯片数据，并通过多 Agent 协作逐页生成详细的 PPT 内容（包括文本扩写、图片搜索、图表数据等）。

## 角色和职责

### 主要职责

1. **大纲解析**：将 Markdown 格式的 PPT 大纲解析为 JSON 结构化数据
2. **内容生成**：使用大语言模型（LLM）对每一页幻灯片进行内容扩写和丰富
3. **资源检索**：
   - 调用搜索引擎检索相关文档（微信公众号文章）
   - 调用知识库检索用户上传的私有文档
   - 调用图片搜索 API（Pexels）为幻灯片配图
4. **图表生成**：根据检索到的数据生成可视化图表（折线图、柱状图、饼图等）
5. **质量控制**：对生成的内容进行 JSON 格式校验和字段完整性验证
6. **流式输出**：通过 SSE（Server-Sent Events）实时返回生成进度

### 在系统中的位置

```
用户请求 → main_api → simpleOutline (生成大纲)
                    ↓
              slide_agent (生成内容) → 返回给前端
```

## 技术架构

### Agent 框架：Google ADK

[`slide_agent`](../../backend/slide_agent/main_api.py#L44) 基于 **Google ADK（Agent Development Kit）** 框架构建，与 [`simpleOutline`](simpleOutline_service.md) 使用相同的技术栈。

### A2A 通信协议

服务通过 **A2A（Agent-to-Agent）** 协议对外提供服务：
- **端口**：[`10011`](../../backend/slide_agent/main_api.py#L48)
- **协议**：HTTP + SSE 流式传输
- **Agent Card**：通过 `/.well-known/agent.json` 暴露服务元数据
- **调用方**：[`main_api`](../../backend/main_api/main.py) 通过 [`content_client.py`](../../backend/main_api/content_client.py) 封装调用

## 核心流程

### 1. 服务启动流程

入口文件：[`main_api.py`](../../backend/slide_agent/main_api.py)

关键配置：
- 监听地址：`0.0.0.0`（默认）
- 服务端口：`10011`
- 流式输出：默认启用（通过环境变量 `CONTENT_STREAMING` 控制）

启动步骤：
1. 加载环境变量（优先使用项目根目录的 `.env`）
2. 创建 [`ADKAgentExecutor`](../../backend/slide_agent/adk_agent_executor.py#L55) 包装 [`root_agent`](../../backend/slide_agent/slide_agent/agent.py#L80)
3. 初始化 A2A 应用（[`A2AStarletteApplication`](../../backend/slide_agent/main_api.py#L113)）
4. 配置 CORS 中间件，允许跨域访问
5. 启动 Uvicorn 服务器

### 2. 请求处理流程

#### 2.1 请求入口

客户端通过 A2A 协议发送消息，消息结构：

```python
message_data = {
    'message': {
        'role': 'user',
        'parts': [{'kind': 'text', 'text': markdown_outline}],
        'metadata': {
            'search_engine': ['KnowledgeBaseSearch', 'DocumentSearch', 'SearchImage'],
            'user_id': 'user_123',
            'language': 'chinese'
        }
    }
}
```


#### 2.2 Agent 执行链

[`root_agent`](../../backend/slide_agent/slide_agent/agent.py#L80) 是一个 [`SequentialAgent`](../../backend/slide_agent/slide_agent/agent.py#L80)，执行流程如下：

**第一步：大纲解析（before_agent_callback）**

在 [`before_agent_callback`](../../backend/slide_agent/slide_agent/agent.py#L41) 中：
1. 提取用户发送的 Markdown 大纲
2. 校验格式（必须包含 `#` 一级标题、`##` 二级标题或 `###` 三级标题）
3. 调用 [`parse_markdown_to_slides()`](../../backend/slide_agent/slide_agent/utils.py#L10) 解析为 JSON 结构
4. 将解析结果存入 `state['outline_json']`

解析后的 JSON 结构示例：

```json
[
  {"type": "cover", "data": {"title": "主标题", "text": "副标题"}},
  {"type": "contents", "data": {"items": ["章节1", "章节2"]}},
  {"type": "transition", "data": {"title": "章节标题", "text": "过渡语"}},
  {"type": "content", "data": {"title": "内容标题", "items": [
    {"title": "要点1", "text": "详细内容"}
  ]}},
  {"type": "end"}
]
```

**第二步：循环生成内容（ppt_generator_loop_agent）**

[`ppt_generator_loop_agent`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L360) 是一个 [`LoopAgent`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L360)，最多迭代 200 次，包含三个子 Agent：

**1. PPTWriterSubAgent（生成器）**

[`PPTWriterSubAgent`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L73) 负责内容生成：
- 根据 `current_slide_index` 获取对应的 slide schema
- 动态生成 prompt（根据页面类型：cover/contents/transition/content/end）
- 调用大语言模型生成内容
- 可选调用工具：
  - [`DocumentSearch`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py#L159)：搜索微信公众号文章（通过搜狗微信搜索）
  - [`KnowledgeBaseSearch`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py#L199)：搜索用户知识库（调用 personaldb 服务）
  - [`SearchImage`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py#L27)：搜索配图（Pexels API）
- 将生成的原始文本存入 `state['last_written_raw']`

**2. CheckerAgent（校验器）**

[`CheckerAgent`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L165) 负责质量控制：
- 读取 `state['last_written_raw']`
- 尝试解析为 JSON（支持清理 Markdown 代码块围栏）
- 调用 [`validate_slide()`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L215) 验证字段完整性
- 设置校验状态：
  - 成功：`state['is_valid_json'] = True`, `state['last_slide_json'] = data`
  - 失败：`state['is_valid_json'] = False`, 记录错误信息

**3. ControllerAgent（控制器）**

[`ControllerAgent`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L240) 负责流程控制：
- 根据校验结果决策：
  - **校验通过**：将 JSON 加入 `state['generated_slides_content']`，推进 `current_slide_index`，流式输出当前页
  - **校验失败**：重试（最多 3 次），超过阈值则跳过并推进
- 判断是否完成所有页面：
  - 若 `current_slide_index >= slides_plan_num`，触发 `escalate` 终止循环
- 每完成一页即通过 SSE 流式返回给前端

### 3. 数据流转图

```
Markdown 大纲
    ↓ (parse_markdown_to_slides)
JSON 数组 [slide1, slide2, ...]
    ↓ (遍历每个 slide)
当前 slide schema
    ↓ (PPTWriterSubAgent + Prompt)
调用 LLM + Tools
    ↓ (生成内容)
原始文本 (last_written_raw)
    ↓ (CheckerAgent)
JSON 校验 + 字段验证
    ↓ (ControllerAgent)
有效 JSON → 累积到 generated_slides_content
    ↓ (流式输出)
SSE 推送给前端（每页独立推送）
```

## 图表处理逻辑

### 生成端（slide_agent）

在 [`CONTENT_PAGE_PROMPT`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/prompt.py#L78) 中，LLM 被指示：

1. **触发条件**：仅当主题涉及趋势/对比/占比/量化指标，且通过工具检索到可引用数据时
2. **数据要求**：所有数值必须来自工具返回的原文内容，不得编造
3. **类型选择**：
   - 时间趋势 → `line`（折线图）
   - 类目对比 → `bar` 或 `column`（柱状图）
   - 占比 → `pie` 或 `ring`（饼图）
   - 其他支持：`area`（面积图）、`radar`（雷达图）
4. **输出格式**：在 `data.items` 数组末尾新增一个 `kind: "chart"` 的项

JSON 结构示例：

```json
{
  "type": "content",
  "data": {
    "title": "市场趋势分析",
    "items": [
      {
        "title": "文本要点1",
        "text": "详细内容..."
      },
      {
        "kind": "chart",
        "title": "2020-2025年增长趋势",
        "text": "数据来源于XXX报告",
        "chartType": "line",
        "labels": ["2020", "2021", "2022", "2023", "2024", "2025"],
        "series": [
          {
            "name": "市场规模",
            "data": [100, 150, 200, 280, 350, 420]
          }
        ],
        "options": {
          "xAxis": {"name": "年份"},
          "yAxis": {"name": "规模（亿元）"}
        }
      }
    ]
  }
}
```

### 拆分端（content_client）

在 [`main_api`](../../backend/main_api/main.py) 调用 [`slide_agent`](../../backend/slide_agent/) 时，通过 [`content_client.py`](../../backend/main_api/content_client.py) 进行数据处理。

关键方法：[`process_chart_part_text()`](../../backend/main_api/content_client.py#L164)

**拆分规则**：
1. 检测 JSON 中 `type === "content"` 且 `items[].kind === "chart"` 或 `kind === "image"`
2. 将普通文本项、图表项和图片项分离
3. **每个 chart/image 单独作为一条 slide 返回**，确保前端正确渲染

**拆分示例**：

输入（slide_agent 返回）：
```json
{
  "type": "content",
  "data": {
    "title": "技术趋势",
    "items": [
      {"title": "文本1", "text": "内容1"},
      {"kind": "chart", "title": "图表1", ...},
      {"title": "文本2", "text": "内容2"}
    ]
  }
}
```

输出（拆分为 2 条）：
```json
// 第1条：普通文本项
{
  "type": "content",
  "data": {
    "title": "技术趋势",
    "items": [
      {"title": "文本1", "text": "内容1"},
      {"title": "文本2", "text": "内容2"}
    ]
  }
}

// 第2条：图表单独一页
{
  "type": "content",
  "data": {
    "title": "技术趋势",
    "items": [
      {"kind": "chart", "title": "图表1", ...}
    ]
  }
}
```

**重要性**：此拆分逻辑确保图表在前端能够独立渲染，不会与文本内容混淆或被覆盖。

## 工具系统

### 1. DocumentSearch（文档搜索）

实现：[`tools.py:159`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py#L159)

功能：通过搜狗微信搜索 API 检索公众号文章

**调用链**：
1. [`sogou_weixin_search(keyword)`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/weixin_search.py)：搜索关键词，返回文章列表
2. [`get_real_url(sogou_link)`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/weixin_search.py)：解析搜狗链接，获取真实 URL
3. [`get_article_content(real_url, referer)`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/weixin_search.py)：提取文章正文

**注意事项**：
- 必须传入 `referer`（搜狗链接），否则请求会失败（根据 `AGENTS.md` 规则）
- 返回结果包含：标题、发布时间、真实 URL、正文内容

### 2. KnowledgeBaseSearch（知识库搜索）

实现：[`tools.py:199`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py#L199)

功能：调用 [`personaldb`](../../backend/personaldb/) 服务检索用户上传的文档

**请求参数**：
```python
{
    "userId": user_id,      # 从 metadata 中获取
    "query": keyword,       # 搜索关键词
    "keyword": "",          # 强制包含的关键词（可选）
    "topk": 5               # 返回前 N 条结果
}
```

**环境变量依赖**：`PERSONAL_DB`（personaldb 服务地址，默认端口 9100）

### 3. SearchImage（图片搜索）

实现：[`tools.py:27`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py#L27)

功能：通过 Pexels API 搜索高质量图片

**API 配置**：
- 环境变量：`PEXELS_API_KEY`
- 未配置时回退到模拟数据（从预设图片池随机选择）

**返回格式**：
```python
[
  {
    "id": 123456,
    "src": "https://images.pexels.com/...",
    "width": 1920,
    "height": 1080,
    "alt": "图片描述",
    "photographer": "摄影师名称",
    "url": "原始页面链接"
  }
]
```

## 模型配置

配置文件：[`config.py`](../../backend/slide_agent/slide_agent/config.py)

### PPT_WRITER_AGENT_CONFIG

用于内容生成的主模型，支持从环境变量读取配置：

```python
{
    "provider": os.getenv("PPT_WRITER_TYPE", "ali"),
    "model": os.getenv("PPT_WRITER_MODEL", "qwen-turbo-latest"),
    "api_key": os.getenv("PPT_WRITER_API_KEY"),
    "base_url": os.getenv("PPT_WRITER_BASE_URL"),
}
```

支持的 `PPT_WRITER_TYPE`（协议类型）：
- `google`：Gemini 系列
- `openai`：所有 OpenAI 兼容模型（OpenAI / DeepSeek / 阿里 DashScope / 豆包 / SiliconFlow / vLLM / Xinference 等）
- `claude`：Anthropic Claude 系列

### PPT_CHECKER_AGENT_CONFIG

用于内容校验的模型（目前未使用，校验改为规则校验），同样支持环境变量：

```python
{
    "provider": os.getenv("PPT_CHECKER_TYPE", "ali"),
    "model": os.getenv("PPT_CHECKER_MODEL", "qwen-turbo-latest"),
    "api_key": os.getenv("PPT_CHECKER_API_KEY"),
    "base_url": os.getenv("PPT_CHECKER_BASE_URL"),
}
```

### 模型创建

通过 [`create_model()`](../../backend/slide_agent/slide_agent/create_model.py) 统一创建，支持多 provider，非 Google 模型需加前缀（如 `openai/gpt-4`）。

## Prompt 系统

Prompt 文件：[`prompt.py`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/prompt.py)

### Prompt 结构

每个页面类型对应一个 prompt 模板：

```python
prompt_mapper = {
    "cover": COVER_PAGE_PROMPT,
    "contents": CONTENTS_PAGE_PROMPT,
    "transition": TRANSITION_PAGE_PROMPT,
    "content": CONTENT_PAGE_PROMPT,
    "end": END_PAGE_PROMPT
}
```

### 动态 Prefix

根据工具配置动态选择前缀：

1. **无工具**：[`PREFIX_PAGE_PROMPT`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/prompt.py#L4) - 基础约束
2. **仅图片搜索**：[`PREFIX_PAGE_PROMPT_WITH_IMAGE`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/prompt.py#L14) - 增加图片搜索指令
3. **含搜索工具**：[`PREFIX_PAGE_PROMPT_WITH_SEARCH`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/prompt.py#L46) - 强制使用搜索工具

### Prompt 设计原则

1. **结构保持**：不得修改已有字段名称，不得删除字段
2. **语言统一**：通过 `{language}` 参数控制输出语言
3. **防止编造**：明确要求数据来源，避免精确数值
4. **纯 JSON 输出**：严禁输出 Markdown、代码块围栏等额外内容

## 重试与容错机制

### 重试策略

在 


[`ControllerAgent`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L240) 中实现：

**重试计数**：
- 通过 `state['retry_count_map']` 记录每页的重试次数
- 最大重试次数：3 次（硬编码）

**重试逻辑**：
```python
if current_retries <= max_retries:
    # 不推进页码，触发下一轮 Writer
    return
else:
    # 超过阈值，跳过此页并推进
    current_slide_index += 1
```

### 容错处理

1. **JSON 解析失败**：
   - 自动清理 Markdown 代码块围栏（`\`\`\`json` 和 `\`\`\``）
   - 提取首个 `{` 到最后一个 `}` 的子串
   - 仍失败则标记为 `is_valid_json = False`

2. **字段缺失**：
   - 通过 [`validate_slide()`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/utils.py) 检查必需字段
   - 记录缺失字段列表，提供给 LLM 作为反馈

3. **工具调用失败**：
   - 捕获异常但不中断流程
   - 返回错误信息给 LLM，由 LLM 决定如何处理

4. **超时保护**：
   - HTTP 客户端超时：60 秒（setup）/ 360 秒（generate）
   - 无限重试保护：最大迭代次数 200 次

## 环境变量配置

建议统一在项目根目录 `.env` 配置（变量清单见 `../dev/ENV_GUIDE.md`）。

- 服务端口与流式：
  - `CONTENT_API_PORT`：默认 `10011`
  - `CONTENT_STREAMING`：默认 `false`
- 内容生成模型（Writer）：
  - `PPT_WRITER_TYPE`：`google` / `openai` / `claude`（其他厂商通过 `openai + PPT_WRITER_BASE_URL` 接入）
  - `PPT_WRITER_MODEL`
  - `PPT_WRITER_API_KEY`
  - `PPT_WRITER_BASE_URL`（可选，OpenAI 兼容网关/自托管时）
- 校对模型（预留）：
  - 当前 `CheckerAgent` 为规则校验，不调用大模型；下面变量仅用于未来切换为 LLM 校对：
  - `PPT_CHECKER_TYPE` / `PPT_CHECKER_MODEL` / `PPT_CHECKER_API_KEY` / `PPT_CHECKER_BASE_URL`
- 图片与知识库：
  - `PEXELS_API_KEY`：可选；未配置时图片搜索会走模拟/跳过逻辑
  - `PERSONAL_DB`：personaldb 服务地址（用于 `KnowledgeBaseSearch`）
- 图表开关：
  - `USE_CHART`：建议显式设置为 `true/false`；当前实现为“变量存在即启用”

## 服务依赖

### 上游服务

- **[`main_api`](../../backend/main_api/main.py)**：调用 `slide_agent` 生成内容
  - 通过 [`content_client.py`](../../backend/main_api/content_client.py) 封装
  - 端口：6800

### 下游服务

- **[`personaldb`](../../backend/personaldb/main.py)**：知识库检索
  - 端口：9100
  - 工具：[`KnowledgeBaseSearch`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py#L199)

### 外部 API

- **Pexels API**：图片搜索
  - 需要 API Key
  - 工具：[`SearchImage`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py#L27)

- **搜狗微信搜索**：文档检索
  - 无需 API Key
  - 工具：[`DocumentSearch`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py#L159)

## 文件结构

```
backend/slide_agent/
├── main_api.py                    # 服务入口，A2A 应用启动
├── adk_agent_executor.py          # ADK Agent 执行器实现
├── a2a_client.py                  # A2A 客户端测试示例
├── slide_agent/
│   ├── agent.py                   # root_agent 定义
│   ├── config.py                  # 模型配置
│   ├── create_model.py            # 模型创建工具
│   ├── utils.py                   # Markdown 解析工具
│   └── sub_agents/
│       └── ppt_writer/
│           ├── agent.py           # Writer/Checker/Controller Agent
│           ├── prompt.py          # Prompt 模板
│           ├── tools.py           # 搜索工具实现
│           ├── utils.py           # 校验工具
│           ├── weixin_search.py   # 微信搜索实现
│           └── cache_utils.py     # 缓存工具
├── Dockerfile                     # Docker 镜像构建
├── requirements.txt               # Python 依赖
└── README.md                      # 服务说明
```

## 关键特性

### 1. 流式输出

通过 SSE（Server-Sent Events）实时推送生成进度：

```python
# ADKAgentExecutor 中的处理
if agent_author in self.show_agent:  # ControllerAgent
    await task_updater.update_status(
        TaskState.working,
        message=task_updater.new_agent_message(parts, metadata={"author": agent_author})
    )
```

前端可实时接收每页生成的内容，无需等待全部完成。

### 2. 元数据传递

通过 `state['metadata']` 在工具间传递上下文：

```python
# 工具调用时获取元数据
metadata = tool_context.state.get("metadata", {})
user_id = metadata.get("user_id")
language = metadata.get("language")
```

元数据字段：
- `search_engine`：启用的搜索工具列表
- `user_id`：用户 ID（用于知识库检索）
- `language`：输出语言（中文/英文）
- `tool_document_ids`：工具返回的文档 ID（用于引用）
- `references`：引用来源列表

### 3. 动态 Prompt

根据页面类型和工具配置动态生成 prompt：

```python
def _get_dynamic_instruction(self, ctx: InvocationContext) -> str:
    current_slide_index = ctx.state.get("current_slide_index", 0)
    outline_json = ctx.state.get("outline_json")
    current_slide_schema = outline_json[current_slide_index]
    
    # 根据类型选择 prompt
    slide_prompt = prompt_mapper[current_slide_schema["type"]]
    
    # 根据工具配置选择前缀
    if not search_engine:
        prefix = PREFIX_PAGE_PROMPT
    elif search_engine == ["SearchImage"]:
        prefix = PREFIX_PAGE_PROMPT_WITH_IMAGE
    else:
        prefix = PREFIX_PAGE_PROMPT_WITH_SEARCH
    
    return prefix + slide_prompt.format(input_slide_data=json.dumps(current_slide_schema))
```

### 4. 状态管理

通过 `session.state` 管理生成过程中的状态：

| 状态字段 | 类型 | 说明 |
|---------|------|------|
| `outline_json` | list | 解析后的幻灯片数组 |
| `slides_plan_num` | int | 总页数 |
| `current_slide_index` | int | 当前正在生成的页索引 |
| `last_written_raw` | str | Writer 生成的原始文本 |
| `last_slide_json` | dict | Checker 解析后的 JSON |
| `is_valid_json` | bool | 是否通过校验 |
| `retry_count_map` | dict | 每页的重试次数 |
| `generated_slides_content` | list | 已生成的有效内容累积 |
| `last_validation_passed` | bool | 上次校验是否通过 |
| `last_validation_feedback` | str | 校验失败的错误信息 |

## 性能优化

### 1. 心跳保持

在 [`content_client.py:193`](../../backend/main_api/content_client.py) 中，SSE 连接每 10 秒发送心跳防止断连（虽然代码中未显式实现，但这是 A2A 协议的标准行为）。

### 2. 并发控制

每次只生成一页内容，避免并发调用 LLM 导致的资源竞争和成本激增。

### 3. 缓存机制

[`cache_utils.py`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/cache_utils.py) 提供缓存支持，可缓存搜索结果和生成内容（需根据具体实现启用）。

## 调试与日志

### 日志配置

日志文件：`api.log`（服务目录下）

日志级别：`INFO`

关键日志点：
1. 模型调用前后（[`my_before_model_callback`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L20), [`my_after_model_callback`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L31)）
2. 工具调用（每个工具的 `print` 和 `logger.info`）
3. 校验结果（[`CheckerAgent`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L165)）
4. 页面推进（[`ControllerAgent`](../../backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py#L240)）

### 测试客户端

使用 [`a2a_client.py`](../../backend/slide_agent/a2a_client.py) 进行本地测试：

```bash
python backend/slide_agent/a2a_client.py
```

## 常见问题

### 1. 图表未生成

**原因**：
- 环境变量 `USE_CHART` 未设置为 `true`
- LLM 未找到可引用的数据源
- 搜索工具未启用

**解决**：
- 设置 `USE_CHART=true`
- 确保 `metadata.search_engine` 包含搜索工具
- 检查工具返回的数据是否包含可用数值

### 2. 知识库搜索失败

**原因**：
- `PERSONAL_DB` 环境变量未配置
- `user_id` 未传入
- personaldb 服务未启动

**解决**：
- 设置 `PERSONAL_DB=http://localhost:9100`
- 确保 `metadata.user_id` 有效
- 检查 personaldb 服务状态

### 3. 流式输出中断

**原因**：
- 网络超时
- LLM 调用失败
- JSON 解析连续失败超过重试次数

**解决**：
- 增加 HTTP 客户端超时时间
- 检查模型配置和 API Key
- 查看日志中的错误信息

## 总结

[`slide_agent`](../../backend/slide_agent/) 是 AI2PPT 项目中最复杂的服务之一，通过多 Agent 协作实现了：

1. **大纲解析**：Markdown → JSON 结构化数据
2. **内容生成**：逐页扩写，支持文本、图片、图表
3. **质量控制**：JSON 校验 + 重试机制
4. **流式输出**：实时推送生成进度
5. **工具集成**：文档搜索、知识库检索、图片搜索

核心设计理念：
- **渐进式生成**：每页独立生成和校验
- **容错优先**：校验失败自动重试，超限则跳过
- **数据驱动**：Prompt 和工具配置完全由元数据控制
- **可观测性**：详细的日志和状态管理
