# TeachDo 整体重构计划（补充版）

## 0. 文档说明（本次为补充，不是替换）
- 本文在原有计划基础上补充细化，目标是形成可直接执行的实施文档。
- 原计划/背景文档参考：`doc/dev/DEVELOPMENT_PLAN.md`（本文优先用于落地实施，若两者冲突以本文为准）。
- 核心方向不变：
1. 保留现有 `teachdo-frontend`，在其上重构。
2. 不迁移历史旧前端样式流程页，仅迁移能力链路。
3. 以 TeachDo 核心链路可用为 V1 首要目标（能力来源为现有 ai2ppt 链路）。
- 更新时间：2026-02-15。

## 1. 项目目标
- 保留现有 `teachdo-frontend` 的工作台视觉与交互结构。
- 在工作台内替换原 PPT 生成单元，接入现有 PPT 生成引擎能力链路。
- 以 `teachdo-frontend` 作为唯一前端入口，确保单前端架构。
- 新建 `teachdo` 仓库，使用干净历史（不保留 ai2ppt 的 git commit 历史），仅迁移需要的代码与文档。

## 2. 已确认范围与原则
- 保留：
1. TeachDo 工作台布局、页面风格、信息架构。
2. 课程/单元管理与 Tab 工作流。
- 替换：
1. `teachdo-frontend` 现有 PPT 生成模块的业务能力实现。
2. 虚构接口调用与不稳定解析逻辑。
- 不迁移：
1. 历史旧前端页面样式与流程页面（`Home/Outline/PPT`）。
- 优先级：
1. 先确保 TeachDo 核心链路完整可用。
2. 再扩展非 PPT 模块能力。

## 2.1 命名与文案清理规则（迁移期与交付期）
- 迁移期（当前文档与实施阶段）允许在文档中出现 `ai2ppt` 术语，用于描述迁移来源能力、接口路径和历史代码上下文。
- 交付期（重构后项目）对外命名统一为 `TeachDo`：
1. 用户可见（UI 文案/标题/帮助文档）不出现 `ai2ppt/AI2PPT`。
2. 代码实现（前端+后端）不保留 `ai2ppt/AI2PPT` 字符串与语义命名（允许文档中的迁移说明保留）。
- UI 文案、页面标题、帮助文档、品牌标识中的历史品牌字样在上线前全部替换。
- 前端业务函数命名使用 `teachdo`/`ppt` 语义，不继续新增 `ai2ppt` 语义命名。
- 后端兼容路径可暂保留 `/tools/aippt*`，但前端对外展示不暴露该命名。

## 2.2 关键决策（已确认）
1. API 访问策略：统一走相对路径 `/api`（Dev 用 Vite proxy，Prod 用 Nginx 反代）。
2. 模板策略：沿用现有后端模板（`/templates` + `/data/*`）。
3. KB/会话作用域：`sessionId/user_id = course.id`（course-scoped）。
4. 导出策略：只使用编辑器导出（PPT 预览页不提供导出）。
5. 编辑器形态：工作台内仅预览；点击“进行编辑”跳转到独立编辑器页面。
6. 新仓库策略：`teachdo` 采用干净历史（新建 git 仓库，不保留 ai2ppt git 历史）。
7. KB 引用策略：仅在 PPT 生成阶段默认开启“引用知识库素材”（当 KB 无 `ready` 文件时自动关闭并禁用）。
8. KB 检索范围：生成时可选；默认仅引用 `folder_id=0` 上传素材，可勾选包含 `folder_id=1` 生成产物。
9. 编辑器迁移工具链策略：采用策略 A（保留 TeachDo 工具链，逐步引入旧编辑器依赖修复编译问题）。

## 3. 可行性结论与依据

### 3.1 可行性结论
- 可行，且技术路径明确。
- 风险主要在编辑器模块体量与依赖差异，可通过模块隔离+分阶段集成控制。

### 3.2 关键依据（代码现状）
- 后端已提供可用主链路接口：`/tools/aippt_outline_unified`、`/tools/aippt`、`/templates`、`/data/*`、`/healthz`。
- TeachDo 当前工作台已具备可替换边界：
1. `CourseWorkspaceView` 以 `PPTView` 作为独立单元。
2. `aiService` 已有部分真实接口调用，但夹杂虚构接口。
- 当前 `start.py` 与 `docker-compose.yml` 仍指向旧 `frontend/`，需切换到 `teachdo-frontend/`。

## 4. V1 验收标准
1. 大纲能力：仅基于主题输入流式生成大纲并可保存（V1 不在大纲阶段引用知识库/上传素材）。
2. 模板能力：可从后端拉取模板并选择模板。
3. 内容能力：可流式生成 PPT 内容，支持增量渲染与结束收尾。
4. 编辑能力：PPT 预览页提供“进行编辑”入口，跳转到独立编辑器页面进行编辑。
5. 导出能力：仅在编辑器页面支持导出 PPTX（预览页不提供导出）。
6. 路由能力：工作台标签路由化，可直达、可刷新恢复。
7. 稳定性：不再依赖虚构接口导致运行时报错。

