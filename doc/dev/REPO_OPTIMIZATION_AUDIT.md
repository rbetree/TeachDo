# AI2PPT 深入巡检：可优化点清单（按优先级）

最后更新：2026-02-10

本文件汇总一次“深挖式”巡检中发现的可优化点，目标是提升 **安全性 / 稳定性 / 可维护性 / 开发体验 / 前端性能**。  
建议按 **P0 → P1 → P2 → P3** 的顺序逐步落地，并保持“每个主题一个小 PR/commit”的节奏，便于回滚与审查。

---

## P0（必须优先）安全硬化

### 1) `/data/{filename}` 可能存在目录穿越（Path Traversal）

- 现象：接口直接用 `os.path.join("./template", filename)` 拼路径并返回文件（位置：`backend/main_api/main.py` 的 `/data/{filename}`）。
- 风险：攻击者可通过 `../` 或绝对路径读到非模板目录的任意文件（取决于部署环境权限），属于高危信息泄露。
- 建议修复：
  - 使用 `pathlib.Path` 做路径归一化：`(TEMPLATE_DIR / filename).resolve()`。
  - 校验 resolve 后仍位于 `TEMPLATE_DIR` 内，否则直接 `404/400`。
  - 仅允许白名单后缀（如 `.json/.jpg/.png` 等）并拒绝包含路径分隔符的输入。
- 验收：
  - `GET /data/../.env`、`GET /data/%2e%2e%2f...` 等返回 404/400。
  - 合法模板文件可正常下载。

### 2) `/proxy` 存在 SSRF / 开放代理风险

- 现象：`/proxy?url=...` 可代理任意上游 URL，并返回给浏览器同源访问（位置：`backend/main_api/main.py` 与 `backend/mock_api/mock_main.py`）。
- 风险：
  - SSRF：可探测/访问内网服务、云元数据（如 169.254.169.254）、本机端口等。
  - 作为开放代理：被滥用下载/转发内容，带来合规与成本风险。
- 建议修复（至少做一层“安全闸门”）：
  - 增加开关：默认关闭（例如 `ENABLE_PROXY_ENDPOINT=false`），仅开发环境开启。
  - 限制协议：仅允许 `http/https`，禁止 `file://` 等。
  - 限制目标：拒绝内网/本机/保留地址段（127.0.0.0/8、10/8、172.16/12、192.168/16、169.254/16、::1 等）。
  - （可选）改为白名单：仅允许代理图片 CDN/特定域名。
- 验收：
  - 访问 `http://127.0.0.1:...` / `http://localhost/...` / `http://169.254.169.254/...` 被拒绝。
  - 开关关闭时接口直接 404/403。

### 3) 上传文件名未净化，可能写出临时目录（路径注入）

- 现象：personaldb 上传分支把 `upload_file.filename` 拼到 `temp_file_name` 中（位置：`backend/personaldb/main.py`），虽然前面有 UUID 前缀，但 `filename` 若包含路径分隔符仍可能造成路径穿越。
- 建议修复：
  - 永远用 `Path(upload_file.filename).name` 取 basename（或自实现更严格的安全文件名）。
  - 进一步限定允许字符集（只保留 `[a-zA-Z0-9._-]`），其余替换为 `_`。
- 验收：
  - filename 为 `../../x` 或 `a/b` 时仍只会落到 `TEMP_DIR` 里。

### 4) CORS 全放开（`allow_origins=["*"]`）不适合生产

- 现象：`main_api`/`simpleOutline`/`slide_agent`/`mock_api` 目前均设置 `allow_origins=["*"]`。
- 风险：对公网暴露时，浏览器侧跨域访问会被完全放开，易造成滥用或数据泄露风险（取决于接口是否含敏感数据）。
- 建议修复：
  - 用环境变量控制：`CORS_ALLOW_ORIGINS=http://localhost:5174,http://127.0.0.1:5174`。
  - 生产环境只允许你的前端域名。

---

## P1（高收益）稳定性与性能

### 1) 外部抓取缺少 timeout，可能长时间卡死

- 现象：微信搜狗抓取使用 `requests.get(...)` 但未设置 `timeout`（位置：`backend/simpleOutline/weixin_search.py`、`backend/slide_agent/.../weixin_search.py`）。
- 建议：
  - 给所有外部请求加合理超时（连接 + 读取，例如 5s/15s）。
  - 失败时返回可诊断的错误信息（当前多处直接吞异常并返回 `[]`，不利于排查）。

### 2) async 路径中混用同步 HTTP 调用，会阻塞事件循环

- 现象：`backend/main_api/main.py` 的某些 async 流程里使用同步 `httpx.post(...)`。
- 建议：
  - 统一在 async 场景使用 `httpx.AsyncClient`。
  - 内部服务调用统一 `trust_env=False`，避免系统代理导致本机服务误走代理（仓库中已有类似修复实践）。

### 3) MinerU 输出目录固定为 `./output_pdf`，会造成写盘点分散

- 现象：`backend/personaldb/main.py` 中 `MagicPDFConverter(output_dir="./output_pdf")`。
- 建议：
  - 统一改写到 `get_tmp_dir("personaldb") / "output_pdf"`，保证运行期产物仍集中在 `var/tmp/...`。

---

## P2（中收益）开发体验与一致性

### 1) 启动脚本与“根 `.env` 权威”的约定仍不完全一致

- 现象：`backend/start_backend.py` 仍在做“每服务复制 env_template / 读取服务目录 `.env` 并覆盖”这套逻辑。
- 建议：
  - 对齐当前约定：默认只要求根目录 `.env`，服务目录 `.env` 仅本机覆盖。
  - 启动器打印清晰的“配置来源与最终端口/URL”，减少排错成本。

### 2) 端口/变量命名不一致

- 现象：`start.py` 使用 `PERSONALDB_PORT`，但其它文档/compose/环境变量口径更偏向 `PERSONAL_DB`/`PERSONAL_DB_PORT`。
- 建议：
  - 统一命名并做兼容读取（短期），最终只保留一套（长期）。

### 3) 依赖拆分：运行依赖 vs 开发依赖

- 现象：多个服务 `requirements.txt` 含 `pytest`，Docker 镜像也会安装。
- 建议：
  - 拆 `requirements.txt`（运行） + `requirements-dev.txt`（测试/格式化/类型检查），减少镜像体积与供应链风险面。

---

## P3（可持续）前端首屏与构建产物优化

### 1) 产物存在超大 chunk（首包偏大）

- 现象：`npm run build` 提示 `index-*.js` chunk 约 2.94MB（gzip 约 957KB）。
- 建议方向：
  - 清理未使用但会被打包的 import（例如 `frontend/src/App.vue` 中一些静态 import）。
  - 路由级懒加载：`Editor` 等大页面尽量 `() => import(...)`。
  - 针对大型库（ProseMirror / pptxgenjs / echarts）考虑按路由或功能分包。
  - （可选）配置 `manualChunks`，把重依赖拆到独立 chunk，提升缓存命中。

---

## 推荐落地顺序（建议按批次提交）

1) P0：`/data` 路径校验 + `/proxy` 安全闸门 + 上传文件名净化 + CORS 白名单化  
2) P1：外部抓取 timeout + async 内同步请求替换 + MinerU 输出目录集中  
3) P2：启动脚本/变量命名统一 + 依赖拆分  
4) P3：路由懒加载 + 分包/首包优化

---

## 验证清单（每批改动都建议跑）

- Python：`python -m compileall backend`
- 后端单测：`python -m pytest backend -q`
- 前端：`cd frontend && npm run build`
- Docker（如涉及）：`docker compose config` + `docker compose up --build`（冒烟）
