# 快速开始

本页用于快速启动 TeachDo 的开发环境，并给出最常用的验证命令。

## 环境准备

建议本机至少具备以下环境：

- Python 3 与可用的虚拟环境
- Node.js 与 `npm`
- 可访问项目依赖源的网络环境
- 根目录 `.env` 配置文件（可由 `env_template.txt` 复制生成）

## 一键启动

这是最推荐的本地启动方式，适合首次启动和日常开发。

```bash
cp env_template.txt .env
python3 start.py
```

如果项目依赖已经安装完成，希望跳过安装阶段：

```bash
python3 start.py --no-install
```

如果需要实时查看聚合日志：

```bash
python3 start.py --tail
```

默认端口如下：

- 前端：`5174`
- 主 API：`6800`
- 大纲服务：`10001`
- PPT 内容服务：`10011`
- 知识库服务：`9100`

## 分别启动前后端

适合前后端联调或只关注单侧改动时使用。

后端全服务：

```bash
cd backend
pip install -r requirements.txt
python3 start_backend.py
```

前端开发：

```bash
cd frontend
npm i
npm run dev
```

TeachDo 前端统一请求相对路径 `/api/*`，开发环境会通过 `frontend/vite.config.ts` 代理到 `http://127.0.0.1:6800/*`。

## Docker 启动

如果你希望使用容器方式本地运行，可以使用以下命令：

```bash
cp env_template.txt .env
docker compose up --build
```

启动后常用访问地址：

- 前端：`http://127.0.0.1:5174`
- 主 API：`http://127.0.0.1:6800`

如本机 `5174` 端口被占用，可临时指定其他端口：

```bash
FRONTEND_PORT=12345 docker compose up --build
```

## GHCR 预构建镜像

仓库已提供 GitHub Actions 工作流用于构建并推送镜像到 GHCR。拉取并运行预构建镜像时，可使用：

```bash
export TEACHDO_IMAGE_PREFIX=ghcr.io/rbetree/teachdo
export TEACHDO_IMAGE_TAG=latest

docker compose pull
docker compose up -d --no-build
```

## 常用校验命令

前端质量校验：

```bash
cd frontend
npm run typecheck
npm run lint
npm run build
```

后端测试：

```bash
venv/bin/python -m pytest backend -q
```

接口冒烟：

```bash
python3 scripts/verify_endpoints.py
```

## 路由速查

- 选择教学资料：`/`
- 工作台：`/material/:materialId/:tab`
- 独立编辑器：`/material/:materialId/ppt/editor`

## 进一步阅读

- [功能介绍](/guide/features)
- [截图展示](/guide/screenshots)
- [项目架构](/dev/architecture)
- [更新日志](/changelog)
