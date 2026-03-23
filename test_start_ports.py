from __future__ import annotations

import errno
import socket


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_check_tcp_port_bindable_detects_inuse_on_other_local_ip():
    """
    回归测试：
    - 某进程监听在 127.0.0.2:PORT（外网 IP / 其他网卡同理）
    - 使用 connect(127.0.0.1, PORT) 会失败（看起来像“端口未占用”）
    - 但实际 bind(0.0.0.0, PORT) 会报 EADDRINUSE（启动会失败）
    """
    from start import check_tcp_port_bindable

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.2", 0))
    port = int(listener.getsockname()[1])
    listener.listen(1)
    try:
        ok_any, err_any = check_tcp_port_bindable("0.0.0.0", port)
        assert not ok_any
        assert err_any == errno.EADDRINUSE

        ok_local, err_local = check_tcp_port_bindable("127.0.0.1", port)
        assert ok_local
        assert err_local is None
    finally:
        listener.close()


def test_check_tcp_port_bindable_normalizes_localhost_to_ipv4():
    from start import check_tcp_port_bindable

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    port = int(listener.getsockname()[1])
    listener.listen(1)
    try:
        ok, err = check_tcp_port_bindable("localhost", port)
        assert not ok
        assert err == errno.EADDRINUSE
    finally:
        listener.close()


def test_check_tcp_port_bindable_free_port():
    from start import check_tcp_port_bindable

    port = _pick_free_port()
    ok, err = check_tcp_port_bindable("127.0.0.1", port)
    assert ok is True
    assert err is None


def test_check_tcp_port_bindable_occupied_port():
    from start import check_tcp_port_bindable

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = int(s.getsockname()[1])

        ok, err = check_tcp_port_bindable("127.0.0.1", port)
        assert ok is False
        # 平台 errno 可能为空，但若存在应为 EADDRINUSE。
        if err is not None:
            assert int(err) == int(errno.EADDRINUSE)


def test_check_ports_autoswitch_personal_db_port_when_unbindable(monkeypatch):
    import start

    def fake_check_tcp_port_bindable(_host: str, port: int):
        if int(port) == 9100:
            return False, errno.EADDRINUSE
        if int(port) == 9101:
            return True, None
        return True, None

    monkeypatch.setattr(start, "check_tcp_port_bindable", fake_check_tcp_port_bindable)
    monkeypatch.setattr(start.ProductionStarter, "kill_processes_on_ports", lambda _self, _ports: 0)

    # 显式指定为默认端口，避免本机 settings.json/.env 干扰测试。
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PERSONAL_DB_PORT", "9100")
    monkeypatch.setenv("PERSONAL_DB", "http://127.0.0.1:9100")
    monkeypatch.delenv("PERSONALDB_PORT", raising=False)

    starter = start.ProductionStarter(no_install=True)
    starter.setup_logging()

    starter.check_ports()

    assert int(starter.services["personal_db"]["port"]) == 9101
    env = starter._build_subprocess_env()
    assert env["PERSONAL_DB_PORT"] == "9101"
    assert env["PERSONALDB_PORT"] == "9101"
    assert env["PERSONAL_DB"] == "http://127.0.0.1:9101"