## 5. 架构与接口设计

### 5.1 前端路由（全标签路由化）
- `/`：课程列表。
- `/course/:courseId`：课程工作台（当课程有单元时自动跳转到默认单元页）。
- `/course/:courseId/unit/:unitId/:tab`：单元标签页。
 - `tab` 取值：`outline`、`lesson`、`ppt`。
- `/course/:courseId/:tab`：课程级标签页。
 - `tab` 取值：`kb`、`assistant`。
- `/course/:courseId/unit/:unitId/ppt/editor`：独立编辑器页面路由（从工作台跳转进入）。

### 5.2 后端接口映射（V1）
- 前端统一走相对路径：以 `/api` 作为唯一 API 前缀（Dev 用 Vite proxy；生产反代在开发完成后处理）。
- 下述为 main_api 实际路径（不带 `/api` 前缀）；前端访问时统一加上 `/api`。
- `GET /healthz`：服务可用性检查。
- `GET /templates`：模板列表（返回 `data` 数组）。
- `POST /tools/aippt_outline_unified`：统一大纲流式生成（form-data）。
- `POST /tools/aippt`：PPT 内容流式生成（SSE）。
- `GET /data/{filename}`：模板相关静态资源。

### 5.3 TeachDo 服务层标准化（目标形态）
- 统一在 `teachdo-frontend/src/services/aiService.ts` 维护接口调用，不再散落组件内直接 `fetch`。
- `BASE_API = '/api'`，所有请求走相对路径（不使用 `http://localhost:6800` 这类绝对地址）。
- 统一提供：
1. `checkBackend()`
2. `getTemplates()`
3. `generateOutline(course, unit, onStream)`
4. `generatePPT(course, unit, outline, template, onSlide)`
- 对 V1 非核心能力（lesson/assistant）提供可运行兜底，避免硬失败。
 - 统一会话/知识库作用域：`sessionId/user_id = course.id`（course-scoped）。

### 5.4 数据模型调整（teachdo-frontend）
- `CourseUnit` 增加 `outlineMeta`：记录来源模式、文件名、时间戳。
- `CourseUnit` 增加 `editorDocument`：记录编辑器文档快照（slides/theme/viewport）。
- `CourseUnit` 保留 `presentation`：用于预览与快速回显。
- `CourseUnit` 保留 `selectedTemplateId`：用于生成与回显一致性。

### 5.5 知识库真实化与“产物入库”（新增）
#### 5.5.1 知识库定义与原则
- 知识库（KB）的目标是“可检索语料”，用于 `generateFromUploadedFile`（KnowledgeBaseSearch）检索引用。
- 本计划中“KB 素材”指：教师在知识库页面上传并向量化的文件内容（默认 `folder_id=0`），生成时通过检索返回的片段（topk chunks）作为上下文引用。
- 编辑器文档（`editorDocument` 的 slides/theme 等 JSON）属于“可编辑资产”，不直接作为 KB 文件存储。
- 生成产物（大纲/讲稿/最终 PPT 文本）应“入库”为可检索语料：以文本形式写入 personaldb（向量化），让后续生成/助教可引用。

#### 5.5.1.1 持久化边界（新增，已确认）
- 不需要跨设备/多人共享 `editorDocument`。
- `editorDocument` 的持久化策略：
1. V1：沿用编辑器自身的本地持久化能力（IndexedDB 或等价机制），并在关键节点同步一份快照到 `CourseUnit.editorDocument` 便于工作台预览回显。
2. 不引入后端“编辑资产存储”作为 V1 前置条件。

#### 5.5.1.2 KB 检索过滤（folder_id，新增）
- 目标：生成时默认只引用“上传素材”（`folder_id=0`），可选包含“生成产物”（`folder_id=1`）。
- 推荐实现（最小改动，前后端一致）：
1. 前端在生成请求中携带 `kb_folder_ids`（例如 `[0]` 或 `[0,1]`）。
2. main_api 在调用 slide_agent 时把该字段透传进 `metadata`（例如 `metadata.kb_folder_ids=[0]`）。
3. slide_agent 的 `KnowledgeBaseSearch` 工具读取 `metadata.kb_folder_ids`，对 personaldb `/search` 返回的 `metadatas` 做过滤，只保留允许的 `folder_id`，并同步过滤对应的 `documents`。
- 进阶优化（后续再做）：personaldb `/search` 增加 `folder_ids` 过滤参数并下推到 Chroma query 的 `where`，避免“先检索再过滤”导致 topk 降低。

#### 5.5.2 后端最小新增接口（建议新增在 main_api 下，前端以 `/api` 前缀访问）
> 说明：
> - 前端统一访问：`/api/...`（Vite proxy rewrite 去掉 `/api`，命中 main_api 的实际路由）。
> - main_api 作为 BFF，仅做鉴权/参数校验/转发与响应裁剪，personaldb 作为 KB 持久化存储与检索引擎。
> - 需要配置 `PERSONAL_DB` 指向 personaldb 服务地址（例如 `http://127.0.0.1:9100`），否则 KB 上传/检索不可用。

