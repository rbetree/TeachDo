# TeachDo 结构重构计划：去掉“课程”，统一为“教学资料” + 全局知识库 + 生成时按文件选择

## 摘要（你要的三个改动如何落地）
1. **信息架构**：把原“课程-单元”两层，改成单层 **“教学资料”**（原单元改名），**彻底移除课程**。
2. **知识库**：从“按课程隔离”改为**全局不隔离**；在**创建教学资料**与**生成 PPT**等操作时，用户**按文件多选**决定引用哪些 KB 文件（你已选“选文件(可多选)”）。
3. **创建交互**：侧边栏“新增单元”的内嵌表单改为**弹窗（Modal/Dialog）填写新教学资料**（你已指定）。

> 关键默认值（已按你给的选择定死）：  
> - **不迁移旧数据**：开发阶段测试数据不做迁移；检测到旧课程/单元/旧 KB 时，直接重置本地存储后启用新结构。  
> - **全局 KB 用户 ID**：前端统一使用 `default_user` 作为知识库 userId（与后端默认一致）。  
> - **产物入库**：大纲/PPT 等生成内容统一写入全局 KB（folderId=1，“产物库”）。

---

## 执行看板（优先级 / 状态）

> 说明：此处用于跟踪实现进度，后续每完成一项就把状态改为 DONE。
>
> - 优先级：`P0` 必须（主链路可用） / `P1` 重要（体验与一致性） / `P2` 最后（增强能力）
> - 状态：`TODO` 待做 / `DOING` 进行中 / `DONE` 已完成 / `BLOCKED` 阻塞

### P0（先做：结构重构 + PPT 生成链路）
- [DONE] 前端：移除 course/unit 信息架构，落地单层 `TeachingMaterial`（路由/页面/Store/持久化）
- [DONE] 前端：全局 KB（`default_user`）+ KB 文件多选引用（`KbFilePickerDialog`）+ PPT 生成透传 `kb_file_ids`
- [DONE] 后端：`/tools/aippt` 支持 `kb_file_ids` 透传 + `slide_agent` KnowledgeBaseSearch 文件级过滤
- [DONE] personaldb：`POST /search` 支持 `fileIds` 过滤（服务端向量查询 where 过滤）+ 单测

### P1（再做：大纲 KB 增强 + KB 可观测性 + 删除清理）
- [DONE] 大纲生成：`/tools/aippt_outline_unified` 支持 `kb_file_ids`，并基于 personaldb 检索结果增强 prompt + 单测
- [DONE] KB 文件元数据：补全 `created_at/source_type/source_material_*` 写入与 `GET /files/{user_id}` 返回透出；前端 KB 列表展示“时间+来源”
- [DONE] 删除教学资料：确认弹窗 + 可选“同时删除该教学资料相关 KB 产物文件（folderId=1 + gen 前缀）”

### P2（最后：助教真实可对话能力）
- [TODO] 助教：全局单会话真实对话（可引用当前教学资料已选 `kbFileIds`），提供“清除上下文”，不做历史持久化

## 公共接口/类型变更（对前后端的“契约”）
### 前端类型（`teachdo-frontend/types.ts`）
- 删除/弃用：`CourseGroup`、`CourseUnit`
- 新增：`TeachingMaterial`（UI 文案名：教学资料）
  - 字段（你选的合并方案：标题+学科+简介+目标）：
    - `id: string`
    - `title: string`（原 unit.title）
    - `subject: string`（原 course.subject）
    - `description: string`（原 course.description）
    - `objectives: string`（原 unit.objectives）
    - `createdAt: Date`
    - `kbFileIds: string[]`（**引用的知识库文件 IDs**，创建时选择，生成时可改）
    - 产物：`outlineContent? / lessonPlan? / presentation? / selectedTemplateId? / editorDocument?`
  - 说明：
    - “助教”会话为**全局单会话**（不属于 TeachingMaterial），不做会话/多会话管理；提供“清除上下文”按钮清空上下文与显示消息；**不做历史持久化**。

