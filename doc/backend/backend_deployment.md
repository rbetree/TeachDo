# 后端环境配置与部署指南（以当前代码为准）

本文档聚焦 **后端服务栈**（`main_api` / `simpleOutline` / `slide_agent` / `personaldb`）的运行方式与部署入口。

如果你是「整栈一键启动 / Docker 部署」，建议先看：
- `doc/dev/ENV_GUIDE.md`（统一 `.env` 与优先级）
- `doc/DockerDeploy.md`（根目录 `docker-compose.yml`）
- `README.md` / `README_PRODUCTION.md`（整体入口）

---

## 1. 服务与端口

- `main_api`：`http://127.0.0.1:6800`
- `simpleOutline`（大纲 Agent）：`http://127.0.0.1:10001`
- `slide_agent`（内容 Agent）：`http://127.0.0.1:10011`
- `personaldb`（知识库）：`http://127.0.0.1:9100`

> Docker 部署下，前端通常通过 `http://127.0.0.1:5174`（Nginx 容器）访问，并以 `/api/` 反向代理到 `main_api`。

---

## 2. 环境变量（统一 `.env`）

### 2.1 推荐做法

在项目根目录维护一份 `.env`（从 `env_template.txt` 复制）：

```bash
cp env_template.txt .env
# 修改 .env：填入 OUTLINE_* / PPT_WRITER_* / PPT_CHECKER_* / EMBEDDING_* 等
```

### 2.2 实际加载优先级（代码行为）

各服务代码均遵循：**不覆盖系统环境变量**，并按以下顺序合并：

1. 系统环境变量
2. 当前服务目录 `.env`（可选，用于本机临时覆盖）
3. 项目根目录 `.env`

> `env_template` 只是模板文件：`start.py` / `backend/start_backend.py` 会在必要时拷贝为 `.env`，但运行时不会自动读取 `env_template`。

---

## 3. 启动方式

### 3.1 一键启动（推荐，含前端）

```bash
python start.py
```

特点：
- 自动安装依赖（Python + Node）
- 自动按依赖顺序拉起所有服务并汇总日志到 `logs/*.log`

### 3.2 仅启动后端（不含前端）

```bash
python backend/start_backend.py
```

适用：前端用 `npm run dev` 独立启动，或你有自定义前端部署。

### 3.3 手动逐个启动（按依赖顺序）

建议顺序：`personaldb` → `simpleOutline` → `slide_agent` → `main_api`

```bash
# 1) personaldb（建议用 uvicorn 以便自定义 host/port）
cd backend/personaldb
uvicorn main:app --host 0.0.0.0 --port 9100

# 2) simpleOutline
cd ../simpleOutline
python main_api.py --host 0.0.0.0 --port 10001 --agent_url http://127.0.0.1:10001/

# 3) slide_agent
cd ../slide_agent
python main_api.py --host 0.0.0.0 --port 10011 --agent_url http://127.0.0.1:10011/

# 4) main_api
cd ../main_api
uvicorn main:app --host 0.0.0.0 --port 6800
```

---

## 4. Docker 部署（推荐）

Docker 以 **根目录 `docker-compose.yml`** 为准：

```bash
cp env_template.txt .env
docker compose up --build
```

更多说明见：`doc/DockerDeploy.md`。

---

## 5. 健康检查与自检

- `main_api`：`GET /healthz` → `{"ok": true}`
- `simpleOutline`：`GET /.well-known/agent.json`
- `slide_agent`：`GET /.well-known/agent.json`

---

## 6. 常见问题（高频）

- 端口占用：优先用 `python start.py`（自带端口检测与清理）。
- Docker 内访问宿主机服务：通常使用 `host.docker.internal`（不同系统可能有差异）。

---

## 相关文档

- 环境变量：`../dev/ENV_GUIDE.md`
- Docker 部署：`../DockerDeploy.md`
- API 参考：`./backend_api_reference.md`
- 后端架构：`./backend_architecture.md`
