# Docker 部署说明（推荐使用根目录 docker-compose.yml）

## 1) 最短路径（可跑通）

```bash
cp env_template.txt .env
# 修改 .env，填入你的 API Key

docker compose up --build
```

启动后访问：
- 前端（Nginx）：`http://127.0.0.1:5174`
- 主 API：`http://127.0.0.1:6800`

> 前端统一通过 `/api/` 反向代理到 `main_api`（容器内地址：`http://main_api:6800`）。
>
> 若本机 `5174` 端口被占用，可临时改用其他端口（不需要改 compose 文件）：
>
> ```bash
> FRONTEND_PORT=12345 docker compose up --build
> ```

## 2) 容器内服务互联（Compose 默认网络）

根目录 `docker-compose.yml` 已固定 main_api 访问下游服务的地址（容器内）：
- `OUTLINE_API=http://outline_api:10001`
- `CONTENT_API=http://content_api:10011`
- `PERSONAL_DB=http://personaldb:9100`

## 3) 本地开发（非 Docker）说明

如果你用 Vite 本地启动前端（`npm run dev`），并在宿主机启动后端服务，请根据实际 IP/端口调整代理配置：
- `teachdo-frontend/vite.config.ts`