### 知识库文件（`KBFile`）补充字段（用于列表展示与溯源）
- 目标：知识库列表中每个文件都能展示“上传时间/生成时间”与“来源（上传 / 某个教学资料）”
- 建议字段（后端返回 → 前端映射）：
  - `created_at: number`（ms 时间戳；前端映射为 `uploadedAt: Date`）
  - `source_type: "upload" | "material"`
  - `source_material_id?: string`
  - `source_material_title?: string`（可选，用于展示；若缺省则前端可用 `source_material_id` 去本地 materials 查 title）

### PPT 生成请求（`/tools/aippt`）
- 现有字段保持（兼容旧调用）：`sessionId`、`generateFromUploadedFile`、`kb_folder_ids` 等
- **新增字段**（本需求核心）：
  - `kb_file_ids: string[] | null`：当启用 KB 检索时，限定 RAG 只能从这些 file_id 的向量中检索

### 大纲生成请求（`/tools/aippt_outline_unified`）
- 新增字段：
  - `kb_file_ids: string[] | null`：生成大纲时按文件过滤检索上下文
- 约束：
  - 前端：当启用“使用知识库”时必须已选 ≥1 个 ready 文件，否则不允许提交
  - 后端：保持兜底保护（收到空数组时自动禁用 KB 并返回提示事件），避免异常调用导致体验差

### personaldb 搜索（`POST /search`）
- 现有字段：`userId, query, keyword, topk`
- **新增字段**：
  - `fileIds?: string[]`：服务端在向量查询时按 `file_id` 元数据过滤（避免“先 topk 再过滤”导致命中为空）

---

## 后端修改计划（FastAPI + slide_agent + personaldb）
### 1) `backend/main_api/main.py`（BFF）
- 扩展 `AipptContentRequest`：
  - 增加 `kb_file_ids: list[str] | None = None`
- 扩展 `stream_content_response(...)` 参数并透传到 content agent metadata：
  - `metadata["kb_file_ids"] = kb_file_ids`（仅当 KB 启用且非空）
- 增强保护逻辑：
  - 当 `generateFromUploadedFile=True` 但 `kb_file_ids` 为空时：后端可选择直接降级为 `generateFromUploadedFile=False`（同时 SSE 返回提示事件），避免前端误开 KB 却无文件
- 单测更新（`backend/test_kb_bff.py`）：
  - 新增用例：确认 `kb_file_ids` 在 personaldb ready 时会传入 `stream_content_response`；在 personaldb 未配置/未 ready 时被置空/禁用（与现有 kb_folder_ids 行为一致）
- 扩展 `/tools/aippt_outline_unified`：
  - 接收 `kb_file_ids`（FormData 或 JSON 字段）
  - 若 `kb_file_ids` 非空且 personaldb 可用：调用 personaldb `/search`（携带 `fileIds`）拉取少量相关片段，拼接到大纲 prompt 前（或以 “参考资料” 区块附加），再调用 outline agent
  - 单测：至少覆盖“传入 kb_file_ids 会触发 personaldb 搜索并注入 prompt”与“空选择禁用 KB”

### 2) `backend/slide_agent/.../ppt_writer/tools.py`（KnowledgeBaseSearch）
- 读取 metadata：
  - `kb_file_ids`：优先使用（文件级过滤）
  - `kb_folder_ids`：保留兼容（文件未选择时仍可用）
- 调用 personaldb `/search` 时附带：
  - `fileIds: kb_file_ids`（camelCase，与 personaldb 当前 JSON 风格一致）
- 兜底过滤（防止 personaldb 未升级时）：
  - 若响应中 `metadatas` 含 `file_id`，在工具侧再做一次基于 `kb_file_ids` 的二次过滤

### 3) `backend/personaldb/main.py` + `backend/personaldb/embedding_utils.py`
- `SearchQuery` 增加 `fileIds: Optional[List[str]] = None`
- `embedding_utils.ChromaDB.query2collection(...)` 增加 `where: dict | None = None`
- `/search` 逻辑：
  - 如果 `fileIds` 非空：构造 `where={"file_id": {"$in": fileIds}}` 并传入 Chroma `col.query(where=...)`
  - 若 Chroma 不支持 `$in`（实现时做一次快速验证）：退化为按 fileId 循环 query + merge（按距离排序取 topk）
- 单测（新增轻量单元测试，避免集成测试依赖外部服务）：
  - 用 `TestClient` + monkeypatch `ChromaDB.query2collection`，断言 `where` 在 `fileIds` 传入时必然携带
