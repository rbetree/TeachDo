# PersonalDB 服务文档

## 服务概述

[`personaldb`](../../backend/personaldb/main.py#L1) 是 AI2PPT 项目的知识库服务，负责文档上传、格式转换、向量化存储和智能检索。

**监听端口**: `9100`

**核心职责**: 文档上传、格式转换、向量化、语义检索

---

## 文档转换链

根据 [`AGENTS.md`](../../.kilocode/rules/AGENTS.md) 规则，实现了完整的转换流程：

```
PDF → MagicPDFConverter (MinerU) → Markdown
  ↓ (失败时回退)
MarkItDownConverter → Markdown
```

### MagicPDF 转换器（优先）

**文件**: [`magic_pdf_converter.py`](../../backend/personaldb/core/magic_pdf_converter.py#L1)

- 基于 mineru 库实现本地 PDF 转换
- 支持 OCR、布局分析、表格提取、公式识别
- GPU 加速（`USE_MINERU` 环境变量控制，默认 false）

### MarkItDown 转换器（回退）

**文件**: [`markitdown_converter.py`](../../backend/personaldb/core/markitdown_converter.py#L1)

- 支持 PDF, Word, Excel, PPT, 图片, 音频, HTML 等多种格式
- 作为 MagicPDF 失败时的回退方案

### 转换实现

[`_get_markdown_content()`](../../backend/personaldb/main.py#L66) 函数使用 `@cache_decorator` 装饰：

```python
@cache_decorator
def _get_markdown_content(file_path: str, file_name: str) -> str:
    USE_MINERU = os.environ.get("USE_MINERU", "false")
    if USE_MINERU.lower() == "true" and file_extension == '.pdf':
        converter = MagicPDFConverter()
        return True, converter.convert_pdf_file(file_path)
    else:
        converter = MarkItDownConverter(use_magic_pdf=False)
        return True, converter.convert_file(file_path)
```

---

## 缓存机制

### 1. 函数级缓存（`@cache_decorator`）

**位置**: [`embedding_utils.py:44`](../../backend/personaldb/embedding_utils.py#L44)

- 基于参数 MD5 哈希的自动缓存
- 默认保存为 pickle 到 `var/cache/personaldb/`（可通过 `AI2PPT_CACHE_DIR` 调整）
- 应用于文档转换和向量嵌入

### 2. 文件级缓存（`FileCacheManager`）

**位置**: [`file_cache_manager.py`](../../backend/personaldb/core/file_cache_manager.py#L1)

- 基于文件 MD5 哈希
- 缓存过期时间：7 天
- 目录结构：`summeryanyfile_cache/{mode}/files|markdown|metadata/`

### 3. 临时文件保留

**临时目录**：默认 `var/tmp/personaldb/`（可通过 `AI2PPT_TMP_DIR` 调整）

- 文件上传（`POST /upload/` 的 `file` 分支）：当前实现会将上传内容落到临时目录，**处理完成后不会自动删除**（便于调试，删除逻辑在代码中被注释掉）。
- URL 下载（`POST /upload/` 的 `url` 分支）：下载的临时文件会在处理完成后删除。

---

## 分块策略

**当前使用**: FastChunker

**实现**: [`_chunk_text()`](../../backend/personaldb/main.py#L314)

```python
def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 200):
    chunker = FastChunker(max_tokens=max_chars)
    chunks = chunker.chunk_text(text)
    return [chunk.content for chunk in chunks]
```

**说明**: 根据 AGENTS.md，已从 SemanticChunker 切换到 `FastChunker(max_tokens=1200)`

---

## 向量化与检索

### 嵌入模型

**位置**: [`embedding_utils.py:335`](../../backend/personaldb/embedding_utils.py#L335)

**支持的协议类型 (`EMBEDDING_TYPE`)**:
- `openai`: 所有 OpenAI 兼容的嵌入服务  
  （OpenAI / DeepSeek / 阿里 DashScope / 豆包 / vLLM / Xinference / SiliconFlow 等，只要提供 embeddings 接口）
- `ollama`: Ollama 原生 `/api/embeddings`

### ChromaDB

**位置**: [`embedding_utils.py:95`](../../backend/personaldb/embedding_utils.py#L95)

- 持久化到 `var/cache/personaldb/chromadb/`（可通过 `AI2PPT_CACHE_DIR` 调整）
- 用户隔离：每用户一个 collection（`user_{userId}`）
- 余弦相似度检索
- 支持关键词混合搜索

**核心方法**:
- [`insert_file_vectors()`](../../backend/personaldb/embedding_utils.py#L219): 插入向量
- [`query2collection()`](../../backend/personaldb/embedding_utils.py#L171): 查询
- [`delete_file_vectors()`](../../backend/personaldb/embedding_utils.py#L200): 删除
- [`list_files_by_user()`](../../backend/personaldb/embedding_utils.py#L273): 列出文件

---

## API 端点

### POST `/upload/`
上传文件或URL进行处理和向量化

**参数**: `userId`, `fileId`, `folderId`, `fileType`, `url` 或 `file`

### POST `/search`
搜索个人知识库

**参数**: `userId`, `query`, `keyword`, `topk`

### POST `/vectorize/text`
纯文本向量化

**参数**: `content`, `fileId`, `fileName`, `userId`

### GET `/files/{user_id}`
列出用户所有文件

---

## 环境变量

### 必需
```bash
# 统一配置（推荐）
EMBEDDING_TYPE=openai          # openai 或 ollama
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_API_KEY=your_key
USE_MINERU=false               # GPU加速，默认false
```

### 可选
```bash
EMBEDDING_DIM=1536
#EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1   # OpenAI 兼容端点示例
```

---

## 工作流程

```
上传 → 下载(UUID命名) → 检查缓存 → 转换Markdown →
缓存 → 分块(FastChunker) → 嵌入(批量) → 存储(ChromaDB) → 保留临时文件
```

---

## 关键特性

1. **GPU加速**: `USE_MINERU=true` 启用 MinerU GPU加速
2. **智能缓存**: 函数级 + 文件级双层缓存
3. **灵活分块**: 当前 FastChunker，支持切换
4. **多提供商**: 支持多种嵌入模型提供商
5. **用户隔离**: 独立 ChromaDB collection

---

## 与其他服务集成

- **main_api**: 调用 `/search` 进行知识检索
- **slide_agent**: 使用检索结果作为生成上下文

---

## 故障排查

**PDF转换失败**: 检查 `USE_MINERU`，设为 `false` 回退到 MarkItDown

**向量化失败**: 检查 API 密钥和网络连接

**缓存问题**: 清理 `cache/` 和 `summeryanyfile_cache/` 目录
