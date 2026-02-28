# TeachDo 工程机制沉淀（用于毕设答辩）

> 文档版本：1.0  
> 最后更新：2026-02-28  
> 说明：本文档沉淀 TeachDo 在「大纲 → PPT → 编辑器 → 导出/入库」主链路上，为了保证一致性、可靠性与可维护性而实现的关键工程机制。内容偏“为什么这样设计 + 怎么落地 + 关键代码入口”，便于答辩讲解与复盘。

---

## 1. 关键对象与边界（先把“谁负责什么”讲清楚）

TeachDo 里常见的“同步/删除困惑”，本质来自三类对象的生命周期不同：

1. **内容页产出（Source of Truth）**：`TeachingMaterial`（前端本地持久化）
   - 代表“用户当前看到/编辑”的大纲、教案、PPT（presentation/editorDocument）。
   - 目标：可反复生成、可编辑、刷新不丢、体验流畅。

2. **知识库索引（Derived Index）**：`personaldb`（向量库 + 元数据）
   - 代表“为了检索/引用而建立的索引”，不是内容页本身。
   - 目标：RAG 检索、全文注入、来源可追溯、可清理。

3. **导出产物（Binary Artifacts）**：`artifacts`（PPTX/DOCX 等文件落盘）
   - 代表“可下载的二进制文件版本”（例如导出的 PPTX）。
   - 目标：可多次导出、可保留历史、可再次下载。

> 答辩表达建议：先强调“内容页/知识库/导出文件”是三个边界清晰的子系统；随后再讲一致性策略与防呆机制，老师会更容易理解你在解决什么问题。

---

## 2. 机制目录（可按 ID 逐条讲）

- **M01 幂等入库（产物覆盖写）**：固定 `fileId` + personaldb 先删后写，保证“重复生成=更新同一条”。
- **M02 产物锁定（防止不同步）**：`gen:*` 产物与内容页绑定，禁止在 KB 里单独移除。
- **M03 前缀协议（gen/full/upload）**：用 `fileId` 前缀区分“全文注入 vs RAG 检索”。
- **M04 去重注入（避免上下文重复）**：生成 PPT 时避免重复注入 `outline` 全文。
- **M05 降级与不阻断**：KB 不可用/入库失败不阻断主流程（生成/编辑优先）。
- **M06 引用清理（避免悬挂引用）**：删 KB 文件后清理所有 `kbFileIds` 引用，避免“勾选残留”。
- **M07 流式可中断**：SSE + AbortController，用户可随时取消生成，避免卡死。
- **M08 持久化分层（性能）**：大对象进 IndexedDB，小对象进 localStorage；助教消息不持久化。
- **M09 导出产物持久化（Artifacts）**：文件落盘 + 索引文件；前端监听事件刷新。
- **M10 安全基线**：文件名净化、路径段净化、禁用代理环境变量、超时控制等。
- **M11 可追溯元数据（来源/时间）**：`created_at/source_type/source_material_*` 全链路透传与展示。

---

## 3. 机制详解（每条都能“讲得像论文”）

### M01 幂等入库（产物覆盖写）

**问题**：产物可以反复生成，如果每次都新增一条，会导致 KB 里出现多份历史版本，用户难以分辨“当前版本”，也会污染检索。

**设计**：对“课程产出”使用固定的 `fileId`（例如 `gen:default_user:<materialId>:outline`），让“重复生成”变成“覆盖更新”。

**落地要点**
- 前端：产物入库固定 `fileId`（按 materialId + kind 组合）。
- personaldb：插入向量前先删除同 `fileId` 的旧向量，再插入新向量（delete-then-insert）。

**关键代码入口**
- `frontend/src/components/workspace/OutlineView.vue`（大纲入库 `gen:*:outline`）
- `frontend/src/components/workspace/LessonPlanView.vue`（教案入库 `gen:*:lesson`）
- `frontend/src/components/workspace/ppt/usePptGeneration.ts`（PPT 入库 `gen:*:slides`）
- `frontend/src/views/PPTEditorView.vue`（编辑器最终版入库 `gen:*:slides_final`）
- `backend/personaldb/embedding_utils.py`：`insert_file_vectors()` 内部先调用 `delete_file_vectors()`

