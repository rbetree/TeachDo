# TeachDo 开发计划（当前）

> 更新：2026-02-28  
> 上一版计划已归档：`doc/dev/history/PLAN_ROADMAP_2026-02-17.md`

## 1. 目标与成功标准
- 工作台改为三栏：
  - 左侧 = 导入参考资料库（RAG）
  - 中间 = 大纲 / 教案 / PPT 主区
  - 右侧 = 课程产出文件库（全文上下文 + 文件存放）
- 左侧选中的参考文件：后端按问题/主题做检索（RAG），只把片段放入上下文。
- 右侧选中的产出文件：后端直接把全文放入上下文（不走检索），并且该机制对助教/大纲生成/PPT生成/教案生成全部生效。
- 右侧产出的 DOCX/PPTX：需要后端持久存储，可在右侧列表看到并可再次下载。

---

## 2. 总体方案（关键决策已锁定）

### 2.1 文件分类规则（前后端统一）
- 参考资料（RAG）：`folderId=0`（personaldb 里上传的文件；通常 `file_id` 以 `upload:` 开头）
- 课程产物（全文）：`folderId=1` 且 `file_id` 以 `gen:` 开头（例如 `gen:default_user:<materialId>:outline/slides/...`）
- 全文上传（全文）：`folderId=2` 且 `file_id` 以 `full:` 开头（例如 `full:default_user:<materialId>:<epochMs>:<rand3>`）

说明：实现上用 `file_id` 前缀 `gen:` / `full:` 作为“全文注入”的判定规则（不依赖前端传额外字段）。

### 2.2 选择状态存储（不引入新 schema）
继续复用 `TeachingMaterial.kbFileIds` 存储“当前课程选中的文件ID”：
- 左侧只增删“参考资料ID（非 `gen:`/`full:`）”
- 右侧只增删“全文注入ID（`gen:`/`full:`）”

好处：不改现有数据结构；所有 AI 请求天然能拿到“用户选中集合”。

### 2.3 右侧产物 DOCX/PPTX 的“持久存储”实现方式
- 新增后端 Artifacts 文件存储（落盘到 `var/artifacts/`，并提供 list/upload/download/delete API）。
- DOCX：在调用 `/lesson/export/docx` 时边返回下载、边在后端保存一份到 artifacts。
- PPTX：前端在导出 PPTX 时生成 `Blob`，额外上传到 artifacts；右侧列表即可展示并可再次下载。

---

## 3. 后端改动（`backend/main_api`）

### 3.1 “全文注入（gen:/full:）”能力（对所有相关端点生效）
新增通用逻辑：
1. `kb_file_ids` 归一化后，按 `gen:`/`full:` 拆分：
   - `full_ids = [id for id in kb_file_ids if id.startswith("gen:") or id.startswith("full:")]`
   - `rag_ids = [id for id in kb_file_ids if not (id.startswith("gen:") or id.startswith("full:"))]`
2. 若 personaldb 可用：
   - 对 `rag_ids`：走现有 `/search` 取片段（RAG）
   - 对 `full_ids`：调用 personaldb `GET /files/{user_id}/{file_id}/content` 取全文（加长度上限，例如单文件 40k chars，总计 120k chars；超限截断并在上下文里标注“已截断”）
3. 拼接上下文时显式分区：
   - `课程产出（全文，不经检索）：...`
   - `参考资料检索片段（RAG）：...`

落点（必须都改）：
- `POST /tools/assistant_chat`：system prompt 增加“课程产出全文”段落，并确保 `/search` 只用 `rag_ids`
- `POST /tools/lesson_plan`：lesson system prompt 增加“课程产出全文”；`/search` 只用 `rag_ids`
- `POST /tools/outline`（兼容别名：`/tools/aippt_outline_unified`）：prompt 里追加“课程产出全文”；RAG 只用 `rag_ids`
- `POST /tools/ppt`（兼容别名：`/tools/aippt`）：
  - 无论 `generateFromUploadedFile` 是否开启，都接收 `request.kb_file_ids` 用于解析 `full_ids`
  - 仅当 `generateFromUploadedFile=True` 时，把 `rag_ids` 传给内容 agent 的 metadata（保持“参考资料=检索”语义）
  - 把“课程产出全文”作为额外 markdown 章节追加到传入 content agent 的 `markdown_content`（确保在首个 `#` 之后，避免被正则截掉）

### 3.2 Artifacts 文件存储（DOCX/PPTX 后端持久化）
新增环境变量与路径：
- `TEACHDO_ARTIFACT_DIR`（默认 `var/artifacts`，用 main_api 现有 `_find_repo_root` 做 root-relative 解析）

