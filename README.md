# ai2ppt

---

## ✨ 功能特性

* **智能大纲生成**
  输入主题后，自动生成逻辑清晰、结构合理的演示文稿大纲。

* **逐页内容生成**
  采用流式传输技术，实现 PPT 内容的实时生成与展示，提升交互体验。

* **用户已有大纲或者文件上传到知识库**
  根据知识库的内容生成PPT。

* **模板支持**
  提供多种模板供用户选择，支持内容与样式的分离式填充。

* **不同模型**
  支持各种商业模型和本地模型，参考 doc/ai/CUSTOM_MODEL.md。

* **前后端分离架构**
  前端使用 **Vue.js + Vite + TypeScript**，后端基于 **Python (FastAPI)**，架构清晰、可扩展性强。

* **强化学习驱动**
  引入 **GRPO 强化学习方法**，优化 PPT Agent 的生成效果，使结果更符合用户需求。

---

## 🛠 技术栈

* **前端**: Vue.js, Vite, TypeScript
* **后端**: Python, Flask/FastAPI, A2A, ADK, MCP 搜索
* **AI 模型**: 大语言模型联网搜索（用于大纲与内容生成），可以自行取消联网搜索，如果不需要，找到agent.py中的tools=[]，改成空即可。

---

## 📋 项目结构

```
TrainPPTAgent/
├── backend/           # 后端代码
│   ├── mock_api/      # 模拟生成PPT
│   ├── main_api/      # 核心 API 服务
│   ├── slide_agent/   # AI Agent根据大纲撰搜索网络或者本地知识库写每页PPT
│   ├── simpleOutline/  # AI Agent 搜索并写大纲
│   ├── personaldb/     #知识库，解析各种格式的文件，用于搜索知识库生成PPT
├── frontend/          # 前端代码
│   ├── src/
│   │   ├── views/     # 页面组件（大纲、编辑等）
│   │   ├── services/  # API 调用服务
│   │   └── ...
│   └── vite.config.ts # 前端配置
└── doc/               # 项目文档
    ├── README.md        # 文档索引
    ├── legacy/          # 临时/过时资料（仅供参考）
    ├── Template.md      # 模板制作与导入
    ├── PPT_Structure.md # Slide JSON 结构约定
    ├── CHANGES.md       # 变更记录
    └── ...
```

---

## 🚀 快速开始

### 快速体验
```
# 启动前端
cd frontend
npm install
npm run dev

# 启动模拟后端
cd backend/mock_api
python mock_main.py
```

### 🎯 一键部署（推荐）

#### 新增功能：统一配置 + 一键启动

```bash
# 1. 配置环境变量
cp env_template.txt .env
修改.env # 填入你的API密钥

# 2. 一键启动生产环境
python start.py
```

**功能特性：**
- ✅ **统一配置管理** - 所有环境变量集中在项目根目录 `.env`（服务目录 `.env` 可选覆盖）
- ✅ **自动化部署** - 依赖安装、前端构建、服务启动一键完成
- ✅ **完整监控** - 进程监控、日志管理、优雅停止
- ✅ **生产就绪** - 适合正式环境的性能和稳定性配置

**访问地址：**
- 前端界面：`http://127.0.0.1:5173`

> 📚 详细说明请参考：[生产环境部署指南](README_PRODUCTION.md)

---

### 分别启动前后端服务

#### 方法二：一键启动

使用我们提供的启动脚本，可以一键启动所有后端服务：

```bash
cd backend
pip install -r requirements.txt
python start_backend.py
```

**功能特性：**
- ✅ 自动检查Python版本和依赖
- ✅ 自动安装所需包
- ✅ 端口占用检测和清理（需要用户确认）
- ✅ 自动设置环境文件
- ✅ 多进程管理和监控

#### 方法三：手动启动

0. 在项目根目录配置统一环境变量（只需一次）：

   ```bash
   cp env_template.txt .env
   # 修改 .env，填入你的 API Key
   ```

1. 进入后端目录：

   ```bash
   cd backend
   ```
2. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```
3. 启动主 API 服务（默认运行在 `http://127.0.0.1:6800`）：

   ```bash
   cd main_api
   uvicorn main:app --reload --port 6800
   ```
4. 启动大纲生成服务（默认运行在 `http://127.0.0.1:10001`）：

   ```bash
   cd ../simpleOutline
   python main_api.py
   ```
5. 启动 PPT 内容生成服务（默认运行在 `http://127.0.0.1:10011`）：

   ```bash
   cd ../slide_agent
   python main_api.py
   ```
6. （可选但推荐）启动知识库服务（默认运行在 `http://127.0.0.1:9100`）：

   ```bash
   cd ../personaldb
   uvicorn main:app --reload --port 9100
   ```