**权衡**
- ✅ 优点：KB 永远保持“当前版本”，检索稳定，用户更易理解。
- ❌ 缺点：默认不保留历史；若要历史，需要走 artifacts（PPTX/DOCX）或新增版本号策略。

---

### M02 产物锁定（防止“内容页还在 / KB 被删”的不同步）

**问题**：内容页产出是源数据（可编辑/可展示）；KB 中的 `gen:*` 是索引镜像。如果允许用户在 KB 里删除 `gen:*`，会出现：
- 内容页仍然显示产出（因为源数据还在）
- 右侧“产出入库/全文注入”失效（因为索引被删）
- 用户感知为“不同步/不一致”

**设计**：当 `gen:*` 对应的 `TeachingMaterial` 仍存在时，KB 的该条目视为“与内容页绑定”，**禁止单独移除**（UI 显示锁）。

**关键代码入口**
- `frontend/src/components/workspace/OutputFilesView.vue`：对 `gen:*` 显示锁并拦截删除（toast 提示）
- `frontend/src/components/workspace/KnowledgeBaseView.vue`：同样对 `gen:*` 拦截删除（toast 提示）
- `frontend/src/i18n/index.ts`：新增锁定提示文案

**权衡**
- ✅ 优点：把“源数据 vs 索引镜像”的边界变成可感知的 UI 规则，减少误操作与困惑。
- ❌ 缺点：用户少了“单独清理索引”的自由；但仍可通过“删除教学资料（可选清理 KB 产物）”完成整体清理。

---

### M03 前缀协议（gen/full/upload）统一“全文注入 vs RAG 检索”

**问题**：知识库既要支持“检索片段（RAG）”，也要支持“全文注入（把整篇放进上下文）”。如果混在一起，会导致：
- prompt 变长、重复、成本高
- 上下文语义混乱（全文与片段重复）

**设计**：用 `fileId` 前缀做协议，前后端一致：
- `upload:*`：上传素材 → **只走检索（RAG）**
- `gen:*`：课程产出 → **全文注入**
- `full:*`：全文上传 → **全文注入**

**关键代码入口**
- `frontend/src/utils/kbFileId.ts`：`isFullTextKbFileId()`（`gen:`/`full:` 视为全文）
- `backend/main_api/main.py`：`_split_kb_file_ids()`（按前缀拆分 full_ids 与 rag_ids）

---

### M04 去重注入（避免上下文重复）

**问题**：生成 PPT 时，大纲内容已经通过 `outlineContent` 作为主输入传给后端；如果用户又勾选了 KB 里的 `gen:*:outline`，会导致同一份内容被“重复注入”。

**设计**：前端在提交生成请求前，从 `kbFileIds` 中剔除本教学资料的 `gen:*:outline`，保证上下文不重复。

**关键代码入口**
- `frontend/src/components/workspace/ppt/usePptGeneration.ts`：`kbFileIdsForRequest` 过滤 `...:outline`

---

### M05 降级与不阻断（主链路优先）

**问题**：KB 相关链路涉及解析/向量化/检索/网络调用，失败概率比“本地内容展示”更高；如果任何一步失败都阻断生成，会严重影响核心体验。

**设计**
- 生成/编辑主链路优先：KB 写入失败仅告警（console.warn/toast），不阻断内容页更新。
- 后端调用 personaldb 前做 readiness 判断，不可用则跳过 KB 增强。

**关键代码入口（示例）**
- 前端多个 `vectorizeTextToKb(...).catch(() => console.warn('…已忽略'))`
- `backend/main_api/main.py`：`_is_personaldb_ready()` + 在构建 KB 上下文时跳过不可用情况

---

### M06 引用清理（避免悬挂引用/勾选残留）

**问题**：`TeachingMaterial.kbFileIds` 保存了“当前教学资料勾选的引用文件”。如果某 KB 文件被删除，但引用未清理，会出现：
- UI 勾选数不对
- 生成/助教请求携带不存在的 fileId，导致后端额外的 404/跳过逻辑

**设计**：删除 KB 文件后，遍历所有教学资料，移除该 fileId 的引用。

**关键代码入口**
- `frontend/src/components/workspace/KnowledgeBaseView.vue`：`purgeKbFileReferences()`
- `frontend/src/components/workspace/OutputFilesView.vue`：`purgeKbFileReferences()`

---

