from __future__ import annotations

import errno
import socket


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