##### 5.5.2.1 `POST /api/kb/upload`（上传素材并向量化）
- Content-Type：`multipart/form-data`
- 请求字段：
1. `user_id`（string，必填）：`course.id`
2. `folder_id`（int，选填，默认 0）：0=上传素材，1=生成产物
3. `file_id`（string，选填）：不传则由服务端生成
4. `file_type`（string，选填）：不传则由文件扩展名推断
5. `file`（binary，必填）
- 服务端 `file_id` 生成规则（上传素材）：
1. 格式：`upload:{courseId}:{epochMs}:{rand3}`
2. 例：`upload:course-1730000000000:1730000000000:042`
- 转发到 personaldb：`POST {PERSONAL_DB}/upload/`，字段映射：
1. `userId=user_id`
2. `fileId=file_id`
3. `folderId=folder_id`
4. `fileType=file_type`
5. `file=file`
- 成功响应（200）：
```json
{
  "ok": true,
  "data": {
    "user_id": "course-1730000000000",
    "file_id": "upload:course-1730000000000:1730000000000:042",
    "file_name": "课程标准.pdf",
    "file_type": "pdf",
    "folder_id": 0,
    "status": "ready"
  }
}
```
- 失败响应（示例）：
```json
{ "ok": false, "error": { "code": "KB_UPLOAD_FAILED", "message": "..." } }
```
- 约束：
1. 不向前端返回 personaldb 的 `markdown_content`（可能过大），如需要可返回 `markdown_length`。

##### 5.5.2.2 `GET /api/kb/files/{user_id}`（列出知识库文件）
- 路径参数：
1. `user_id`（string）：`course.id`
- Query（可选）：
1. `folder_id`（int）：只返回某一类（0 上传素材 / 1 生成产物）
- 行为：转发 personaldb `GET /files/{user_id}`，必要时在 main_api 做 folder 过滤
- 成功响应（200）：
```json
{
  "ok": true,
  "data": [
    {
      "user_id": "course-1730000000000",
      "file_id": "upload:course-1730000000000:1730000000000:042",
      "file_name": "课程标准.pdf",
      "file_type": "pdf",
      "folder_id": 0
    }
  ]
}
```

##### 5.5.2.3 `POST /api/kb/vectorize/text`（把生成产物写入 KB 索引）
- Content-Type：`application/json`
- 请求字段：
1. `user_id`（string，必填）：`course.id`
2. `file_id`（string，必填）：推荐使用“确定性命名”，便于覆盖更新
3. `file_name`（string，必填）
4. `file_type`（string，选填，默认 `md`）
5. `folder_id`（int，选填，默认 1）
6. `content`（string，必填）
- `file_id` 命名规范（生成产物，确定性，覆盖更新）：
1. 大纲：`gen:{courseId}:{unitId}:outline`
2. 生成 PPT（未编辑）：`gen:{courseId}:{unitId}:slides`
3. 编辑后最终版：`gen:{courseId}:{unitId}:slides_final`
- 转发到 personaldb：`POST {PERSONAL_DB}/vectorize/text`，字段映射：
1. `userId=user_id`
2. `fileId=file_id`
3. `fileName=file_name`
4. `fileType=file_type`
5. `folderId=folder_id`
6. `content=content`
- 成功响应（200）：`{ "ok": true }`（或携带 personaldb 返回的 `embedding_result`）

##### 5.5.2.4 `DELETE /api/kb/files/{user_id}/{file_id}`（删除 KB 文件向量）
- 路径参数：
1. `user_id`（string）：`course.id`
2. `file_id`（string）
- 行为：转发到 personaldb 新增接口 `DELETE /files/{user_id}/{file_id}`
- 成功响应（200）：`{ "ok": true }`
- 说明：若无删除接口，前端“删除”只能删除本地展示，检索仍可能命中旧向量（不可接受）。

#### 5.5.3 personaldb 需补齐能力（为满足 course.id 为字符串）
- 允许 `user_id` 为字符串（`course.id`），并确保：
1. `GET /files/{user_id}`：路径参数类型改为 string（当前实现是 int，会导致 course.id 无法列出文件）。
2. `list_files_by_user(user_id)`：统一使用 `str(user_id)` 归一对比，确保 metadata 中 `user_id` 一致。
- 允许 `file_id` 为字符串（与 main_api 命名规范一致），并确保：
1. `/vectorize/text` 的 `fileId` 字段允许 string（当前是 int，会导致 `gen:{...}` 无法入库）。
2. `insert_file_vectors` / `delete_file_vectors` / `list_files_by_user` 不假设 `file_id` 为 int。
- 增加删除接口（必须）：
1. `DELETE /files/{user_id}/{file_id}`：删除该 user 的指定 file 对应向量。
2. 实现建议：调用现有 `ChromaDB.delete_file_vectors(user_id, file_id)`，并返回 `{ "ok": true }`。
- （可选，建议）collection 命名安全：
1. 统一将 collection 名称规范化为 `user_{safe_user_id}`（替换不安全字符），避免未来 user_id 形态变化导致 Chroma collection 创建失败。

