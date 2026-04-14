# 环境变量与配置指南（统一 `.env`）

本项目推荐只维护**项目根目录**的一份 `.env`（从 `env_template.txt` 复制），各后端服务默认都会读取它；如需本机临时覆盖，再在对应服务目录创建 `.env`。

## 1) 统一配置（推荐）

```bash
cp env_template.txt .env
# 修改 .env，填入你的 API Key（不要提交到 git）
```

## 2) 读取优先级（约定）

优先级从高到低：

1. 系统环境变量（shell / Docker env）
2. 服务目录 `.env`（可选，用于本机临时覆盖）
3. 项目根目录 `.env`（统一配置）

## 3) 常用配置项

### 3.1 模型配置（按“用途”拆分）

- 大纲模型：`OUTLINE_TYPE` / `OUTLINE_BASE_URL` / `OUTLINE_API_KEY` / `OUTLINE_MODEL`
- 内容撰写模型：`PPT_WRITER_TYPE` / `PPT_WRITER_BASE_URL` / `PPT_WRITER_API_KEY` / `PPT_WRITER_MODEL`
- 内容校对模型：`PPT_CHECKER_TYPE` / `PPT_CHECKER_BASE_URL` / `PPT_CHECKER_API_KEY` / `PPT_CHECKER_MODEL`
- 向量嵌入模型：`EMBEDDING_TYPE` / `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY` / `EMBEDDING_MODEL`

> `*_TYPE` 表示协议类型：
> - LLM（大纲/写作/校对）：目前主要支持 `openai` / `google` / `claude`。  
>   其他厂商/自托管服务（如 DeepSeek、DashScope、Ollama、vLLM、Xinference 等）一般通过 **`openai + *_BASE_URL`** 的 OpenAI 兼容方式接入。
> - Embedding（向量嵌入）：`EMBEDDING_TYPE` 目前支持 `openai` / `ollama`；其他提供方如有 OpenAI 兼容 embeddings 接口，也推荐使用 `openai + EMBEDDING_BASE_URL`。

### 3.2 服务地址

- `OUTLINE_API`：大纲服务地址（默认 `http://127.0.0.1:10001`）
- `CONTENT_API`：内容服务地址（默认 `http://127.0.0.1:10011`）
- `PERSONAL_DB`：知识库服务地址（默认 `http://127.0.0.1:9100`）

### 3.3 运行期目录（建议保持默认）

- `TEACHDO_CACHE_DIR`：缓存目录（默认 `var/cache`，会按服务名分目录）
- `TEACHDO_TMP_DIR`：临时目录（默认 `var/tmp`，会按服务名分目录）
- `TEACHDO_LOG_DIR`：日志目录（默认 `logs`）

### 3.4 功能开关

- `OUTLINE_STREAMING`：大纲服务是否启用 SSE（默认 `true`）
- `CONTENT_STREAMING`：内容服务是否启用 SSE（默认 `false`，避免严格 JSON 解析受影响）
- `USE_CHART`：是否启用图表（默认 `true`）
- `USE_MINERU`：PersonalDB 是否启用 MinerU 解析 PDF（默认 `false`）

### 3.5 可选：图片素材

- `PEXELS_API_KEY`：Pexels 图片搜索 Key（可选）

### 3.6 安全与资源限制（推荐生产环境启用）

- `/proxy` 资源代理：
  - `TEACHDO_PROXY_ALLOWED_HOSTS`：允许代理的域名白名单（逗号分隔，支持子域）。留空表示不启用白名单（兼容现有行为）。
  - `TEACHDO_PROXY_MAX_BYTES`：上游响应体大小上限（字节），默认 `26214400`（25MB）。
- PersonalDB 上传/URL 下载：
  - `TEACHDO_UPLOAD_MAX_BYTES`：上传文件体与 URL 下载累计写入的大小上限（字节），默认 `31457280`（30MB）。
