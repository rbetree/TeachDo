# simpleOutline 服务文档

## 概述

`simpleOutline` 是 TeachDo 后端中负责生成演示文稿大纲的核心服务（沿革与历史命名见 `doc/architecture/PROJECT_HISTORY.md`）。它基于 **Google ADK (Agent Development Kit)** 框架和 **A2A (Agent-to-Agent)** 协议构建，接收用户提供的主题或参考内容，通过智能分析和可选的网络搜索，生成结构化的 Markdown 大纲。

## 服务定位

- **角色**: 大纲生成 Agent
- **上游服务**: 被 [`main_api`](main_api_service.md) 通过 [`outline_client.py`](../../backend/main_api/outline_client.py) 调用
- **下游依赖**: 无（可选调用微信搜索工具）
- **端口**: 10001 (默认)
- **协议**: A2A (Agent-to-Agent Communication)

## 架构特点

### 基于 Google ADK 框架

与 LangChain 不同，`simpleOutline` 使用 **Google ADK** 框架构建：

- **Agent 定义**: 通过 [`OutlineAgent`](../../backend/simpleOutline/agent.py#L54) 类继承 `LlmAgent`
- **工具集成**: 使用 ADK 的工具系统 ([`BaseTool`](../../backend/simpleOutline/agent.py#L10))
- **回调机制**: 支持模型调用前后的回调 ([`before_model_callback`](../../backend/simpleOutline/agent.py#L18), [`after_model_callback`](../../backend/simpleOutline/agent.py#L28))
- **状态管理**: 通过 [`InMemorySessionService`](../../backend/simpleOutline/main_api.py#L96) 管理会话状态

### A2A 协议支持

服务通过 A2A 协议暴露能力：

- **Agent Card**: 通过 `/.well-known/agent.json` 暴露元数据
- **技能描述**: 定义为 "Generate an outline based on the user's requirements"
- **流式响应**: 支持 SSE (Server-Sent Events) 实时推送生成进度
- **Metadata 传递**: 支持在工具调用链中传递上下文信息

## 核心功能

### 1. 智能大纲生成

服务根据用户输入的长度，动态选择生成策略：

```python
# 来自 agent.py:89-93
if len(user_input) > prompt.USER_INPUT_NUMBER:  # 默认 1000 字符
    prompt_instruction = prompt.OUTLINE_INSTRUCTION_NO_SEARCH.format(language=language)
else:
    prompt_instruction = prompt.OUTLINE_INSTRUCTION_WITH_SEARCH.format(language=language)
```

#### 策略 A: 基于用户内容生成 (输入 > 1000 字符)

当用户上传 PDF 或提供长文本时：
- **不使用网络搜索**
- 仅基于用户提供的内容生成大纲
- 适用场景：用户已有完整的参考资料

#### 策略 B: 搜索增强生成 (输入 ≤ 1000 字符)

当用户仅提供简短主题时：
- **自动调用 DocumentSearch 工具**
- 通过微信搜索获取相关文章
- 结合搜索结果丰富大纲内容

### 2. 大纲格式规范

所有生成的大纲遵循统一的 Markdown 结构：

```markdown
# 标题

## 一级部分 (共5个)
### 二级小节 (每个一级部分 3-4 个)
- 要点1 (每个二级小节 3-5 个要点)
- 要点2 (短句，动词开头，不超过18字)
- 要点3
```

**格式要求** (定义在 [`prompt.py`](../../backend/simpleOutline/prompt.py)):
- 使用 Markdown 标题层级
- 一级部分固定 5 个
- 每个一级部分包含 3-4 个二级小节
- 每个二级小节列出 3-5 个要点
- 要点使用短句，动词开头，不超过 18 字
- 不包含引言、结语或目录

## 微信搜索工具链

这是 `simpleOutline` 的一个特色功能，实现了通过搜狗搜索微信公众号文章的完整链条。

### 工具调用流程

```
DocumentSearch (tools.py)
    ↓
sogou_weixin_search (weixin_search.py:18)  # 搜索关键词
    ↓
get_real_url (weixin_search.py:68)         # 获取真实微信链接
    ↓
get_article_content (weixin_search.py:101) # 提取文章内容
```

### 详细实现

#### 1. DocumentSearch 工具

定义在 [`tools.py:19`](../../backend/simpleOutline/tools.py#L19)，这是 ADK Agent 可用的工具：

```python
async def DocumentSearch(
    keyword: str,
    tool_context: ToolContext,
):
    """
    根据关键词搜索文档
    :param keyword: str, 搜索的相关文档的关键词
    :return: 返回每篇文档数据
    """
```

**关键点**:
- 默认搜索 **3 篇**文章（[`tools.py:28`](../../backend/simpleOutline/tools.py#L28)）
- 结果存储在 `metadata["tool_document_ids"]` 中
- 通过 `tool_context.state` 在工具间传递上下文

#### 2. sogou_weixin_search - 搜狗搜索

定义在 [`weixin_search.py:18`](../../backend/simpleOutline/weixin_search.py#L18)：

```python
@cache_decorator
def sogou_weixin_search(query: str) -> List[Dict[str, str]]:
    """在搜狗微信搜索中搜索指定关键词并返回结果列表"""
```

**实现细节**:
- 使用 `requests` 库发起 HTTP 请求到 `https://weixin.sogou.com/weixin`
- 使用 `lxml` 解析 HTML 响应
- 提取文章标题、搜狗链接、发布时间
- **使用缓存装饰器** (`@cache_decorator`) 避免重复搜索

#### 3. get_real_url - 获取真实链接

定义在 [`weixin_search.py:68`](../../backend/simpleOutline/weixin_search.py#L68)：

```python
@cache_decorator
def get_real_url(sogou_url: str) -> str:
    """从搜狗微信链接获取真实的微信公众号文章链接"""
```

**工作原理**:
- 搜狗返回的是跳转链接，需要解析出真实的微信链接
- 从响应的 JavaScript 代码中提取 URL 片段
- 拼接成完整的 `https://mp.weixin.qq.com/...` 链接

#### 4. get_article_content - 提取文章内容

定义在 [`weixin_search.py:101`](../../backend/simpleOutline/weixin_search.py#L101)：

```python
@cache_decorator
def get_article_content(real_url: str, referer: str) -> str:
    """获取微信公众号文章的正文内容"""
```

**⚠️ 关键要点** (来自 `AGENTS.md`):

> **referer必传**: 调用 `get_article_content()` 时必须传入搜狗链接作为 referer，否则失败

实现中的体现 ([`tools.py:46`](../../backend/simpleOutline/tools.py#L46)):

```python
sougou_link = every_result["link"]
real_url = get_real_url(sougou_link)
# referer：请求来源
content = get_article_content(real_url, referer=sougou_link)  # 必须传入 referer
```

**为什么需要 referer**:
- 微信公众号文章有防盗链机制
- 必须证明请求来自搜狗搜索结果页
- 否则会被微信服务器拒绝访问

**内容提取**:
- 使用 XPath 定位文章内容区域: `//div[@id='js_content']//text()`
- 清理空白字符并拼接为完整文本
- 返回纯文本内容供 LLM 分析


### 搜索结果处理

完整的搜索流程 ([`tools.py:36-58`](../../backend/simpleOutline/tools.py#L36-L58)):

```python
results = sogou_weixin_search(keyword)
if not results:
    return f"没有搜索到{keyword}相关的文章"

articles = []
results = results[:number]  # 默认取前3篇
for every_result in results:
    sougou_link = every_result["link"]
    real_url = get_real_url(sougou_link)
    content = get_article_content(real_url, referer=sougou_link)
    article = {
        "title": every_result["title"],
        "publish_time": every_result["publish_time"],
        "real_url": real_url,
        "content": content
    }
    articles.append(article)
```

返回的 `articles` 包含：
- `title`: 文章标题
- `publish_time`: 发布时间
- `real_url`: 真实的微信文章链接
- `content`: 文章正文内容

## 服务启动

### 入口文件

[`main_api.py`](../../backend/simpleOutline/main_api.py#L138) 提供服务启动入口：

```bash
python main_api.py --host 0.0.0.0 --port 10001
```

### 启动参数

- `--host`: 服务器绑定的主机名 (默认: localhost)
- `--port`: 服务器监听的端口 (默认: 10001)
- `--agent_url`: Agent Card 中对外展示和访问的地址

### 环境变量配置

服务使用统一的根目录 `.env`（推荐）与服务目录 `.env`（可选覆盖）。`env_template` 仅用于首次复制生成 `.env`。

```bash
# 模型配置（必需）
OUTLINE_MODEL=gemini-2.0-flash-exp          # 使用的 LLM 模型
OUTLINE_TYPE=google                         # 协议类型: google | openai | claude（其他厂商走 openai + OUTLINE_BASE_URL）
OUTLINE_API_KEY=your_outline_api_key        # 对应提供商的 API Key
# 可选：自托管或代理网关
# OUTLINE_BASE_URL=https://your-openai-compatible-endpoint/v1

# 服务配置
OUTLINE_API_PORT=10001                      # 服务端口
OUTLINE_STREAMING=true                      # 是否启用流式输出
HOST=0.0.0.0                                # 监听地址
```

### 环境变量加载优先级

以代码行为为准（`_load_env_files()`）：**不覆盖系统环境变量**，并按以下顺序合并：

1. 系统环境变量
2. 服务目录 `.env`（可选覆盖）
3. 项目根目录 `.env`

更完整的变量说明见：`../dev/ENV_GUIDE.md`。

## 模型配置

### 模型创建

通过 [`create_model.py`](../../backend/simpleOutline/create_model.py) 统一创建模型实例：

```python
# 在 agent.py 中使用
model = create_model(
    model=os.environ["OUTLINE_MODEL"],
    provider=os.environ["OUTLINE_TYPE"],
    api_key=os.environ.get("OUTLINE_API_KEY"),
    base_url=os.environ.get("OUTLINE_BASE_URL"),
)
```

**支持的模型提供商（协议类型，`OUTLINE_TYPE`）**:
- `google`: Google Gemini 系列
- `openai`: 所有 OpenAI 兼容模型（OpenAI / DeepSeek / 阿里 DashScope / 豆包 / SiliconFlow / vLLM / Xinference 等）
- `claude`: Anthropic Claude 系列

**模型名称前缀**：
`create_model.py` 会自动补全常见前缀（如 `openai/`、`anthropic/`），因此通常可以直接写 `gpt-4o` / `claude-...` 这类“裸模型名”。

## Metadata 传递机制

`simpleOutline` 支持在整个调用链中传递 metadata，这是 A2A 架构的重要特性。

### Metadata 流动路径

根据 [`README.md:74-91`](../../backend/simpleOutline/README.md#L74-L91)，metadata 的流动路径为：

```
1. A2A Client (a2a_client.py)
   └─ payload 中携带 metadata
       ↓
2. ADK Agent Executor (adk_agent_executor.py)
   └─ execute() 从 context.message.metadata 获取
   └─ _upsert_session() 存入 state={"metadata": metadata}
       ↓
3. Agent Callbacks (agent.py)
   └─ before_model_callback: callback_context.state.get("metadata")
   └─ after_model_callback: callback_context.state.get("metadata")
       ↓
4. Tool Execution (tools.py)
   └─ tool_context.state.get("metadata") 获取
   └─ tool_context.state["metadata"] = metadata 更新
       ↓
5. Final Response (adk_agent_executor.py)
   └─ final_session.state.get("metadata") 返回给客户端
```

### 使用示例

在 [`tools.py:31-57`](../../backend/simpleOutline/tools.py#L31-L57) 中：

```python
# 获取 metadata
metadata = tool_context.state.get("metadata", {})
if metadata is None:
    metadata = {}

# 工具处理后更新 metadata
metadata["tool_document_ids"] = articles
tool_context.state["metadata"] = metadata
```

这样，调用方可以在最终响应中获取到工具调用的详细信息（如搜索到的文档列表）。

## 回调机制

### 模型调用前回调

[`before_model_callback`](../../backend/simpleOutline/agent.py#L18) 在每次调用 LLM 前触发：

```python
def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    agent_name = callback_context.agent_name
    history_length = len(llm_request.contents)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    return None  # 返回 None，继续调用 LLM
```

**用途**:
- 检查和修改请求参数
- 记录调用日志
- 访问 metadata 信息

### 模型调用后回调

[`after_model_callback`](../../backend/simpleOutline/agent.py#L28) 在 LLM 响应后触发：

```python
def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    # 提取响应文本
    response_parts = llm_response.content.parts
    part_texts = [p.text for p in response_parts if p.text is not None]
    part_text_content = "\n".join(part_texts)
    
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型后的callback, 回复内容是: {part_text_content}")
    return None
```

**注意**: 在流式模式下，每个 token 都会触发此回调。

### 工具调用后回调

[`after_tool_callback`](../../backend/simpleOutline/agent.py#L45) 在工具执行后触发：

```python
def after_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    tool_name = tool.name
    print(f"调用了{tool_name}工具后的callback, tool_response数据为：{tool_response}")
    return None
```

## 流式响应

### SSE (Server-Sent Events)

服务支持通过 SSE 实时推送生成进度：

```python
# 在 main_api.py:100-110 配置
if streaming:
    logger.info("使用 SSE 流式输出模式")
    run_config = RunConfig(
        streaming_mode=StreamingMode.SSE,
        max_llm_calls=500
    )
```

### 响应事件类型

根据 [`README.md:47-69`](../../backend/simpleOutline/README.md#L47-L69)，客户端会收到以下事件：

1. **submitted**: 任务已提交
2. **working**: 正在处理
3. **status-update with message**: 流式输出的文本片段
4. **artifact-update**: 最终完整结果
5. **completed**: 任务完成

示例响应：

```json
{
  "id": "...",
  "jsonrpc": "2.0",
  "result": {
    "contextId": "...",
    "taskId": "...",
    "final": false,
    "kind": "status-update",
    "status": {
      "state": "working",
      "message": {
        "kind": "message",
        "parts": [{"kind": "text", "text": "# 电动汽车市场概况\n..."}],
        "role": "agent"
      }
    }
  }
}
```

## 与 main_api 的集成

`main_api` 通过 [`outline_client.py`](../../backend/main_api/outline_client.py) 调用此服务：

```python
# 示例调用
async for event in outline_client.send_message(
    agent_url="http://localhost:10001",
    message=topic,
    metadata={"language": "chinese"}
):
    # 处理流式事件
    if event["type"] == "final":
        outline = event["text"]
```

**关键点**:
- 使用 A2A 协议通信
- 支持 metadata 传递（如语言设置）
- 接收流式响应并聚合最终结果

## 项目结构

```
backend/simpleOutline/
├── __init__.py
├── agent.py                 # OutlineAgent 定义
├── tools.py                 # DocumentSearch 工具
├── weixin_search.py         # 微信搜索工具链
├── prompt.py                # Prompt 模板
├── main_api.py              # 服务入口
├── adk_agent_executor.py    # ADK 与 A2A 集成
├── a2a_client.py            # A2A 客户端
├── create_model.py          # 模型创建工具
├── cache_utils.py           # 缓存装饰器
├── .env                     # 环境配置
├── env_template             # 环境变量模板
├── requirements.txt         # 依赖列表
└── README.md                # 服务说明
```

## 依赖服务

- **无强依赖**: `simpleOutline` 是独立服务
- **可选外部调用**: 搜狗微信搜索（公网 API）
- **被调用方**: `main_api` 服务

## 性能优化

1. **缓存机制**: 所有搜索函数使用 `@cache_decorator`
   - 避免重复搜索相同关键词
   - 减少网络请求延迟

2. **搜索数量限制**: 默认只搜索 3 篇文章
   - 平衡内容质量和响应速度
   - 防止本地模型上下文过长

3. **流式响应**: 使用 SSE 实时推送
   - 改善用户体验
   - 及时反馈生成进度

## 常见问题

### Q: 为什么微信搜索失败？

**A**: 检查以下几点：
1. 确保调用 `get_article_content()` 时传入了 `referer` 参数
2. 检查网络连接是否正常
3. 搜狗可能有反爬虫限制，尝试更换 Cookie

### Q: 如何切换模型？

**A**: 修改 `.env` 文件中的 OUTLINE_* 变量：

```bash
OUTLINE_MODEL=gemini-2.0-flash-exp   # 或其他支持的模型
OUTLINE_TYPE=google                  # 对应的提供商
OUTLINE_API_KEY=your_outline_api_key
```

非 Google 模型在内部会自动添加 `openai/` 或 `anthropic/` 前缀，无需手动处理。

### Q: 如何禁用流式输出？

**A**: 设置环境变量：

```bash
OUTLINE_STREAMING=false
```

### Q: 大纲格式不符合要求怎么办？

**A**: 检查 [`prompt.py`](../../backend/simpleOutline/prompt.py) 中的提示词，确保格式规则清晰。如果模型持续不遵守，可能需要：
1. 更换更强大的模型
2. 在提示词中增加示例
3. 使用后处理脚本规范化输出

## 相关文档

- [main_api 服务文档](main_api_service.md)
- [后端架构总览](backend_architecture.md)
- [AGENTS.md 规则文档](../../.kilocode/rules/AGENTS.md)

## 总结

`simpleOutline` 服务是 TeachDo 的核心组件之一（沿革与历史命名见 `doc/architecture/PROJECT_HISTORY.md`），负责将用户的简短主题或长文档转换为结构化的演示文稿大纲。其主要特点包括：

1. **基于 Google ADK**: 使用现代化的 Agent 框架，而非传统的 LangChain
2. **智能策略选择**: 根据输入长度自动决定是否使用网络搜索
3. **微信搜索集成**: 独特的搜狗微信搜索工具链，能获取高质量中文内容
4. **A2A 协议**: 标准化的 Agent 通信协议，易于集成和扩展
5. **流式响应**: 通过 SSE 实时推送生成进度，提升用户体验
6. **Metadata 传递**: 完整的上下文传递机制，支持复杂的多步骤流程

作为演示文稿生成流程的第一步，`simpleOutline` 为后续的内容生成（[`slide_agent`](../../backend/slide_agent)）提供了结构化的框架，确保最终生成的 PPT 具有清晰的逻辑和完整的内容覆盖。