- KB 文件元数据补全（时间/来源）：
  - 写入（upload/vectorize/text）时在 Chroma metadata 增加：
    - `created_at`（ms 时间戳）
    - `source_type`（`upload` / `material`）
    - `source_material_id/source_material_title`（当为产物入库时写入；upload 则为空）
  - `GET /files/{user_id}` 返回中透出上述字段（供前端展示）

---

## 前端修改计划（Vue3 + Pinia + Router + Tailwind）
### 1) 路由重构（`teachdo-frontend/src/router/index.ts`）
- 移除所有 `course/:courseId/...`、`unit/:unitId/...` 路由
- 新增单层教学资料路由：
  - `GET /`：`workspace` → 教学资料列表页
  - `GET /material/:materialId/:tab`：教学资料工作台（`tab ∈ outline|lesson|ppt`，默认 outline）
  - `GET /material/:materialId/ppt/editor`：PPT 编辑器
- `beforeEach` 守卫改为：
  - 校验 `materialId` 存在于 `store.materials`
  - 自动选择 `currentMaterialId`
  - `tab` 非法 → 重定向到 outline

### 2) Store 与持久化（`teachdo-frontend/src/stores/appStore.ts` + `src/utils/appStoreIdb.ts`）
- `AppStoreState` 改为：
  - `materials: TeachingMaterial[]`
  - `currentMaterialId: string | null`
  - `kbFiles: KBFile[]`（全局 KB 文件列表）
  - `assistantMessages: ChatMessage[]`（全局单会话，仅内存；**不做持久化**）
  - `theme, language`
- 存储边界（评审结论）：
  - `TeachingMaterial` 属于**结构化业务数据**：开发阶段仍由前端 store（localStorage/IndexedDB）作为 source of truth
  - 知识库（personaldb/Chroma）属于**非结构化文档与检索**：只存“上传资料/生成产物”的文件内容与向量，不用来存 TeachingMaterial 本体
- Actions：
  - `upsertMaterial(...) / selectMaterial(...) / updateMaterial(...)`
  - `setKbFiles(...)`（由 KnowledgeBaseView/同步逻辑更新）
- 持久化策略（开发阶段，数据无所谓，按“无需迁移”处理）：
  - localStorage：**新版本号**（例如 v3），检测到旧版本则**不迁移**，直接初始化为空（可保留旧的 theme/language）
  - IndexedDB：启用**新 DB_NAME**（避免旧 unitLarge/courseLarge 干扰），表设计：
    - `kbLarge`：存 `kbFiles`
    - `materialLarge`：按 `materialId` 存 outline/ppt/editorDocument 等大对象

### 3) 页面与组件改造
#### 3.1 教学资料列表页（替换 `CourseSelectionView.vue`）
- 改为 `TeachingMaterialSelectionView.vue`（或保留文件名但重写内容）：
  - 卡片展示：标题、学科、简介、目标摘要、产物状态（大纲/幻灯片是否已生成）
  - “创建教学资料”按钮 → 打开创建弹窗
  - 进入工作台：路由到 `/material/:materialId/outline`

#### 3.2 教学资料工作台（替换 `CourseWorkspaceView.vue`）
- 改为单实体模式：
  - 当前教学资料由 `store.currentMaterial` 提供
  - 左侧栏：显示“教学资料列表”（可快速切换），不再有课程 header
  - 中间区域：Outline/Lesson/PPT 逻辑复用，但 props 全部换成 `currentMaterial`
  - 右侧栏：模块保留（KB/助教），KB 变为全局

#### 3.4 右侧“助教”面板（`AssistantView.vue`）
- 改为“全局单会话 + 不持久化”：
  - 不再挂在 TeachingMaterial 上，也不写 localStorage/IndexedDB
  - 仅维护 `assistantMessages`（数组）作为当前会话显示与上下文
  - 提供按钮“清除上下文”：清空上下文与显示消息（回到 greeting）
- KB 引用：
  - 默认使用 `currentMaterial.kbFileIds` 作为检索过滤（对话时可引用这些 KB 文件）

