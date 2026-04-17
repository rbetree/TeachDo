# TeachDo 后端（FastAPI 多服务）

TeachDo 后端由 `main_api`（网关）+ 多个下游服务组成，推荐通过脚本统一启动与管理。

## 推荐入口

- 一键启动（含前端）：见根目录 `README.md`（`python3 start.py`）
- 仅启动后端：
  ```bash
	  cd backend
	  pip install -r requirements.txt
	  python3 start_backend.py
	  ```

## 文档入口

- 后端启动说明（偏操作）：`启动说明.md`
- 后端文档导航（索引）：`../doc/backend/README.md`
- API 参考（维护版）：`../doc/backend/backend_api_reference.md`

## 服务与端口（默认）

- `main_api`：6800（对前端唯一入口）
- `simpleOutline`：10001（大纲 Agent）
- `slide_agent`：10011（内容 Agent）
- `personaldb`：9100（知识库）




