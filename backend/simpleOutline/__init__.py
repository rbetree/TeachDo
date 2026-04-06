"""
simpleOutline 服务包。

说明：
- 该目录既支持“脚本方式”启动（例如 `python main_api.py`，使用同目录的顶层导入），
  也支持作为 package 被测试代码引用（例如 `import backend.simpleOutline.prompt`）。
- 为避免 import package 时触发重依赖（LLM/SDK）初始化，这里不做副作用导入。
"""
