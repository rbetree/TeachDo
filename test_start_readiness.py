from __future__ import annotations

import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - http.server 接口约定
        if self.path != "/healthz":
            self.send_response(404)
            self.end_headers()
            return
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 - 保持签名
        # 避免污染 pytest 输出
        return


def test_wait_for_http_ready_success():
    from start import wait_for_http_ready

    port = _pick_free_port()
    server = HTTPServer(("127.0.0.1", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert wait_for_http_ready(f"http://127.0.0.1:{port}/healthz", timeout_s=3, interval_s=0.1)
    finally:
        server.shutdown()
        server.server_close()


def test_wait_for_http_ready_timeout():
    from start import wait_for_http_ready

    port = _pick_free_port()
    # 不启动服务，应该超时
    assert not wait_for_http_ready(f"http://127.0.0.1:{port}/healthz", timeout_s=1, interval_s=0.1)

