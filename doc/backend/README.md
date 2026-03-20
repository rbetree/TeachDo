# 后端文档导航

本目录是后端相关文档的索引页，推荐先读「部署/运行」与「API 参考」，再按需深入到各服务实现细节。

---

## 1) 推荐阅读路径

- 快速启动与配置：`../dev/ENV_GUIDE.md`、`./backend_deployment.md`、`../DockerDeploy.md`
- API 对接（以代码为准）：`./backend_api_reference.md`
- 后端架构总览：`./backend_architecture.md`
- 各服务实现细节：
  - `./main_api_service.md`
  - `./simpleOutline_service.md`
  - `./slide_agent_service.md`
  - `./personaldb_service.md`

---

## 2) 后端服务与端口

- `main_api`：6800（对前端唯一入口）
- `simpleOutline`：10001（大纲 Agent）
- `slide_agent`：10011（内容 Agent）
- `personaldb`：9100（知识库/向量检索）

---

## 3) 其他入口文档（仓库根目录）

- 项目整体说明：`../../README.md`
- 生产部署说明：`../../README_PRODUCTION.md`
- 后端启动说明（更偏操作）：`../../backend/启动说明.md`

---

## 4) 历史/抓包类文档（仅供参考）

- `../legacy/API_OUTLINE.md`、`../legacy/API_CONTENT.md`、`../legacy/API_TEMPLATE.md`、`../legacy/API_IMAGE.md`

这些文件多为「抓包/记录」性质，可能包含无关请求头（Cookie 等）或与代码实现存在偏差；对接时请以 `./backend_api_reference.md` 为准。

1. **善用搜索**：使用编辑器或浏览器的搜索功能快速定位信息
2. **循序渐进**：从架构文档开始，逐步深入到具体服务
3. **结合代码**：文档和代码结合阅读，理解更深刻
4. **实践为主**：动手部署和调试，加深理解
5. **记录问题**：遇到问题记录下来，可能对其他人也有帮助

---

**祝您使用愉快！如有任何问题，欢迎提交 Issue 或参与讨论。** 🚀