### M07 流式可中断（SSE + AbortController）

**问题**：大模型生成可能耗时长；若不能取消，用户会觉得“卡死/不可控”，也会浪费算力。

**设计**：前端用 `AbortController` 控制 SSE 请求，取消后进入可恢复状态（清理草稿/回滚等）。

**关键代码入口（示例）**
- `frontend/src/components/workspace/OutlineView.vue`：取消生成、COMPARE/回滚逻辑
- `frontend/src/components/workspace/LessonPlanView.vue`：取消生成、失败回滚到 prevPlan
- `frontend/src/components/workspace/ppt/usePptGeneration.ts`：取消生成与“部分生成草稿预览”处理

---

### M08 持久化分层（性能：IndexedDB vs localStorage）

**问题**：大纲/教案/PPT 文档可能很大。如果直接把大对象频繁写入 localStorage，会导致卡顿甚至写入失败。

**设计**
- 轻量状态（materials 基本信息）写 localStorage。
- 大对象（outline/lesson/presentation/editorDocument/kbFiles）写 IndexedDB，并在启动时异步回填。
- 助教 messages 更新频繁且不做持久化，避免高频写导致卡顿。

**关键代码入口**
- `frontend/src/stores/appStore.ts`：`saveMaterialLarge/loadMaterialLarge/saveAppLarge/loadAppLarge` 与 `$subscribe` 跳过 assistantMessages

---

### M09 导出产物持久化（Artifacts 子系统）

**问题**：用户需要“可下载的 PPTX/DOCX”，而且希望多次导出后仍能回看/再次下载。

**设计**
- 后端提供 artifacts API：上传/列表/下载/删除。
- 落盘文件名与目录段做净化（兼容 Windows/防路径穿越）。
- 前端在右侧“课程产出”里展示并下载 artifacts，并监听事件刷新列表。

**关键代码入口**
- `backend/main_api/main.py`：`/artifacts/*` + `_artifact_safe_filename/_artifact_safe_segment`
- `frontend/src/components/workspace/OutputFilesView.vue`：artifacts 列表与下载

---

### M10 安全基线（文件名/路径/网络环境）

**问题**：涉及文件与网络时，常见风险包括 Header 注入、路径穿越、代理环境变量干扰请求等。

**设计**
- 文件名净化：避免 `../`、`\r\n`、Windows 非法字符等。
- 下游请求统一 `trust_env=False`（不读系统代理环境），并设置合理超时。

**关键代码入口（示例）**
- `backend/main_api/main.py`：`_kb_safe_filename/_artifact_safe_filename`；多处 `httpx.AsyncClient(trust_env=False, timeout=...)`
- `backend/personaldb/main.py`：下载文件 `requests.get(..., proxies=None, timeout=60)`

---

### M11 可追溯元数据（来源/时间）

**问题**：知识库里既有“上传素材”，也有“课程产出”。如果不能展示来源与时间，用户会困惑“这个文件从哪来的/什么时候生成的”。

**设计**：在 KB 写入时统一写入 `created_at/source_type/source_material_id/source_material_title`，列表接口透出，前端映射展示。

**关键代码入口**
- `backend/personaldb/embedding_utils.py`：写入与兜底推断 `source_*` / `created_at`
- `backend/main_api/main.py`：`GET /kb/files/{user_id}` 归一化返回字段
- `frontend/src/services/ai/kbService.ts`：字段定义
- `frontend/src/components/workspace/KnowledgeBaseView.vue`、`frontend/src/components/workspace/OutputFilesView.vue`：展示与映射

---

## 4. 验证清单（答辩前自测建议）

1. 生成大纲/教案/PPT → 右侧出现对应 `gen:*` 条目 → 再次生成 → KB 同 `fileId` 内容更新（不新增重复条目）。
2. 在 KB/右侧产出中尝试“移除 gen:* 条目” → UI 显示锁 → toast 提示“请删除教学资料清理”。
3. 删除一个 `upload:*` 文件 → 所有教学资料里引用该 fileId 的勾选被清理（勾选数变化正确）。
4. 生成过程中点击取消 → 页面状态可恢复（不残留半成品/不需要刷新）。
5. 导出 artifacts（PPTX/DOCX）→ 右侧 artifacts 可再次下载 → 文件名无非法字符且可在 Windows 下保存。