#### 5.5.3.1 KB 持久化与目录约定（落盘，新增）
- personaldb 已使用 `chromadb.PersistentClient` 落盘存储。
- 默认落盘目录（相对 repo root）：`var/cache/personaldb/chromadb`。
1. 当前仓库使用 `AI2PPT_CACHE_DIR` 控制基路径（默认 `var/cache`），详见 `backend/personaldb/runtime_paths.py:get_cache_dir()`。
2. 当前仓库临时文件目录基路径由 `AI2PPT_TMP_DIR` 控制（默认 `var/tmp`）。
3. TeachDo 新仓库交付前会把上述环境变量命名替换为 `TEACHDO_CACHE_DIR`、`TEACHDO_TMP_DIR`、`TEACHDO_LOG_DIR`（代码实现不保留 `AI2PPT_*`）。
- 本地开发时：只要不删除 `var/cache`，personaldb 重启后 KB 仍可检索命中。
- Docker/部署（阶段 H 再做）：
1. 需要将 `var/cache/personaldb` 挂载为 volume，否则容器重建会丢失 KB 数据。
2. 生产建议显式配置 `TEACHDO_CACHE_DIR=/data/cache` 并做持久化挂载（路径可按你部署习惯调整）。

#### 5.5.4 前端知识库页面（TeachDo）与后端同步策略
- 知识库页面作为“上传入口与状态中心”，负责：
1. 上传：调用 `/api/kb/upload`，上传过程中显示 uploading/progress（前端模拟进度即可），成功后标记 ready。
2. 列表：进入页面或刷新时调用 `/api/kb/files/{course.id}`，与本地 `currentCourse.kbFiles` 合并校准。
3. 删除：调用 `/api/kb/files/{course.id}/{file_id}`，成功后移除本地条目。

#### 5.5.5 生成产物入库（默认开启）
- 产物入库以“文本索引”为准，避免存 raw JSON：
1. 大纲保存后：将最终大纲 markdown 作为文本写入 `/api/kb/vectorize/text`（`file_type='md'`）。
2. PPT 生成后：将生成的 slide 文本（标题+要点+备注）拼成 markdown，写入 `/api/kb/vectorize/text`。
3. 编辑器退出/保存后：对编辑后的 slide 文本重新写入同一 `file_id`（覆盖旧向量），确保 KB 命中的是“最终版”。
- `folder_id` 归类约定（已确认）：
1. `folder_id=0`：上传素材（教师上传的文件）。
2. `folder_id=1`：生成产物（大纲/讲稿/最终 PPT 文本等入库索引）。

### 5.6 `/tools/aippt` SSE 协议与 `AIPPTSlide` 结构（补充）
#### 5.6.1 SSE 事件边界与解析规则
- main_api 的流式接口使用 SSE：事件以空行分隔（`\n\n` 或 `\r\n\r\n`）。
- 单条事件可能包含多行 `data:`（尤其是 payload 内带换行时），需要将所有 `data:` 行拼接为完整 payload。
- 结束标记：payload 为 `[DONE]`。
- 容错：
1. 某些模型可能把 JSON 包在 ```json / ``` 围栏内，需要先移除围栏再 `JSON.parse`。
2. 避免“按行解析”的实现，因为后端会合法输出多行 data，按行会导致 JSON 被截断。
- 参考实现（迁移来源：ai2ppt 仓库）：`frontend/src/views/PPT/index.vue` 的 `processEvent/pump`。

#### 5.6.2 `AIPPTSlide`（后端每页生成的 JSON）约定
- WriterAgent 的输出遵循固定结构：顶层键名为 `type` 与 `data`（可选 `images`）。
- `type` 取值：`cover`、`contents`、`transition`、`content`、`end`。
- `data` 常见字段：
1. `cover`：`data.title`、`data.text`
2. `contents`：`data.items: string[]`
3. `transition`：`data.title`、`data.text`
4. `content`：`data.title`、`data.items: { kind?: string, title: string, text: string }[]`（可能包含 `kind=chart|image` 等）
5. `end`：可能有 `data.text`
- `images`（可选）：当启用 SearchImage 工具时，可能追加 `images: [{ id, src, alt, width?, height? }]`。

#### 5.6.3 AI Slide 到编辑器 `Slide[]` 的映射策略（必须复用）
- 目标：工作台预览与编辑器渲染必须一致，因此不能用“TeachDo 自定义的简化 slide 数据结构”替代编辑器的 `Slide` 类型。
- 推荐方案：迁移并复用旧前端的生成器与类型体系（迁移来源：ai2ppt 仓库）：
1. `frontend/src/hooks/useAIPPT.ts` 的 `AIPPTGenerator(templateSlides, aiSlides, imgs)` 负责把 `AIPPTSlide[]` 映射为编辑器 `Slide[]`。
2. `frontend/src/types/slides.ts`、`frontend/src/configs/*`、`frontend/src/utils/*` 中与渲染/导出相关的类型与工具按需迁入 `teachdo-frontend/src/editor-runtime`。
- TeachDo 侧的数据落点：
1. 生成时：把生成出的 `Slide[]` + `theme` + `viewport` 写入 `CourseUnit.editorDocument`（用于后续预览与进入编辑器）。
2. 预览时：直接读取 `CourseUnit.editorDocument` 渲染（只读模式）。