> 如需对单个服务做“本机临时覆盖”，再在对应服务目录复制 `env_template` 为 `.env` 并修改（覆盖优先级：系统环境变量 > 服务 `.env` > 根目录 `.env`）。

> **详细说明：** 请参考 [backend/启动说明.md](backend/启动说明.md)

### 前端服务

1. 进入前端目录：

   ```bash
   cd frontend
   ```
2. 安装依赖：

   ```bash
   npm install
   ```
3. 启动开发服务器（默认运行在 `http://127.0.0.1:5173`）：

   ```bash
   npm run dev
   ```

> **提示**: 前端通过 Vite 代理与后端 API 通信，具体配置请查看 `frontend/vite.config.ts`。

#### 方法四：docker compose一键部署(确保能连接docker hub网络)
docker compose up --build

---

## 🤖 AI 生成流程

1. **输入主题 / 选择文件**
   - 主题模式：用户在前端首页输入主题
   - 文档模式：用户在前端首页上传 PDF / DOCX / MD 等文档
2. **在大纲页流式生成大纲**
   - 主题模式：`/outline` 页面调用 `/tools/aippt_outline`，流式生成 Markdown 大纲
   - 文档模式：`/outline` 页面调用 `/tools/aippt_outline_from_file`，基于上传文档流式生成大纲（知识库解析 + 大纲生成）
3. **编辑与确认大纲**
   - 用户在大纲编辑页调整结构和内容
4. **生成内容**
   - 调用 `/tools/aippt`，结合模板逐页生成 PPT 内容，可选择是否基于上传文件、是否使用网络搜索
5. **实时渲染**
   - 前端渲染并展示完整 PPT，支持继续编辑与导出

---

## 📑 流程图

PPTGen：可以扩展为更多功能的Agent，例如检查质量（图表等)
```mermaid
flowchart TD
  U((用户)) --> FE[前端界面]
  FE -->|输入主题| API[后端 API]

  API -->|调用大纲服务| Outline[大纲服务]
  Outline -->|调用 Web搜索| WebSearch1[Web 搜索]
  Outline --> API

  FE -->|确认大纲| API --> PPTGen[PPT生成服务：内部循环和检查Json格式]
  PPTGen -->|调用 Web搜索| WebSearch2[Web 搜索]
  PPTGen -->|调用 配图搜索| ImgSearch[配图搜索]
  PPTGen -->|调用 搜索上传文件| DBSearch[知识库]
  PPTGen --> API

  FE -->|渲染展示 PPT| U
```

---

## 🖼 界面示意

* **大纲生成**
  ![outline.png](doc/assets/images/outline.png)

* **模板选择**
  ![select_template.png](doc/assets/images/select_template.png)

* **逐页生成 PPT**
  ![start_ppt_generate.png](doc/assets/images/start_ppt_generate.png)

* **图表支持 PPT**
  ![图表支持.png](doc/assets/images/图表支持.png)


---

## 📌 待办事项
* [x] 图表的支持
* [ ] 支持上传自定义 PPT 模板并自动标注

---

## 📖 文档与参考

维护版文档统一在 `doc/`，并遵循“**单一职责**”与“**主题不重复**”的约定：

- **维护版入口（索引）**：`doc/README.md`
- **维护版（对齐当前实现）**：
  - `doc/architecture/PROJECT_ARCHITECTURE.md`：系统架构与能力边界
  - `doc/architecture/FEATURE_API_OVERVIEW.md`：功能 → API / 页面映射（稳定口径）
  - `doc/backend/backend_api_reference.md`：后端 API 契约（以代码为准，最权威）
  - `doc/backend/backend_deployment.md`：后端运行/部署方式
  - `doc/dev/FRONTEND_GUIDE.md`：前端技术总览（实现为准）
  - `doc/dev/FRONTEND_API_CALLS.md`：前端 `src/services` 调用清单（方法 → 端点）
  - `doc/dev/ENV_GUIDE.md`：统一 `.env` 配置与优先级
  - `doc/DockerDeploy.md`：Docker/Compose 部署说明
  - `doc/Template.md`：模板制作与导入
  - `doc/PPT_Structure.md`：Slide JSON 结构约定
  - `doc/ai/*`：Prompt / 模型 / 训练相关（维护版）
  - `doc/CHANGES.md`：变更记录
- **归档（仅参考，不作为信息源）**：`doc/legacy/README.md`

冲突处理：若维护版文档与实际代码/接口不一致，以 `doc/backend/backend_api_reference.md` 与源码为准。
---

## 📝 关于前端引用项目（本项目后端免版权，但前端部分为AGPL-3版权）：
  [https://github.com/pipipi-pikachu/PPTist](https://github.com/pipipi-pikachu/PPTist)

## 📬 联系方式

如有问题，请联系作者：
![weichat.png](doc/assets/images/weichat.png)

---