#### 3.3 左侧栏“新增”改弹窗（替换 `UnitSidebar.vue`）
- 把侧边栏内嵌表单删除
- 点击 `+` → 打开 `TeachingMaterialCreateDialog.vue`
- 弹窗提交后：
  - `store.upsertMaterial(...)`
  - 路由跳转到新 material 的 outline tab
  - **不再“创建即生成大纲”**：进入 outline 后由用户手动点击“生成大纲”按钮触发生成
  - 提示文案：可先去“知识库”上传资料并勾选引用文件，再开始生成（大纲/课件等）

### 4) 全局知识库与“按文件选择引用”
#### 4.1 KnowledgeBaseView 全局化（`components/workspace/KnowledgeBaseView.vue`）
- 去掉 `currentCourse` 依赖：
  - `userId` 固定为 `default_user`
  - 文件列表来自 `store.kbFiles`
- 上传/删除/导出逻辑改为更新全局 kbFiles
- UI 提示：这是“全局知识库”，生成时会选择引用文件
- 列表展示补全：
  - 展示 `uploadedAt`（来自后端 `created_at`）
  - 展示来源：`upload` 显示“上传”；`material` 显示“教学资料：{title}”

#### 4.2 复用的 KB 文件选择器（新增组件）
- 新增 `KbFilePickerDialog.vue`（参考 `PptAdvancedDialog` 的 Teleport + 可访问性实现）：
  - 输入：`files`, `selectedIds`
  - 功能：搜索、按 folderId(0上传/1产物)筛选（**两类都可选**，默认显示全部）、仅显示 ready、全选/清空、确认返回
  - 交互标准：Esc 关闭、焦点恢复、按钮/列表项 ≥44px、明显 focus ring

#### 4.3 创建教学资料时选择引用 KB（`TeachingMaterialCreateDialog.vue`）
- 表单字段：
  - 标题（必填）
  - 学科（必填）
  - 简介（可选）
  - 教学目标（必填）
  - 引用知识库文件（可选，多选：打开 `KbFilePickerDialog`；也可创建后再选）
- 结果写入：`material.kbFileIds = selectedKbFileIds`

#### 4.4 PPT 生成时选择引用 KB（`PptAdvancedDialog.vue` + `usePptGeneration.ts` + `pptService.ts`）
- `PptAdvancedDialog` 增加区域：
  - “知识库文件”：显示已选数量与“选择文件”按钮（打开 `KbFilePickerDialog`）
- `usePptGeneration`：
  - 以 `currentMaterial.kbFileIds` 作为默认选择（对话框里可改）
  - 当用户点击“重新生成”并确认对话框时：把最终选择回写到 `currentMaterial.kbFileIds`（作为下次默认）
  - 若开启“使用知识库”但未选任何 ready 文件：自动关闭并 toast 提示
  - 调用 `streamAipptSlides` 时传 `kbFileIds`
- `pptService.streamAipptSlides`：
  - payload 增加 `kb_file_ids`
- `/tools/aippt` 的 `sessionId`：
  - 固定传 `default_user`（与全局 KB userId 一致）

### 5) 产物入库（Outline/PPT/Editor）
- 所有 `vectorizeTextToKb(...)` 的 `userId` 改为 `default_user`
- `folderId=1` 保持：代表“产物库”
- `fileId` 命名规范统一：
  - `gen:default_user:{materialId}:outline`
  - `gen:default_user:{materialId}:slides`
  - `gen:default_user:{materialId}:slides_final`
- 覆盖策略：同一 `materialId` 重复生成时复用同一 `fileId`，按“覆盖写入”（personaldb 会先删再插入向量）
- 删除教学资料时的可选清理：
  - 删除时弹确认弹窗，提供 checkbox：“同时删除该教学资料相关 KB 文件（产物库）”
  - 勾选时删除：仅删除**产物库**文件——`folderId=1` 且 `fileId` 前缀为 `gen:default_user:{materialId}:` 的文件；**不删除** `folderId=0` 的用户上传素材（避免误删被多个教学资料复用的文件）

### 6) 顶栏/文案/i18n
- `AppTopBar.vue`：面包屑从“课程名”改成“教学资料标题”
- `i18n/index.ts`：所有对用户可见的“课程/单元”文案替换为“教学资料”（保留 key 也可，但推荐逐步清理）

---

## 测试与验收
### 自动化
- 后端：`pytest backend -q`
  - 必须覆盖：`/tools/aippt` 透传 `kb_file_ids`、personaldb `/search` fileIds 过滤逻辑