## 6. 分阶段实施计划（含 DoD）

### 6.0 当前进度（滚动更新）
- 更新：2026-02-15
- 当前仓库状态：
  - [x] 已完成迁移并初始化新仓库（已 `git init`）
  - [x] 已完成一次“初始提交”（迁移基线已固定，后续改动可独立追踪）
  - [x] 已完成阶段 A（仓库与启动链路切换）
  - [x] 已完成阶段 B（工作台路由化）
  - [ ] 下一步优先级：阶段 C0（KB 后端打底）-> 阶段 C（大纲模块重构）

### 阶段 A：仓库与启动链路切换
- [ ] 1. 创建新仓库 `teachdo`（干净历史）：
  - [x] 迁移代码到新目录（排除 `.git/` 与运行期目录如 `venv/`、`**/node_modules/`、`var/`、`logs/`、`**/__pycache__/` 等）
  - [x] 在新目录执行 `git init`
  - [ ] 配置新的 remote
  - [x] 首次 `git commit`（`chore: initial import`；commit 前确认 `.gitignore` 不会提交本地环境文件）
- [x] 2. 修正忽略规则（在新仓库中执行）：
  - [x] 确认根目录 `.gitignore` 未忽略 `/teachdo-frontend`
  - [x] （可选）补充忽略：`.run/`、`.kilocode/`（如不希望提交 IDE/工具配置目录）
- [x] 3. 修改 `start.py`：前端目录从 `frontend/` 切换为 `teachdo-frontend/`。
  - 同步统一端口：`teachdo-frontend/vite.config.ts` 当前 `server.port=3000`，因此 `start.py` 默认 `FRONTEND_PORT` 也应调整为 `3000`（保留环境变量覆盖能力）。
- [x] 4. 为 `teachdo-frontend/vite.config.ts` 增加 dev proxy：
  - `/api` -> `http://127.0.0.1:6800`，rewrite 去掉 `/api` 前缀。
- [x] 5. TeachDo 前端服务层与 API 基址统一（为后续 C/D 阶段铺路）：
  - 将 `teachdo-frontend/src/services/aiService.ts` 统一改为 `BASE_API='/api'`（不依赖 `VITE_API_BASE`、不写死 `http://localhost:6800`）。
  - 抽一个可复用的 SSE 解析工具（按 `5.6.1` 规则），供大纲与 PPT 两处共用，避免各写一套导致解析边界不一致。
  - DoD：
    1. `python start.py` 能启动 `teachdo-frontend`。
    2. Dev 环境前端通过 `/api/*` 访问后端，无需改代码切换 baseUrl。
    3. Docker/生产部署相关内容延后到“开发完成后”再处理（见阶段 H）。
    4. 可运行一键验证脚本并通过（至少验证 `/healthz`、`/templates` 通过 `teachdo-frontend` 的 `/api` 代理可访问，见 `8.4`）。

### 阶段 B：工作台路由化
- [x] 1. 将当前 tab 内部状态切换为 URL 驱动切换（可直达）。
- [x] 2. 增加 `courseId/unitId/tab` 参数守卫与纠错回退。
- [x] 3. 刷新后可恢复到当前课程、单元和标签页。
- DoD：
1. 手动输入任一路由均可进入正确页面或自动回退。
2. 浏览器刷新后状态一致。

### 阶段 C0：KB 后端打底（必须先做）
> 目标：让 KB 上传/列表/删除/产物入库成为“可用的后端能力”，并确保 KB 不可用时不会阻断 PPT 生成主链路。
1. main_api 增加 KB BFF（前端统一以 `/api/...` 访问）：
- `POST /kb/upload`、`GET /kb/files/{user_id}`、`POST /kb/vectorize/text`、`DELETE /kb/files/{user_id}/{file_id}`（契约见 `5.5.2`）。
- 响应统一 `{ ok: boolean, data?: any, error?: { code, message } }`，避免前端散落判断。
2. personaldb 适配（落盘与向量一致性）：
- `GET /files/{user_id}`：`user_id` 改为 string。
- `POST /vectorize/text`：`fileId/userId` 支持 string；写入 metadata 时保持 `file_id/user_id/folder_id` 一致类型（建议统一存 string）。
- 新增 `DELETE /files/{user_id}/{file_id}`：调用 `delete_file_vectors(user_id, file_id)` 删除该文件向量。
3. slide_agent 兼容性与过滤：
- `KnowledgeBaseSearch` 移除 `assert PERSONAL_DB`（未配置时返回 `(False, "PERSONAL_DB 未配置，跳过知识库检索")`，不得抛异常阻断生成）。
- 支持 `metadata.kb_folder_ids` 过滤：对 personaldb `/search` 返回的 `metadatas/documents` 同步过滤，仅保留允许的 `folder_id`。
4. main_api `/tools/aippt` 的 KB 降级（避免误开关导致 500）：
- 当 `PERSONAL_DB` 未配置或 personaldb `/healthz` 不可用时，强制将 `generateFromUploadedFile=false`（或至少不把 `KnowledgeBaseSearch` 加入 `search_engine`）。
- 记录日志但不中断生成。
- DoD：
1. `/api/kb/upload`、`/api/kb/files/*`、`/api/kb/vectorize/text`、`/api/kb/files/*`(DELETE) 可联调通过。
2. `PERSONAL_DB` 缺失或 personaldb 停止时，PPT 生成仍可用（仅自动禁用 KB 生成）。

