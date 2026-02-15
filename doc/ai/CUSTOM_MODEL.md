# 如何配置和使用自定义模型（统一 `.env`）

本项目后端通过 **LiteLLM + ADK** 以“协议类型 + base_url”的方式接入多种模型。

强烈建议只维护**项目根目录**的一份 `.env`（从 `env_template.txt` 复制），变量优先级见 `doc/dev/ENV_GUIDE.md`。

---

## 1) 统一配置入口

```bash
cp env_template.txt .env
# 修改 .env：填入你使用的模型与 API Key（不要提交到 git）
```

模型按“用途”拆分为四组：
- 大纲：`OUTLINE_*`
- 内容写作：`PPT_WRITER_*`
- 内容校对：`PPT_CHECKER_*`（当前 Checker 为规则校验，预留字段）
- 向量嵌入：`EMBEDDING_*`

---

## 2) LLM（大纲/写作/校对）支持哪些 `*_TYPE`？

当前代码侧的协议类型主要支持：
- `google`（Gemini 协议）
- `claude`（Anthropic 协议）
- `openai`（OpenAI 兼容协议）

其他厂商/本地部署（如 DeepSeek、DashScope、豆包、SiliconFlow、Ollama、vLLM、Xinference 等）只要提供 **OpenAI 兼容接口**，都推荐用：

- `*_TYPE=openai`
- `*_BASE_URL=你的兼容网关地址`
- `*_API_KEY=对应 Key（本地一般用 EMPTY）`

> 模型名前缀（`openai/`、`anthropic/`）会在 `create_model.py` 中自动补全，通常可以直接写“裸模型名”（如 `gpt-4o`、`claude-3-...`）。

---

## 3) OUTLINE（大纲）配置示例

### 3.1 Google Gemini（`OUTLINE_TYPE=google`）

```env
OUTLINE_TYPE=google
OUTLINE_API_KEY=your_gemini_key
OUTLINE_MODEL=gemini-2.0-flash
```

### 3.2 OpenAI 官方（`OUTLINE_TYPE=openai`，无需 base_url）

```env
OUTLINE_TYPE=openai
OUTLINE_API_KEY=your_openai_key
OUTLINE_MODEL=gpt-4o
# OUTLINE_BASE_URL 留空即可
```

### 3.3 Claude（`OUTLINE_TYPE=claude`）

```env
OUTLINE_TYPE=claude
OUTLINE_API_KEY=your_claude_key
OUTLINE_MODEL=claude-3-sonnet-20240229
```

### 3.4 DeepSeek / DashScope / 豆包等（OpenAI 兼容）

```env
OUTLINE_TYPE=openai
OUTLINE_API_KEY=your_vendor_key
OUTLINE_BASE_URL=https://api.deepseek.com/v1
OUTLINE_MODEL=deepseek-chat
```

---

## 4) PPT_WRITER（内容写作）配置示例

与 OUTLINE 相同思路，改为 `PPT_WRITER_*`：

```env
PPT_WRITER_TYPE=openai
PPT_WRITER_API_KEY=your_vendor_key
PPT_WRITER_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PPT_WRITER_MODEL=qwen-turbo-latest
```

---

## 5) EMBEDDING（向量嵌入）配置示例

`personaldb` 的嵌入模型目前支持：
- `EMBEDDING_TYPE=openai`（OpenAI 兼容 embeddings）
- `EMBEDDING_TYPE=ollama`（Ollama 原生 `/api/embeddings`）

### 5.1 OpenAI 兼容 embeddings

```env
EMBEDDING_TYPE=openai
EMBEDDING_API_KEY=your_embedding_key
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-large
```

### 5.2 Ollama 原生 embeddings

```env
EMBEDDING_TYPE=ollama
EMBEDDING_BASE_URL=http://127.0.0.1:11434
EMBEDDING_MODEL=mxbai-embed-large
```

> 说明：
> - `EMBEDDING_TYPE=ollama` 时，代码会优先读取 `EMBEDDING_BASE_URL`；未设置则回退到 `OLLAMA_BASE_URL`（默认 `http://127.0.0.1:11434`）。
> - `vLLM/Xinference/...` 等如需做 embedding，推荐直接使用 `EMBEDDING_TYPE=openai` + `EMBEDDING_BASE_URL=你的 OpenAI 兼容网关`（无需额外的厂商专用环境变量）。
