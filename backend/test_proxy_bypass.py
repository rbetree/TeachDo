import json
import asyncio
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from backend.main_api.content_client import A2AContentClientWrapper
from backend.main_api.outline_client import A2AOutlineClientWrapper


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class _AgentCardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/.well-known/agent.json":
            self.send_response(404)
            self.end_headers()
            return

        # 只返回 main_api 侧 A2ACardResolver 解析所需的最小字段集合
        # 字段结构参考运行中的 outline/content agent card。
        body = json.dumps(
            {
                "capabilities": {"streaming": True},
                "defaultInputModes": ["text"],
                "defaultOutputModes": ["text"],
                "description": "Test agent card",
                "name": "test-agent",
                "protocolVersion": "0.2.5",
                "skills": [
                    {
                        "description": "Test skill",
                        "examples": ["outline"],
                        "id": "test_agent",
                        "name": "test-agent",
                        "tags": ["test"],
                    }
                ],
                "url": "http://127.0.0.1/",
                "version": "1.0.0",
            }
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # 测试里不输出 http.server 默认日志，避免污染 pytest 输出
        return


@pytest.fixture()
def agent_card_server():
    port = _pick_free_port()
    server = HTTPServer(("127.0.0.1", port), _AgentCardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()


def test_outline_setup_bypasses_proxy_env(monkeypatch, agent_card_server):
    # 模拟“系统代理开启但 no_proxy 未正确包含 127.0.0.1”的环境
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:1")
    monkeypatch.setenv("https_proxy", "http://127.0.0.1:1")
    monkeypatch.setenv("all_proxy", "http://127.0.0.1:1")
    monkeypatch.setenv("no_proxy", "")
    monkeypatch.setenv("NO_PROXY", "")

    wrapper = A2AOutlineClientWrapper(session_id="test", agent_url=agent_card_server)
    asyncio.run(wrapper.setup())
    assert wrapper.agent_card is not None
    assert wrapper.agent_card.name == "test-agent"


def test_content_setup_bypasses_proxy_env(monkeypatch, agent_card_server):
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:1")
    monkeypatch.setenv("https_proxy", "http://127.0.0.1:1")
    monkeypatch.setenv("all_proxy", "http://127.0.0.1:1")
    monkeypatch.setenv("no_proxy", "")
    monkeypatch.setenv("NO_PROXY", "")

    wrapper = A2AContentClientWrapper(session_id="test", agent_url=agent_card_server)
    asyncio.run(wrapper.setup())
    assert wrapper.agent_card is not None
    assert wrapper.agent_card.name == "test-agent"