新增 API（路径建议，保持与 KB 风格一致）：
- `GET /artifacts/{user_id}/{material_id}`：列出该课程的 artifacts（返回元数据数组，按时间倒序）
- `POST /artifacts/{user_id}/{material_id}`：multipart 上传（fields：`kind`=`pptx/docx`，`file`）
- `GET /artifacts/{user_id}/{material_id}/{artifact_id}`：下载文件（`Content-Disposition` 带原文件名）
- `DELETE /artifacts/{user_id}/{material_id}/{artifact_id}`：删除文件

保存规则（决策锁定）：
- 每次导出都生成一个新的 `artifact_id=uuid4().hex`
- 文件名保留原名（会做安全净化）
- 后端维护 `index.json`（或等价）记录元数据与真实落盘文件名

DOCX 自动入库：
- 扩展 `LessonExportDocxRequest`：新增 `materialId?: str`、`userId?: str`、`persist?: bool`
- 前端导出时传 `persist=true`、`materialId=<TeachingMaterial.id>`、`userId=default_user`
- 后端在生成 bytes 后保存到 artifacts，再返回二进制；并在响应头里附加 `X-TeachDo-Artifact-Id: <artifact_id>`

---

## 4. 前端改动（`frontend`）

### 4.1 三栏布局（工作台容器）
- `frontend/src/views/TeachingMaterialWorkspaceView.vue`：
  - 结构改为：`<WorkspaceLeftPanel /> <main /> <WorkspaceOutputPanel />`
  - 适配响应式：移动端两侧栏默认收起，以 overlay 形式展开
- `frontend/src/stores/workspaceUiStore.ts`：
  - 在现有（目前叫 rightPanel）基础上新增 `outputPanelCollapsed` 状态与切换 action

### 4.2 左侧“参考资料库（RAG）”——只展示导入文件
- 复用现有 `KnowledgeBaseView`，新增参数 `sourceFilter="uploaded"`（或等价），仅展示 `folderId=0`
- 选择逻辑仅统计/清理“参考资料ID（非 `gen:`/`full:`）”，避免把右侧全文注入文件计入“已选参考资料”
- 文案口径统一：
  - 标题：`参考资料`
  - 副标题：`用于检索（RAG），只会把相关片段放入上下文`

### 4.3 右侧“课程产出文件库（全文上下文 + 文件存放）”
新增组件（建议）：
- `frontend/src/components/workspace/WorkspaceOutputPanel.vue`
- `frontend/src/components/workspace/OutputFilesView.vue`

功能拆分：
1. 文本产物（MD，来自 KB 的 gen: 文件）
   - 数据源：`store.kbFiles` 里 `folderId=1` 且（`sourceMaterialId===currentMaterial.id` 或 `file_id` 前缀匹配 `gen:<user>:<materialId>:`）
   - 操作：
     - 勾选：把该 `gen:` file_id 加入 `TeachingMaterial.kbFileIds`（作为“全文注入”来源）
     - 下载：沿用 `kbExportFile`
     - 清空：只清掉 `kbFileIds` 里 `gen:` 子集
   - 文案口径：
     - 标题：`课程产出`
     - 副标题：`勾选后将全文加入上下文（不检索）`
2. 全文上传文件（来自 KB 的 full: 文件）
   - 数据源：`store.kbFiles` 里 `folderId=2` 且 `file_id` 前缀匹配 `full:<user>:<materialId>:`  
     （用于“把整份参考资料全文注入上下文”，不走检索）
   - 操作：
     - 上传：复用 `kbUpload`，传 `folderId=2` + 自定义 `file_id=full:...`
     - 勾选：把该 `full:` file_id 加入 `TeachingMaterial.kbFileIds`（作为“全文注入”来源）
     - 下载/删除：沿用 `kbExportFile` / `kbDeleteFile`
3. 导出文件（DOCX/PPTX，来自后端 artifacts）
   - 新增 `artifactService`（`frontend/src/services/ai/artifactService.ts`）对接后端：
     - `listArtifacts(userId, materialId)`
     - `uploadArtifact(userId, materialId, kind, file)`
     - `downloadArtifact(userId, materialId, artifactId)`（fetch + blob 下载）
     - `deleteArtifact(...)`
   - 右侧展示两类：
     - 教案.docx：若已有 artifacts 就显示列表项；若没有，显示“去教案页导出并保存”（跳转到 lesson tab）
     - PPT.pptx：若已有 artifacts 就显示列表项；若没有，显示“去编辑器导出并保存”（跳转 editor 路由）

