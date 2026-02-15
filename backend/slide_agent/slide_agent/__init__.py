"""
slide_agent 包初始化。

注意：这里不要导入任何“重型模块”（尤其是 `agent`）。
否则一旦有人仅仅为了使用 `slide_agent.runtime_paths` / `utils` 等轻量模块而导入包，
也会被迫触发 ADK / LLM / 工具链的完整导入与初始化，导致冷启动显著变慢，甚至形成循环导入。
"""

__all__ = []