### 阶段 C：大纲模块重构
1. 在 `OutlineView` 中接入 `/api/tools/aippt_outline_unified`。
2. 主题必填；V1 只支持“主题模式”（不在大纲阶段引用知识库/上传素材，也不在 Outline 页面上传文件）。
3. 保留现有对比/编辑/保存交互，替换底层流式生成实现。
4. 统一错误处理与 toast 文案。
5. 统一传参约定：
- `content` 包含课程与单元上下文（可包含课程名称、单元标题、教学目标等）。
- `user_id = course.id`（用于后续“产物入库”与 PPT 生成阶段 KB 作用域对齐）。
6. 大纲保存后“产物入库”（写入 KB 索引）：
- 调用 `/api/kb/vectorize/text`，`file_id=gen:{courseId}:{unitId}:outline`，`folder_id=1`，`content=最终大纲 markdown`。
- DoD：
1. 主题模式可流式输出并保存。
2. SSE 中断时有明确错误提示，不导致页面崩溃。

### 阶段 D：PPT 模块替换
1. 在 `PPTView` 中使用真实模板接口替换 mock 逻辑。
2. 接入 `/api/tools/aippt` SSE 流，处理增量页生成。
3. 统一 SSE 解析策略（必须与旧前端一致），覆盖跨 chunk、多行 `data:`、`\r\n`、`[DONE]`：
- 以“空行分隔事件”作为解析边界（见 `5.6.1`）。
- 单条事件内拼接多行 `data:` 得到 payload。
- 兼容 ```json 围栏并做容错解析。
4. 将生成结果写入单元状态，并提供进入编辑器入口（“进行编辑”）。
5. 模板契约与生成管线对齐（沿用 ai2ppt 逻辑）：
- 模板列表：`GET /api/templates`。
- 模板详情：`GET /api/data/${templateId}.json`（包含 `slides/theme/width/height`）。
- 生成流：`POST /api/tools/aippt` 返回的每个 SSE payload 解析为 `AIPPTSlide`（JSON）。
- 由 “模板 slides + AIPPTSlide” 生成可编辑 `Slide[]`（与编辑器一致的数据结构），必须复用 `AIPPTGenerator`（见 `5.6.3`），并写入 `CourseUnit.editorDocument`。
6. 高级开关（可选，但建议保留 ai2ppt 功能点）：
- `generateFromWebSearch` 默认打开（使用网络搜索生成）。
- `generateFromUploadedFile` 默认打开（使用知识库生成）；当知识库无 `ready` 文件时自动关闭/禁用。
- KB 检索范围（生成时可选）：
 - 默认仅引用 `folder_id=0` 上传素材（KB 素材）。
 - 可选包含 `folder_id=1` 生成产物（outline/slides/slides_final 等入库文本）。
 - 前端需把选择结果作为 `kb_folder_ids` 传给后端，后端透传到 slide_agent 的 metadata 并在 `KnowledgeBaseSearch` 内执行过滤（见 `5.5.1.2`）。
- 上传文件不在 PPT 页进行：文件上传与管理统一在知识库页面完成，同时上传并向量化到 personaldb，并保存到 `currentCourse.kbFiles`。
7. 会话作用域：
- `sessionId = course.id`。
8. PPT 生成完成后“产物入库”（写入 KB 索引）：
- 调用 `/api/kb/vectorize/text`，`file_id=gen:{courseId}:{unitId}:slides`，`folder_id=1`。
- `content` 推荐拼成 markdown：每页用 `## Slide N` + 标题/要点/备注，便于 KB 检索与引用。
- DoD：
1. 生成过程可见增量页面增长。
2. 完成后可稳定回显、可重新生成。
3. 预览页渲染效果与编辑器一致（同一套 renderer/主题/比例）。

