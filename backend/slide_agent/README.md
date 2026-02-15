# 🧠 Slide Agent（内容生成服务）

本服务负责将「Markdown 大纲」扩写为逐页的 **Slide Schema(JSON)**，并通过 A2A + ADK 以（可选）SSE 方式流式输出给 `main_api`。

## 🚀 快速开始

1) 在项目根目录配置统一 `.env`（只需一次）：

```bash
cp env_template.txt .env
# 修改 .env，填入你的 API Key
```

2) 启动内容生成服务（默认端口 `10011`）：

```bash
cd backend/slide_agent
python main_api.py
```

3) 本地请求示例（可选）：

```bash
python a2a_client.py
```

## ⚙️ 常用配置

- `CONTENT_STREAMING`：内容服务是否启用 SSE（默认建议 `false`）
- `USE_CHART`：是否启用图表生成（默认 `true`）
- `PEXELS_API_KEY`：Pexels 图片素材 Key（可选）

> 推荐统一在项目根目录 `.env` 配置；如需本机临时覆盖，再复制 `env_template` 为本目录 `.env`。

## 🔍 搜索/工具配置入口

- 工具与搜索引擎实现：`backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py`

## 📁 目录结构（与实际一致）

```text
backend/slide_agent/
├── a2a_client.py
├── adk_agent_executor.py
├── env_template
├── main_api.py
├── requirements.txt
└── slide_agent/
    ├── agent.py
    ├── agent_utils.py
    ├── config.py
    ├── create_model.py
    ├── runtime_paths.py
    └── sub_agents/
        └── ppt_writer/
            ├── agent.py
            ├── cache_utils.py
            ├── prompt.py
            ├── tools.py
            ├── utils.py
            └── weixin_search.py
```

## 📌 部署注意

`main_api.py` 的 `--agent_url` 是 **Agent Card 对外声明的访问地址**，在容器/内外网环境中可能与监听地址不同；部署时请按实际访问路径设置。
