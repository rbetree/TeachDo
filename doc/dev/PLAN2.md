# 知识库文件“来源标签”改造（区分：上传素材 vs 生成产物）

## 目标与效果
- 在知识库文件列表/选择器中，为每个文件展示**清晰可读的标签**，区分：
  - `folderId=0` → **素材**（上传得到）
  - `folderId=1` → **产物**（AI 生成并入库的大纲/PPT 等）
- 标签必须“文字 + 颜色”双重表达（不只靠颜色），满足可访问性。

## 数据判定规则（无歧义）
1. 若 `KBFile.folderId === 1`：来源=generated（产物）
2. 若 `KBFile.folderId === 0` 或缺失/非法：来源=uploaded（素材）
3. （可选兜底）若未来出现新 folderId：来源=unknown（未知，灰色标签）

> 说明：当前后端 `main_api /kb/files/{user_id}` 已保证 `folder_id` 归一化并缺省为 0，因此前端主要走规则 1/2。

## 前端改动（TeachDo Frontend）
### 1) i18n 文案（`teachdo-frontend/src/i18n/index.ts`）
新增 key（中英都补齐）：
- `kb.source.uploaded`：`素材` / `Materials`
- `kb.source.generated`：`产物` / `Artifacts`
- `kb.source.unknown`：`未知` / `Unknown`
- `kb.source.uploaded_full`：`上传素材` / `Uploaded materials`
- `kb.source.generated_full`：`生成产物` / `Generated artifacts`

### 2) 来源判定与复用工具（新增 `teachdo-frontend/src/utils/kbSource.ts`）
- 导出：
  - `type KbSource = 'uploaded' | 'generated' | 'unknown'`
  - `getKbSource(folderId?: number): KbSource`
  - `getKbSourceUi(source: KbSource): { i18nKey, i18nTitleKey, icon, className }`
- 统一 Tailwind 风格（建议）：
  - 素材：`sky/indigo` 系（与“上传”语义一致）
  - 产物：`purple` 系（与“AI 产出”语义一致）
  - 未知：`slate` 系
- 标签样式统一为：`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border`

### 3) 知识库列表展示（`teachdo-frontend/src/components/workspace/KnowledgeBaseView.vue`）
- 在**两种布局**都加来源标签：
  - Page Variant（表格布局）：在“文件名”行右侧追加 pill 标签（不挤占 truncate，必要时放到下一行）
  - Panel Variant（侧栏卡片布局）：在文件标题区域或状态区域旁追加 pill 标签
- 标签可带 icon：
  - 素材：`upload-cloud`
  - 产物：`sparkles`
- A11y：
  - `:title="t(kb.source.*_full)"`（鼠标悬停）
  - 对读屏：`aria-label` 可直接复用 title 文案

### 4) 选择知识库文件时也展示（你后续“生成时按文件多选”的 FilePicker）
- 在 `KbFilePickerDialog.vue` 的每一行文件右侧展示同款来源标签
- （推荐）增加筛选 chip：`全部 / 素材 / 产物`，便于快速排除产物或只看产物

## 后端改动（可选/保障项）
- **原则上不需要改后端**：因为 `main_api` 已把 `folder_id` 归一化返回给前端。
- 若要更强保障，可在 `backend/main_api/main.py` 的 `kb_list_files` 中补充注释/断言：`folder_id` 缺失时默认 0，并确保永远返回 `folder_id:int`。

## 验收（DoD）
1. 上传一个 KB 文件后，列表中该文件显示标签 **“素材”**。
2. 生成大纲/PPT 入库后，列表中对应文件显示标签 **“产物”**。
3. 标签在浅色/深色主题都可读，且不影响主信息（文件名仍可正常 truncate）。
4. 若未来出现未知 folderId，显示 **“未知”** 灰色标签，不崩溃。

## 需要更新的计划文档
- `doc/dev/PLAN.md`：在知识库相关条目下新增一条“KB 文件来源标签（素材/产物）”的 DoD 与验收截图要求（可选）。