- 前端：  
  - `cd teachdo-frontend && npm run typecheck`  
  - `cd teachdo-frontend && npm run lint`  
  - `cd teachdo-frontend && npm run build`

### 快速验收（P0 手工用例）
> 建议用隐身窗口或先清理站点数据，避免旧 localStorage/IndexedDB 影响。

1. **教学资料列表页（新结构）**
   - 打开应用首页，应看到“教学资料”列表（不再出现课程/单元两层）。
   - 点击任意条目进入工作台，地址应为 `/material/:materialId/...`。

2. **创建教学资料（不自动生成大纲）**
   - 点击“创建教学资料”，填写标题/学科/目标，创建后进入 outline 页。
   - 确认：不会自动触发大纲生成；outline 为空时展示“生成大纲”按钮。

3. **全局知识库（default_user）**
   - 右侧面板切到“知识库”，应显示“全局知识库”。
   - 上传文件后列表出现 `ready` 文件；刷新后仍可见；导出/删除可用。

4. **PPT：按文件选择引用（kb_file_ids）**
   - 先生成大纲，再进入 PPT 页。
   - 打开“高级设置”：勾选“引用知识库素材”后点击“选择文件”，多选 1~N 个 `ready` 文件确认。
   - 生成 PPT 成功后，在浏览器 DevTools → Network 中检查 `/api/tools/aippt` 请求体包含 `kb_file_ids`（且 `sessionId` 为 `default_user`）。

5. **重新生成：回写默认 kbFileIds**
   - 在 PPT 预览页点击“重新生成”，在高级设置中变更勾选文件后重新生成。
   - 再次打开高级设置，确认默认选中文件已更新（写回 material.kbFileIds）。

6. **产物入库（folderId=1）**
   - 生成大纲/PPT 后回到知识库刷新，应看到 `gen:default_user:{materialId}:outline/slides/...` 等产物文件（位于生成产物 folder）。

### 手工验收场景（必须全部通过）
1. **创建教学资料（弹窗）**：必填校验正确；创建后进入工作台 outline 页；手动点击“生成大纲”后生成成功。
2. **全局 KB**：上传文件后列表出现 ready；删除/导出正常。
   - 文件列表可展示上传时间与来源（上传/教学资料）
3. **PPT 生成选择 KB 文件**：打开高级设置→选择 1~N 个 KB 文件→生成成功；后端确实收到 `kb_file_ids`。
4. **未选文件时的兜底**：启用“使用知识库”但未选任何 ready 文件 → 自动提示并禁用（不发空选择到后端）。
5. **产物入库**：生成的大纲/PPT/最终编辑版会出现在 KB 的 folderId=1 分类中，并可被再次选择引用。
6. **助教面板**：全局单会话可对话；可引用当前教学资料已选 KB 文件；点击“清除上下文”会清空上下文与显示消息。
7. **删除教学资料**：弹窗可选“同时删除相关 KB 产物文件”；勾选后 KB 中对应产物文件消失。

---

## 明确假设/默认（写死，避免实现者再做决策）
- `KB_USER_ID = "default_user"`（前端常量；所有 KB 操作统一用它）
- KB 选择粒度：**按文件 ID 多选**（`kb_file_ids`）
- 不做旧数据迁移：旧课程/单元结构不自动转换；旧 KB 不自动搬运
- 创建不触发生成：创建教学资料后**不自动生成大纲**，由用户手动点击“生成大纲”
- KB 文件选择范围：`folderId=0`（上传素材）与 `folderId=1`（产物库）**两类都可选**
- 产物入库策略：覆盖写入（同一 `materialId` 复用同一 `fileId`）
- 助教：全局单会话、不做历史持久化；提供“清除上下文”按钮；默认可引用 `currentMaterial.kbFileIds`
- 大纲生成：启用知识库时按 `kb_file_ids` 做检索增强（无文件选择则前端不允许提交）
- 删除教学资料：可选删除该 material 的 KB 产物文件（`folderId=1` + `gen:default_user:{materialId}:*`）
- KB 文件元数据：需要展示上传时间（`created_at`）与来源（upload/material）
- folderId 语义沿用：
  - `0` = 上传素材
  - `1` = 生成产物（全局“产物库”）