### 阶段 E：编辑器独立页 + 工作台预览
0. 工具链与依赖对齐（编辑器体量最大，需优先保证可编译）：
- 采用策略 A（已确认）：保留 TeachDo 工具链，在 `teachdo-frontend` 内逐步引入旧编辑器依赖并修复编译问题（可能会遇到 Vite 5 -> 7 的兼容差异）。
- 回退策略（仅当 A 卡住时启用）：将 `teachdo-frontend` 的构建工具链下调对齐旧编辑器（Vite/TS/ESLint），先确保编辑器能跑，再逐步升级。
1. 将现有编辑器能力迁入 `teachdo-frontend/src/editor-runtime`（隔离 pinia/store/types/utils/components）。
2. 依赖迁移（必须，来自旧 `frontend/package.json`，按实际引用增量加入）：
- 典型必需：`dexie`、`prosemirror-*`、`echarts`、`html-to-image`、`lodash`、`nanoid`、`tippy.js`、`vuedraggable`、`tinycolor2`、`svg-pathdata`、`svg-arc-to-cubic-bezier` 等。
- 目标：编辑器路由能编译运行，且导出 PPTX 可用（依赖缺失会直接导致功能不可用）。
3. 工作台 `PPTView` 只做“预览模式”：
- 使用与编辑器相同的渲染组件（同一份 `Slide` 数据结构与主题配置）。
- 预览布局采用“缩略图列表 + 当前页大画布”（与编辑器一致的 viewport 尺寸/比例）。
- 提供按钮“进行编辑”，跳转到 `/course/:courseId/unit/:unitId/ppt/editor`。
4. 独立编辑器页面：
- 全功能编辑、撤销/重做、插入元素等保持编辑器自有风格。
- 导出仅在编辑器内完成（PPTX）。
5. 状态回写：
- 进入编辑器时从 `CourseUnit.editorDocument` 加载，缺失则从最新生成结果初始化。
- 退出/返回时把 editor 的 `slides/theme/viewport/title` 写回 `CourseUnit.editorDocument`，以便预览页复显。
- 退出/保存时“产物入库”（写入 KB 索引）：将最终 slide 文本写入 `/api/kb/vectorize/text`，`file_id=gen:{courseId}:{unitId}:slides_final`，覆盖更新向量。
- DoD：
1. 能从工作台进入编辑器并返回。
2. 编辑后数据可持久化到当前单元。
3. 可导出 PPTX。

### 阶段 F：非 PPT 标签收敛
1. 保留 `lesson/kb/assistant` 页面与路由结构。
2. 去掉直接报错的虚构后端调用，改为可运行状态。
3. 在页面上明确“能力建设中/后续重构”的状态提示。
4. 知识库页面归口上传与保存（前置条件：阶段 C0 已完成后端 KB 能力）：
- 支持真实上传并写入 personaldb（通过 `/api/kb/upload`），并同步到 `currentCourse.kbFiles`（状态流转：uploading/processing/ready/error）。
- 支持拉取后端文件列表（`/api/kb/files/{course.id}`）做一致性校准。
- 支持删除文件（需要后端删除接口），删除后不再被检索命中。
- PPT 生成页读取 `kbFiles` 状态联动 `generateFromUploadedFile`（默认打开，无可用 ready 文件时禁用）。
5. 联调与回归：
- 验证“产物入库”写入后，PPT 生成阶段在启用 KB 时能命中检索（可通过 personaldb `/search` 验证）。
- DoD：
1. 三个页面均可正常进入且无 runtime error。
2. 不影响 outline/ppt 主链路。

### 阶段 G：回归与发布
1. 链路回归：大纲、模板、流式生成、编辑、导出全流程。
2. 工程校验：`typecheck`、`lint`、`build`。
3. 文档更新：开发启动、路由说明、接口映射、已知限制。
4. 品牌与命名清理（交付前必须完成）：
- 用户可见（UI 文案/标题/帮助文档）不出现 `ai2ppt/AI2PPT`。
- 代码实现（前端+后端）不出现 `ai2ppt/AI2PPT` 字符串：
1. teachdo-frontend：移除注释/变量/模块名中的历史词。
2. backend：将 `AI2PPT_*` 环境变量等历史命名替换为 `TEACHDO_*`（并同步更新读取逻辑与文档）。
- DoD：
1. 核心流程通过，构建通过。
2. 文档可支撑新成员按文档启动与联调。
3. 用户可见页面和对外帮助文档中不出现 `ai2ppt/AI2PPT`（迁移说明文档可保留）。
4. 在新仓库执行 `rg -n \"ai2ppt|AI2PPT\" teachdo-frontend backend` 无匹配结果（文档目录不做此约束）。

### 阶段 H：部署与 Docker（开发完成后再做）
1. 修改 `docker-compose.yml`：frontend 构建上下文切换为 `./teachdo-frontend`。
2. 为 `teachdo-frontend` 补齐生产容器化文件：
- 增加 `teachdo-frontend/Dockerfile`（构建 dist + 静态托管）。
- 增加 `teachdo-frontend/nginx.conf`，反代 `/api/` 到 `main_api:6800`，并关闭 buffering 以兼容 SSE。
3. 验证 `docker compose up --build` 可运行，且 SSE 在代理下不被缓冲截断。

## 7. 任务拆分与里程碑建议

### M1（基础可运行）
- 完成阶段 A + B。
- 产出：新仓库可启动、工作台路由化完成。

### M2（生成可用）
- 完成阶段 C0 + C + D。
- 产出：Outline/PPT 真实接口链路打通。

### M3（编辑闭环）
- 完成阶段 E。
- 产出：工作台预览 + 独立编辑器 + 导出闭环。

### M4（稳定发布）
- 完成阶段 F + G。
- 产出：V1 发布候选版本。

## 8. 测试计划