### 4.4 PPTX 导出后自动上传入库（后端持久存储）
- 修改 `frontend/src/editor-runtime/hooks/useExport.ts`：
  - `exportPPTX` 不再只 `pptx.writeFile`：
    1. `const blob = await pptx.write({ outputType: 'blob' })`
    2. 用 blob 手动触发下载（保持现有用户体验）
    3. 若 `useMainStore()` 中存在 `teachdoMaterialId + teachdoUserId`，则 POST 到 `/artifacts/{user}/{material}` 上传（kind=`pptx`）
- 修改 `frontend/src/editor-runtime/store/main.ts`：
  - 增加 `teachdoMaterialId`、`teachdoUserId`（以及对应 set action）
- 修改 `frontend/src/views/PPTEditorView.vue`：
  - 初始化编辑器时设置上述字段（materialId 来自路由；userId 用 `KB_USER_ID`）

### 4.5 DOCX 导出时自动后端保存
- 修改 `frontend/src/services/ai/lessonService.ts::exportLessonDocx`：
  - 请求体增加 `persist:true`、`materialId`、`userId`
  - 读响应头 `X-TeachDo-Artifact-Id`，导出成功 toast 增加“已保存到课程产出”

### 4.6 教案 MD 产物入 KB（保证右侧可选全文）
- `frontend/src/components/workspace/LessonPlanView.vue`：
  - `generateLesson` 成功后将教案转换为 markdown（按当前 templateId 生成对应结构）
  - 调 `vectorizeTextToKb` 写入 `gen:<user>:<materialId>:lesson`
  - 这样右侧“文本产物”里会出现可勾选的教案 MD（供全文注入）

---

## 5. 公共接口/类型变更（需要同步前后端）
- 后端新增：`/artifacts/{user_id}/{material_id}`（GET/POST）与 `/artifacts/{user_id}/{material_id}/{artifact_id}`（GET/DELETE）
- 后端扩展：`POST /lesson/export/docx` request body 增加 `userId/materialId/persist`（可选，默认不存）
- 前端新增：`artifactService`；并在 PPTX/DOCX 导出链路调用

---

## 6. 测试用例与验收

### 6.1 后端（pytest）
新增/更新：
- `backend/test_assistant_chat.py`
  - stub 增加 `GET /files/{user_id}/{file_id}/content`
  - 断言：`/search` 的 `fileIds` 只包含 upload；system prompt 包含“课程产出（全文）”与 stub content
- `backend/test_lesson_plan.py`、`backend/test_outline_kb_rag.py`
  - 同上：gen id 不进入 search；gen content 进入 prompt
- `backend/test_kb_bff.py`
  - 如不改 vectorize 返回值则无需动；若改动要同步断言
- 新增 `backend/test_artifacts_api.py`
  - 使用 `tmp_path` + `monkeypatch.setenv("TEACHDO_ARTIFACT_DIR", ...)`
  - 覆盖 upload/list/download/delete 全流程；校验 header 与落盘

### 6.2 前端（本地验收脚本）
启动：
```bash
cp env_template.txt .env && python3 start.py
```

验收步骤（必须全部通过）：
1. 三栏显示：左“参考资料”、右“课程产出”
2. 左侧上传/选择参考文件 → 生成大纲/助教提问 → 后端只做 RAG 片段注入
3. 生成大纲/PPT/教案后，右侧出现对应 MD 产物；勾选后再生成/提问 → 明显能看到模型基于全文产物作答/生成
4. 教案页导出 DOCX：下载成功 + 右侧 artifacts 列表出现 docx，可再次下载
5. PPT 编辑器导出 PPTX：下载成功 + 自动上传成功 + 右侧 artifacts 列表出现 pptx，可再次下载

---

## 7. 分批提交（git）
1. `feat(kb): gen产物全文注入，RAG仅针对upload`（后端 + 单测更新）
2. `feat(artifacts): 后端持久化DOCX/PPTX与API`（后端 + 单测）
3. `refactor(ui): 工作台三栏布局与左右侧栏口径`（前端布局/i18n）
4. `feat(outputs): 右侧产出库(文本+artifacts) + PPTX上传 + DOCX持久保存 + 教案MD入库`（前端功能闭环）

---

## 8. 假设与默认
- `user_id` 继续使用前端现有 `KB_USER_ID=default_user`
- personaldb 已启用（用于参考资料 RAG 与 gen: 文本产物的全文读取）；若 personaldb 不可用：参考 RAG 与全文注入都会降级为“无知识库增强”
- artifacts 落盘目录默认 `var/artifacts`，不纳入 git（仓库惯例目录）