### 8.1 功能测试
1. 路由：
- 非法 `courseId`、`unitId`、`tab` 均可回退到可用页面。
2. 大纲：
- 主题模式可流式生成并保存。
3. PPT：
- 模板拉取成功，流式生成成功，预览页可见。
4. 编辑：
- 可进入编辑器、修改并返回，状态可持久化。
5. 导出：
- PPTX 可导出且文件可打开。

### 8.2 自动化测试（最低要求）
1. SSE 解析单元测试（必须）：
- 覆盖 `\n\n` 与 `\r\n\r\n` 分隔、多行 `data:` 拼接、```json 围栏、`[DONE]`、跨 chunk 缓冲等用例。
2. 路由守卫单元测试（建议）。
3. 关键 store 状态迁移测试（建议）。

### 8.3 最低质量门槛
- `npm run typecheck` 通过。
- `npm run lint` 通过。
- `npm run build` 通过。

### 8.4 一键验证（由助手执行，不需要手工点 UI）
> 目标：在每个里程碑结束时，我可以用脚本完成“可运行性 + 关键接口”验证，减少人工点页面回归。

#### 8.4.1 脚本
- `scripts/verify_endpoints.py`：
1. 支持直连后端（默认）或通过前端 `/api` 代理验证。
2. 覆盖接口：
- `/healthz`
- `/templates`
- `/tools/aippt_outline_unified`（SSE，默认启用；可 `--skip-outline` 跳过）
- `/tools/aippt`（SSE，默认启用；可 `--skip-ppt` 跳过）
- `/kb/*`（仅当阶段 C0 完成后启用；用 `--require-kb` 强制校验）

#### 8.4.2 使用方式（示例）
1. 验证前端 `/api` 代理是否正确（阶段 A 必做）：
- 前提：`teachdo-frontend` dev server 已在 `3000` 启动，后端 main_api 已在 `6800` 启动。
- 命令：`python3 scripts/verify_endpoints.py --base-url http://127.0.0.1:3000 --prefix /api --skip-outline --skip-ppt`
2. 验证后端直连基础接口（不依赖前端）：
- 命令：`python3 scripts/verify_endpoints.py --base-url http://127.0.0.1:6800`
3. 若当前环境未配置模型/外网，仅做前端联调冒烟（用 mock_api 提供固定 SSE 数据）：
- 启动：`python3 -m uvicorn backend.mock_api.mock_main:app --host 127.0.0.1 --port 6800`
- 校验：`python3 scripts/verify_endpoints.py --base-url http://127.0.0.1:6800 --skip-outline`
4. 阶段 C0 完成后校验 KB BFF（会自动上传一个临时小文件并在结束时删除）：
- 命令：`python3 scripts/verify_endpoints.py --base-url http://127.0.0.1:6800 --require-kb --kb-user-id course-smoke`


## 9. 风险与应对
1. 编辑器依赖体量大：
- 通过 `editor-runtime` 命名空间隔离迁入，分批验证。
2. 样式冲突：
- 不迁移历史页面样式，只迁能力代码；控制样式作用域。
3. 流式协议边界：
- 先完善解析器测试，再做联调压测。
4. 仓库迁移遗漏：
- 在迁移清单中加入启动脚本、compose、env、文档四项核对。
5. KB 依赖 personaldb（配置/可用性）：
- 通过阶段 C0 的“KB 降级策略”保证 personaldb 不可用时不阻断 PPT 主链路，仅关闭 KB 检索。

## 10. 回退方案
- 若编辑器集成阻塞：
1. 保留 `PPTView` 预览页生成能力先上线。
2. 编辑器路由以 feature flag 受控灰度开启。
- 若 SSE 解析不稳定：
1. 先降级为完整响应后一次性渲染。
2. 同步保留流式解析分支继续修复。

## 11. 交付清单
1. 新仓库 `teachdo`（含历史迁移说明）。
2. `teachdo-frontend` 单前端可启动/可构建。
3. 工作台全标签路由化。
4. Outline/PPT/Editor 主链路可用。
5. 更新后的开发文档与发布说明。

## 12. 默认假设
1. V1 不新增 `/teachdo/*` 后端接口，以现有 `main_api` 能力为准。
2. `teachdo-frontend` 为唯一前端入口，`frontend/` 退出运行链路。
3. 优先保证 TeachDo 核心链路完整可用，非 PPT 模块按可运行收敛。

## 13. 已确认补充
1. 编辑器迁移工具链：采用策略 A（保留 TeachDo 工具链，逐步引入旧编辑器依赖修复编译问题）。
2. 不在新仓库保留旧前端源码备份（这里的“源码备份”指把旧 `frontend/` 作为 `legacy/` 复制进新仓库用于对照；已决定不复制，迁移对照使用原 ai2ppt 仓库）。
3. 命名清理边界：文档可出现 `ai2ppt/AI2PPT`（迁移说明），但代码实现不出现 `ai2ppt/AI2PPT`。
4. 业务策略：大纲只按主题生成；KB 仅在 PPT 生成阶段启用（大纲阶段不引用 KB）。
