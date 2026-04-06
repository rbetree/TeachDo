#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeachDo dev 环境一键启动脚本，生产环境需要使用 `npm run build` 或 Docker
支持前端构建、后端服务启动、进程管理和监控
"""

import argparse
import fnmatch
import http.client
import io
import logging
import os
import re
import shutil
import signal
import ssl
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlsplit

import glob
import threading
from dotenv import load_dotenv

# -----------------------------
#多文件 tail -f 的实现
# -----------------------------
class MultiLogTailer:
    """
    在同一控制台跟随打印 logs/*.log 的新增内容，行为类似 `tail -f`.
    - 自动发现新文件
    - 每行带文件名前缀
    - 可优雅停止
    """
    COLORS = [
        "\033[95m", "\033[94m", "\033[96m", "\033[92m",
        "\033[93m", "\033[91m", "\033[90m"
    ]
    RESET = "\033[0m"

    def __init__(
        self,
        logs_dir: Path,
        pattern: str = "*.log",
        poll_interval: float = 1.0,
        color: bool = True,
        exclude_globs: Optional[List[str]] = None,
    ):
        self.logs_dir = Path(logs_dir)
        self.pattern = pattern
        self.poll_interval = poll_interval
        self.exclude_globs = exclude_globs or []
        self.stop_event = threading.Event()
        self.threads: Dict[Path, threading.Thread] = {}
        self.opened: Dict[Path, io.TextIOWrapper] = {}
        self._color = color and sys.stdout.isatty()
        self._color_map: Dict[Path, str] = {}
        self._print_lock = threading.Lock()

    def _is_excluded(self, path: Path) -> bool:
        name = path.name
        return any(fnmatch.fnmatch(name, pat) for pat in self.exclude_globs)

    def _color_for(self, path: Path) -> str:
        if not self._color:
            return ""
        if path not in self._color_map:
            idx = len(self._color_map) % len(self.COLORS)
            self._color_map[path] = self.COLORS[idx]
        return self._color_map[path]

    def _prefix(self, path: Path) -> str:
        color = self._color_for(path)
        name = path.name
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if color:
            return f"{ts} {color}[{name}]{self.RESET} "
        return f"{ts} [{name}] "

    def _tail_file(self, path: Path):
        try:
            f = open(path, "r", encoding="utf-8", errors="ignore")
            self.opened[path] = f
            # 定位到文件末尾，仅读取新增
            f.seek(0, os.SEEK_END)
            while not self.stop_event.is_set():
                line = f.readline()
                if line:
                    # 去掉末尾多余换行后打印
                    if line.endswith("\n"):
                        line = line[:-1]
                    with self._print_lock:
                        print(self._prefix(path) + line, flush=True)
                else:
                    # 文件可能被轮转/截断，尝试刷新并等待
                    if not path.exists():
                        # 若被轮转导致路径不存在，稍等后退出当前线程，等待主 watcher 重新发现新文件
                        break
                    # 若文件被截断（例如 start.py 重新以 'w' 打开写入），文件指针可能在 EOF 之后，
                    # 需要把读取位置拉回到文件起点，否则会一直读不到新增内容。
                    try:
                        if path.stat().st_size < f.tell():
                            f.seek(0, os.SEEK_SET)
                    except Exception:
                        pass
                    time.sleep(0.1)
        except Exception as e:
            with self._print_lock:
                print(f"[LogTailer] 打开/读取日志失败: {path} -> {e}", flush=True)
        finally:
            try:
                f = self.opened.pop(path, None)
                if f:
                    f.close()
            except Exception:
                pass
            # 线程退出时从线程表删除
            self.threads.pop(path, None)

    def _spawn_tail_thread(self, path: Path):
        if path in self.threads:
            return
        t = threading.Thread(target=self._tail_file, args=(path,), daemon=True)
        self.threads[path] = t
        t.start()

    def _watcher(self):
        # 主 watcher：定期扫描新文件
        while not self.stop_event.is_set():
            try:
                self.logs_dir.mkdir(exist_ok=True)
                matches = [Path(p) for p in glob.glob(str(self.logs_dir / self.pattern))]
                # 启动新出现的文件
                for p in matches:
                    if p.is_file() and p not in self.threads and not self._is_excluded(p):
                        self._spawn_tail_thread(p)
                # 清理已消失的文件对应线程（线程在文件消失时会自行退出）
                for p in list(self.threads.keys()):
                    if not p.exists():
                        # 线程会在读取时自行退出，这里不强杀
                        pass
            except Exception as e:
                with self._print_lock:
                    print(f"[LogTailer] 目录扫描失败: {e}", flush=True)
            finally:
                time.sleep(self.poll_interval)

    def start(self):
        # 先对当前存在的文件起 tail
        initial = [Path(p) for p in glob.glob(str(self.logs_dir / self.pattern))]
        for p in sorted(initial):
            if p.is_file() and not self._is_excluded(p):
                self._spawn_tail_thread(p)
        # 再起 watcher
        self.watcher_thread = threading.Thread(target=self._watcher, daemon=True)
        self.watcher_thread.start()

    def stop(self):
        self.stop_event.set()
        # 等待 watcher 退出
        try:
            if hasattr(self, 'watcher_thread'):
                self.watcher_thread.join(timeout=2)
        except Exception:
            pass
        # 关闭所有文件
        for f in list(self.opened.values()):
            try:
                f.close()
            except Exception:
                pass
        self.opened.clear()
        # 等待子线程退出
        for t in list(self.threads.values()):
            try:
                t.join(timeout=2)
            except Exception:
                pass
        self.threads.clear()


def _normalize_host(host: str) -> str:
    host = (host or "").strip()
    if host.startswith(("http://", "https://")):
        parsed = urlsplit(host)
        return parsed.hostname or host
    return host


def _access_host_for_bind_host(bind_host: str) -> str:
    bind_host = _normalize_host(bind_host)
    if bind_host in {"0.0.0.0", "::", "localhost"}:
        return "127.0.0.1"
    return bind_host or "127.0.0.1"


def _http_get_status(url: str, *, timeout_s: float = 2.0) -> Optional[int]:
    """
    发起一次 HTTP GET 探测并返回 status_code。

    - 不使用环境代理（http.client 直连），避免本机服务误走代理。
    - 仅用于启动探针，不读取响应体内容。
    """
    parts = urlsplit(url)
    scheme = (parts.scheme or "http").lower()
    host = parts.hostname
    if not host:
        return None

    port = parts.port or (443 if scheme == "https" else 80)
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"

    conn = None
    try:
        if scheme == "https":
            conn = http.client.HTTPSConnection(host, port, timeout=timeout_s, context=ssl.create_default_context())
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout_s)

        conn.request("GET", path, headers={"Connection": "close"})
        resp = conn.getresponse()
        try:
            resp.read()
        except Exception:
            pass
        return resp.status
    except Exception:
        return None
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass


def wait_for_http_ready(
    url: str,
    *,
    timeout_s: int,
    interval_s: float = 0.6,
    expected_statuses: Optional[Set[int]] = None,
) -> bool:
    """
    轮询 URL，直到返回期望的 HTTP 状态码（默认 200）或超时。

    该函数会被单元测试直接引用，请保持为纯函数（不要依赖 ProductionStarter 状态）。
    """
    expected = expected_statuses or {200}
    deadline = time.monotonic() + max(1, int(timeout_s))
    while time.monotonic() < deadline:
        status = _http_get_status(url, timeout_s=2.0)
        if status in expected:
            return True
        time.sleep(max(0.1, float(interval_s)))
    return False


def check_tcp_port_bindable(host: str, port: int) -> Tuple[bool, Optional[int]]:
    """
    检查 `host:port` 是否可被当前进程绑定（TCP LISTEN）。

    与“connect 探测端口是否有服务”不同，这里直接以 bind 成功与否判断端口是否可用：
    - 能覆盖“端口被占用但 127.0.0.1 连接不上”的场景（例如进程绑定在 127.0.0.2 / 外网 IP 上）
    - 更贴近实际启动时的行为（uvicorn 会在 bind 时失败）

    返回：
    - (True, None)：可绑定
    - (False, errno)：不可绑定（errno 可能为空）
    """
    import socket

    host = _normalize_host(host)
    # 用 127.0.0.1 替代 localhost，避免在部分环境下解析到 IPv6 导致误判/漂移。
    if host in {"", "localhost"}:
        host = "127.0.0.1"

    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as s:
            # 与 uvicorn 等 Web server 的默认行为对齐：允许快速重启，避免 TIME_WAIT 造成误判。
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except Exception:
                pass
            s.bind((host, int(port)))
            # 进一步贴近实际：确保该端口可进入 LISTEN。
            try:
                s.listen(1)
            except Exception:
                pass
        return True, None
    except OSError as e:
        return False, getattr(e, "errno", None)
    except Exception:
        return False, None


def find_listening_pids_on_tcp_port(port: int) -> Set[int]:
    """
    尽力定位正在监听（TCP LISTEN）指定端口的进程 PID。

    注意：
    - 在 WSL mirrored networking、宿主机端口占用、或权限受限时，可能无法返回 PID。
    - 本函数用于“最佳努力”的诊断与清理，不应作为端口占用判断的唯一依据。
    """

    def _via_psutil() -> Set[int]:
        try:
            import psutil  # type: ignore
        except Exception:
            return set()

        wanted: Set[int] = set()
        try:
            for c in psutil.net_connections(kind="inet"):
                try:
                    if not c.laddr:
                        continue
                    if int(getattr(c.laddr, "port", -1)) != int(port):
                        continue
                    if getattr(c, "status", None) != psutil.CONN_LISTEN:
                        continue
                    pid = getattr(c, "pid", None)
                    if pid:
                        wanted.add(int(pid))
                except Exception:
                    continue
        except Exception:
            return set()
        return wanted

    def _via_lsof() -> Set[int]:
        if shutil.which("lsof") is None:
            return set()
        try:
            result = subprocess.run(
                ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                capture_output=True,
                text=True,
                check=False,
            )
            out = (result.stdout or "").strip()
            if not out:
                return set()
            return {int(x) for x in out.splitlines() if x.strip().isdigit()}
        except Exception:
            return set()

    def _via_fuser() -> Set[int]:
        if shutil.which("fuser") is None:
            return set()
        try:
            result = subprocess.run(
                ["fuser", "-n", "tcp", str(port)],
                capture_output=True,
                text=True,
                check=False,
            )
            out = (result.stdout or "") + (result.stderr or "")
            return {int(x) for x in re.findall(r"\b\d+\b", out)}
        except Exception:
            return set()

    def _via_ss() -> Set[int]:
        if shutil.which("ss") is None:
            return set()
        try:
            result = subprocess.run(
                ["ss", "-ltnp", f"sport = :{port}"],
                capture_output=True,
                text=True,
                check=False,
            )
            out = (result.stdout or "") + (result.stderr or "")
            return {int(x) for x in re.findall(r"pid=(\d+)", out)}
        except Exception:
            return set()

    for getter in (_via_psutil, _via_lsof, _via_fuser, _via_ss):
        pids = getter()
        if pids:
            return pids
    return set()


def _tail_last_lines(path: Path, *, max_lines: int = 80) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [line.rstrip("\n") for line in lines[-max_lines:]]
    except Exception:
        return []


class ProductionStarter:
    def __init__(
        self,
        *,
        no_install: bool = False,
        verbose_install: bool = False,
        timeout_s: Optional[int] = None,
        parallel_start: bool = False,
    ):
        self.project_root = Path(__file__).parent
        self.backend_dir = self.project_root / "backend"
        # TeachDo 新仓库以 frontend 作为唯一前端入口
        self.frontend_dir = self.project_root / "frontend"
        self.dist_dir = self.frontend_dir / "dist"
        self.logs_dir = self.project_root / "logs"

        self.no_install = no_install
        self.verbose_install = verbose_install
        self.user_timeout_s = timeout_s
        self.parallel_start = parallel_start

        # 先加载 settings.json（若存在），再加载 .env；从而实现 settings 覆盖 .env
        try:
            from backend.common.settings_store import load_and_apply_settings

            load_and_apply_settings(overwrite=False, repo_root=self.project_root)
        except Exception:
            pass

        # 加载环境配置
        env_file = self.project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
        else:
            # 允许无 .env 启动：用户可通过前端“设置”页写入 var/settings.json
            print("WARNING: 未找到 .env，将使用默认配置启动（可在“设置”页保存配置后重启服务生效）")

        # 日志目录可由 TEACHDO_LOG_DIR 覆盖（默认 logs）
        configured_logs_dir = (os.environ.get("TEACHDO_LOG_DIR") or "logs").strip() or "logs"
        logs_dir_path = Path(configured_logs_dir).expanduser()
        if not logs_dir_path.is_absolute():
            logs_dir_path = self.project_root / logs_dir_path
        self.logs_dir = logs_dir_path

        self.bind_host = _normalize_host(os.environ.get("HOST", "127.0.0.1"))
        self.access_host = _access_host_for_bind_host(self.bind_host)

        personaldb_port = int(
            os.environ.get("PERSONALDB_PORT")
            or os.environ.get("PERSONAL_DB_PORT")
            or (urlsplit(os.environ.get("PERSONAL_DB", "")).port if os.environ.get("PERSONAL_DB") else None)
            or "9100"
        )
        outline_port = int(
            os.environ.get("OUTLINE_API_PORT")
            or (urlsplit(os.environ.get("OUTLINE_API", "")).port if os.environ.get("OUTLINE_API") else None)
            or "10001"
        )
        content_port = int(
            os.environ.get("CONTENT_API_PORT")
            or (urlsplit(os.environ.get("CONTENT_API", "")).port if os.environ.get("CONTENT_API") else None)
            or "10011"
        )
        main_api_port = int(os.environ.get("MAIN_API_PORT", "6800"))

        # 按依赖顺序启动：personaldb -> outline -> slide_agent -> main_api
        self.services: Dict[str, Dict] = {
            "personal_db": {
                "port": personaldb_port,
                "dir": self.backend_dir / "personaldb",
                "script": "main.py",
                "name": "知识库",
                "ready_path": "/healthz",
                "default_timeout_s": 180,
                "args": [],
            },
            "outline": {
                "port": outline_port,
                "dir": self.backend_dir / "simpleOutline",
                "script": "main_api.py",
                "name": "大纲生成服务",
                "ready_path": "/healthz",
                # 该服务依赖 google-adk / genai 等，冷启动在部分环境可能较慢，给更充足的默认等待时间。
                "default_timeout_s": 600,
                "args": [
                    "--host",
                    self.bind_host,
                    "--port",
                    str(outline_port),
                    "--agent_url",
                    f"http://{self.access_host}:{outline_port}/",
                ],
            },
            "content": {
                "port": content_port,
                "dir": self.backend_dir / "slide_agent",
                "script": "main_api.py",
                "name": "内容生成服务",
                "ready_path": "/healthz",
                # 同 outline，冷启动可能较慢。
                "default_timeout_s": 600,
                "args": [
                    "--host",
                    self.bind_host,
                    "--port",
                    str(content_port),
                    "--agent_url",
                    f"http://{self.access_host}:{content_port}/",
                ],
            },
            "main_api": {
                "port": main_api_port,
                "dir": self.backend_dir / "main_api",
                "script": "main.py",
                "name": "主API服务",
                "ready_path": "/healthz",
                "default_timeout_s": 180,
                "args": [],
            },
        }

        # frontend/vite.config.ts 默认端口为 5174；这里通过 CLI 参数显式传入，避免误导/漂移
        self.frontend_port = int(os.environ.get("FRONTEND_PORT", "5174"))
        self.frontend_host = "127.0.0.1"

        self.processes: Dict[str, subprocess.Popen] = {}
        self._log_file_handles: Dict[str, io.TextIOWrapper] = {}
        # 运行期对环境变量的覆盖（仅对子进程生效，不修改用户的 Shell 环境）。
        self._runtime_env_overrides: Dict[str, str] = {}
        self._sync_internal_service_env_overrides()

    def _sync_internal_service_env_overrides(self) -> None:
        """
        同步“内部服务 URL/端口”到子进程环境变量。

        背景：
        - TeachDo 支持通过 `var/settings.json` 持久化 OUTLINE_API / CONTENT_API / PERSONAL_DB 等 URL；
        - main_api 内部客户端会优先读取这些 URL（而不是 *_PORT）；
        - 当用户临时通过环境变量改端口（例如 `OUTLINE_API_PORT=10034`）或 start.py 自动换端口时，
          如果 URL 未同步更新，会出现 main_api 仍然请求旧端口的情况（典型报错：无法获取 agent card）。

        约束：
        - 只影响 start.py 启动的子进程，不污染用户 Shell 环境；
        - 统一使用 access_host（通常为 127.0.0.1）拼接 URL，避免客户端误用 0.0.0.0。
        """

        def _service_port(service_name: str, default_port: int) -> int:
            cfg = self.services.get(service_name) or {}
            try:
                return int(cfg.get("port") or default_port)
            except Exception:
                return int(default_port)

        personaldb_port = _service_port("personal_db", 9100)
        outline_port = _service_port("outline", 10001)
        content_port = _service_port("content", 10011)
        main_api_port = _service_port("main_api", 6800)

        # 对齐端口类变量（用于服务自身启动，以及前端 proxy 的一致性）。
        self._runtime_env_overrides["PERSONAL_DB_PORT"] = str(personaldb_port)
        self._runtime_env_overrides["PERSONALDB_PORT"] = str(personaldb_port)
        self._runtime_env_overrides["OUTLINE_API_PORT"] = str(outline_port)
        self._runtime_env_overrides["CONTENT_API_PORT"] = str(content_port)
        self._runtime_env_overrides["MAIN_API_PORT"] = str(main_api_port)
        self._runtime_env_overrides["FRONTEND_PORT"] = str(self.frontend_port)

        # 对齐 URL 类变量（main_api 等服务会优先读取这些 URL）。
        self._runtime_env_overrides["PERSONAL_DB"] = f"http://{self.access_host}:{personaldb_port}"
        self._runtime_env_overrides["OUTLINE_API"] = f"http://{self.access_host}:{outline_port}"
        self._runtime_env_overrides["CONTENT_API"] = f"http://{self.access_host}:{content_port}"

    def setup_logging(self):
        """设置日志系统"""
        self.logs_dir.mkdir(exist_ok=True)

        log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(self.logs_dir / 'production.log', encoding='utf-8'),
            ]
        )
        self.logger = logging.getLogger('ProductionStarter')

    def _print(self, msg: str) -> None:
        print(msg, flush=True)
        self.logger.info(msg)

    def _print_warn(self, msg: str) -> None:
        print(f"[WARN] {msg}", flush=True)
        self.logger.warning(msg)

    def _print_error(self, msg: str) -> None:
        print(f"[ERROR] {msg}", flush=True)
        self.logger.error(msg)

    def print_banner(self):
        """打印启动横幅"""
        banner = f"""
{'='*80}
TeachDo 生产环境启动器
{'='*80}
启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
项目目录: {self.project_root}
绑定地址: {self.bind_host} (本机访问: {self.access_host})
日志目录: {self.logs_dir}
{'='*80}
        """
        print(banner)
        self.logger.info("启动生产环境部署")

    def check_environment(self):
        """检查环境依赖"""
        self._print("==> 检查环境依赖...")

        # 检查Python版本
        if sys.version_info < (3, 8):
            self._print_error("需要 Python 3.8 或更高版本")
            sys.exit(1)

        # 检查Node.js
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            self._print(f"Node.js 版本: {result.stdout.strip()}")
        except FileNotFoundError:
            self._print_error("未找到 Node.js，请先安装 Node.js")
            sys.exit(1)

        # 检查项目结构
        if not self.backend_dir.exists():
            self._print_error(f"后端目录不存在: {self.backend_dir}")
            sys.exit(1)

        if not self.frontend_dir.exists():
            self._print_error(f"前端目录不存在: {self.frontend_dir}")
            sys.exit(1)

        self._print("OK 环境检查通过")

    def _build_subprocess_env(self) -> Dict[str, str]:
        """
        为子进程构建运行环境：
        - 去掉代理变量（避免本机服务误走代理导致 502/超时）
        - 设置 PYTHONPATH 指向项目根目录（方便导入 backend/common）
        - 设置 PYTHONUNBUFFERED=1（重定向到文件时也能实时写入）
        """
        env = os.environ.copy()
        for k in (
            "http_proxy",
            "https_proxy",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "all_proxy",
            "ALL_PROXY",
            "no_proxy",
            "NO_PROXY",
        ):
            env.pop(k, None)

        existing_pp = env.get("PYTHONPATH") or ""
        root = str(self.project_root)
        env["PYTHONPATH"] = root if not existing_pp else f"{root}{os.pathsep}{existing_pp}"
        env["PYTHONUNBUFFERED"] = "1"

        # LiteLLM 默认会尝试从 GitHub 拉取模型价格/上下文窗口映射表，网络不通时会阻塞启动。
        # 这里默认强制使用包内置的本地备份（不覆盖用户显式配置）。
        env.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "true")

        # 确保子进程与启动器的 bind_host 一致，避免“端口检查通过但服务实际 bind 失败”的漂移。
        env["HOST"] = self.bind_host

        # 应用运行期覆盖（例如自动换端口）。
        if self._runtime_env_overrides:
            env.update(self._runtime_env_overrides)
        return env

    def _is_wsl(self) -> bool:
        if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
            return True
        try:
            with open("/proc/version", "r", encoding="utf-8", errors="ignore") as f:
                return "microsoft" in (f.read() or "").lower()
        except Exception:
            return False

    def _pick_bindable_tcp_port(self, host: str, start_port: int, *, max_tries: int = 200) -> Optional[int]:
        start_port = int(start_port)
        for p in range(start_port, start_port + max(1, int(max_tries))):
            ok, _ = check_tcp_port_bindable(host, p)
            if ok:
                return int(p)
        return None

    def _override_personal_db_port(self, new_port: int) -> None:
        new_port = int(new_port)
        if "personal_db" in self.services:
            self.services["personal_db"]["port"] = new_port
        self._sync_internal_service_env_overrides()

    def _maybe_autoswitch_personal_db_port(self, occupied: List[Tuple[str, int, str, Optional[int]]]) -> bool:
        """
        尝试在端口无法释放时自动为“知识库”服务换一个可用端口。

        典型场景：
        - WSL2 mirrored networking 下，Windows 宿主机占用 127.0.0.1:9100（JetDirect 打印端口等），
          WSL 内 lsof/ss 查不到进程但 bind 会失败。
        """
        import errno

        if "personal_db" not in self.services:
            return False

        current_port = int(self.services["personal_db"]["port"])
        hit = False
        for _host, port, name, err in occupied:
            if name != "知识库":
                continue
            if int(port) != current_port:
                continue
            if err not in {None, errno.EADDRINUSE}:
                continue
            hit = True
            break

        if not hit:
            return False

        base = 9101 if current_port == 9100 else current_port + 1
        new_port = self._pick_bindable_tcp_port(self.bind_host, base, max_tries=200)
        if new_port is None:
            return False

        self._print_warn(f"知识库端口 {current_port} 无法使用，自动切换到 {new_port}（仅本次启动生效）")
        if self._is_wsl():
            self._print_warn("检测到 WSL 环境：若 9100 由 Windows 宿主机占用，WSL 内可能无法定位/终止对应进程。")
        self._override_personal_db_port(new_port)
        return True

    def _run_command(
        self,
        cmd: List[str],
        *,
        cwd: Optional[Path] = None,
        log_file: Optional[Path] = None,
        verbose: bool = False,
        env: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        运行命令，并将 stdout/stderr 写入 log_file。
        - verbose=True 时，会同时把输出实时打印到控制台（主窗口仍尽量保持简洁，仅用于依赖安装）。
        """
        if log_file is None:
            result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=False, env=env)
            return int(result.returncode)

        log_file.parent.mkdir(exist_ok=True)
        with open(log_file, "w", encoding="utf-8", errors="ignore", buffering=1) as f:
            f.write(f"# CMD: {' '.join(cmd)}\n")
            f.write(f"# CWD: {cwd or Path.cwd()}\n")
            f.write(f"# TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.flush()

            if not verbose:
                result = subprocess.run(
                    cmd,
                    cwd=str(cwd) if cwd else None,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                    env=env,
                )
                return int(result.returncode)

            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd) if cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                f.write(line)
                print(line, end="", flush=True)
            return int(proc.wait())

    def install_dependencies(self):
        """安装依赖"""
        if self.no_install:
            self._print("==> 跳过依赖安装（--no-install）")
            return

        self._print("==> 安装项目依赖（输出写入 logs/install_*.log）...")

        env = self._build_subprocess_env()

        # 安装后端依赖
        requirements_file = self.backend_dir / "requirements.txt"
        if requirements_file.exists():
            self._print("==> 安装 Python 依赖...")
            python_log = self.logs_dir / "install_python.log"
            rc = self._run_command(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(requirements_file),
                    "-i",
                    "https://mirrors.aliyun.com/pypi/simple/",
                ],
                log_file=python_log,
                verbose=self.verbose_install,
                env=env,
            )
            if rc != 0:
                self._print_error(f"Python 依赖安装失败（exit={rc}），请查看: {python_log}")
                for line in _tail_last_lines(python_log, max_lines=80):
                    print(line)
                sys.exit(1)

        # 安装前端依赖
        package_json = self.frontend_dir / "package.json"
        if package_json.exists():
            self._print("==> 安装前端依赖...")
            frontend_log = self.logs_dir / "install_frontend.log"
            rc = self._run_command(
                ["npm", "install"],
                cwd=self.frontend_dir,
                log_file=frontend_log,
                verbose=self.verbose_install,
                env=env,
            )
            if rc != 0:
                self._print_error(f"前端依赖安装失败（exit={rc}），请查看: {frontend_log}")
                for line in _tail_last_lines(frontend_log, max_lines=80):
                    print(line)
                sys.exit(1)

        self._print("OK 依赖安装完成")

    def build_frontend(self):
        """构建前端"""
        self.logger.info("构建前端项目...")

        try:
            # 清理旧的构建文件
            if self.dist_dir.exists():
                shutil.rmtree(self.dist_dir)

            # 执行构建
            result = subprocess.run(
                ['npm', 'run', 'build'],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                check=True
            )

            if not self.dist_dir.exists():
                raise Exception("构建完成但未找到dist目录")

            self.logger.info("前端构建完成")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"前端构建失败: {e}")
            self.logger.error(f"错误输出: {e.stderr}")
            sys.exit(1)

    def check_ports(self):
        """检查端口占用"""
        import errno

        def _occupied_targets() -> List[Tuple[str, int, str, Optional[int]]]:
            occupied: List[Tuple[str, int, str, Optional[int]]] = []
            # 后端服务：使用 self.bind_host（实际启动时也会用它绑定）
            for config in self.services.values():
                host = self.bind_host
                port = int(config["port"])
                name = str(config.get("name", ""))
                ok, err = check_tcp_port_bindable(host, port)
                if ok:
                    continue
                occupied.append((host, port, name, err))

            # 前端：固定用 127.0.0.1 启动（vite dev），不要用 access_host 误判
            ok, err = check_tcp_port_bindable(self.frontend_host, int(self.frontend_port))
            if not ok:
                occupied.append((self.frontend_host, int(self.frontend_port), "前端", err))
            return occupied

        occupied = _occupied_targets()
        occupied_ports = sorted({p for _h, p, _n, _e in occupied})

        # 绑定地址不可用/权限不足：属于配置或环境问题，提前失败并给出清晰提示。
        bind_errors = [(h, p, n, e) for (h, p, n, e) in occupied if e in {errno.EADDRNOTAVAIL, errno.EACCES}]
        if bind_errors:
            for host, port, name, err in bind_errors:
                if err == errno.EACCES:
                    self._print_error(f"{name} 无权限监听 {host}:{port}（EACCES）")
                else:
                    self._print_error(f"{name} 绑定地址不可用：{host}:{port}（EADDRNOTAVAIL）")
            sys.exit(1)

        if occupied_ports:
            self._print_warn(f"发现端口占用: {occupied_ports}，尝试清理占用端口")
            killed = self.kill_processes_on_ports(occupied_ports)
            still_occupied = _occupied_targets()
            still_ports = sorted({p for _h, p, _n, _e in still_occupied})
            if still_ports:
                # 兜底：部分环境（尤其 WSL mirrored networking）端口会被宿主机占用，WSL 内无法定位 PID。
                # 对知识库端口进行自动换端口，提升“开箱可启动”的体验。
                if self._maybe_autoswitch_personal_db_port(still_occupied):
                    still_occupied = _occupied_targets()
                    still_ports = sorted({p for _h, p, _n, _e in still_occupied})
                    if not still_ports:
                        return

                self._print_error(f"端口仍被占用: {still_ports}（已尝试终止 {killed} 个进程）")
                for host, port, name, err in still_occupied:
                    if err == errno.EADDRINUSE:
                        self._print_error(f"{name} 需要监听 {host}:{port}，但端口仍被占用")
                for port in still_ports:
                    self._print_error(
                        f"请手动释放端口 {port}，例如：`lsof -nP -iTCP:{port} -sTCP:LISTEN` 或 `fuser -n tcp {port}`"
                    )
                    if self._is_wsl():
                        self._print_error(
                            f"你在 WSL 环境下，若以上命令查不到 PID，可能是 Windows 宿主机占用端口 {port}。"
                        )
                sys.exit(1)

    def kill_processes_on_ports(self, ports: List[int]):
        """清理占用端口的进程"""
        def _pid_exists(pid: int) -> bool:
            try:
                os.kill(int(pid), 0)
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
            except Exception:
                return True
            return True

        def _terminate_pid(pid: int) -> bool:
            pid = int(pid)
            if pid <= 1 or pid == os.getpid():
                return False

            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                return True
            except PermissionError:
                return False
            except Exception:
                return False

            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                if not _pid_exists(pid):
                    return True
                time.sleep(0.1)

            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                return True
            except Exception:
                return False

            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                if not _pid_exists(pid):
                    return True
                time.sleep(0.1)
            return not _pid_exists(pid)

        killed_count = 0
        for port in ports:
            port = int(port)
            pids = sorted(find_listening_pids_on_tcp_port(port))
            if not pids:
                self._print_warn(
                    f"无法定位占用端口 {port} 的监听进程（可能由宿主机占用/非 LISTEN 状态/权限或工具限制）"
                )
                continue

            self._print_warn(f"端口 {port} 占用进程: {', '.join(str(p) for p in pids)}，尝试终止")
            for pid in pids:
                if _terminate_pid(pid):
                    killed_count += 1

            # 给 OS 一点时间释放端口
            time.sleep(0.2)

        self.logger.info(f"清理完成，终止了 {killed_count} 个进程")
        time.sleep(0.5)
        return killed_count

    def start_backend_service(self, service_name: str, config: Dict) -> Optional[subprocess.Popen]:
        """启动后端服务"""
        runtime = self._spawn_backend_service_process(service_name, config)
        if not runtime:
            return None

        ok = self._wait_for_backend_services_ready({service_name: runtime})
        if not ok:
            return None
        return runtime["process"]

    def _spawn_backend_service_process(self, service_name: str, config: Dict) -> Optional[Dict]:
        service_dir = config["dir"]
        script = config["script"]
        port = int(config["port"])
        name = config["name"]
        ready_path = config.get("ready_path", "/healthz")

        self._print(f"==> 启动 {name} (端口: {port}) ...")

        try:
            log_file = self.logs_dir / f"{service_name}.log"
            # 每次启动都截断旧日志，避免“上次启动的日志”干扰本次排查。
            log_f = open(log_file, "w", encoding="utf-8", buffering=1)
            self._log_file_handles[service_name] = log_f

            env = self._build_subprocess_env()
            args = config.get("args") or []

            process = subprocess.Popen(
                [sys.executable, "-u", script, *args],
                cwd=service_dir,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )

            ready_url = f"http://{self.access_host}:{port}{ready_path}"
            timeout_s = int(self.user_timeout_s) if self.user_timeout_s is not None else int(config.get("default_timeout_s", 180))
            deadline = time.monotonic() + max(1, int(timeout_s))

            return {
                "service_name": service_name,
                "name": name,
                "port": port,
                "process": process,
                "log_file": log_file,
                "ready_url": ready_url,
                "display_url": f"http://{self.access_host}:{port}",
                "timeout_s": timeout_s,
                "deadline": deadline,
            }
        except Exception as e:
            self._print_error(f"启动 {name} 时出错: {e}")
            return None

    def _spawn_frontend_process(self) -> Optional[Dict]:
        """
        启动前端进程（不在这里等待就绪）。

        统一返回 runtime 结构，便于在串行/并行模式下复用同一套 readiness 逻辑。
        """
        self._print(f"==> 启动前端服务 (端口: {self.frontend_port}) ...")
        try:
            log_file = self.logs_dir / "frontend.log"
            log_f = open(log_file, "w", encoding="utf-8", buffering=1)
            self._log_file_handles["frontend"] = log_f

            env = self._build_subprocess_env()

            process = subprocess.Popen(
                [
                    "npm",
                    "run",
                    "dev",
                    "--",
                    "--host",
                    self.frontend_host,
                    "--port",
                    str(self.frontend_port),
                    "--strictPort",
                ],
                cwd=self.frontend_dir,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )

            ready_url = f"http://{self.frontend_host}:{self.frontend_port}/"
            timeout_s = int(self.user_timeout_s) if self.user_timeout_s is not None else 180
            deadline = time.monotonic() + max(1, int(timeout_s))

            return {
                "service_name": "frontend",
                "name": "前端",
                "port": self.frontend_port,
                "process": process,
                "log_file": log_file,
                "ready_url": ready_url,
                "display_url": f"http://{self.frontend_host}:{self.frontend_port}",
                "timeout_s": timeout_s,
                "deadline": deadline,
            }
        except Exception as e:
            self._print_error(f"启动前端时出错: {e}")
            return None

    def _terminate_process(self, process: subprocess.Popen) -> None:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception:
            pass

    def _print_service_fail_tail(self, log_file: Path) -> None:
        tail = _tail_last_lines(log_file, max_lines=80)
        if tail:
            for line in tail:
                print(line)
        else:
            print("（日志暂无输出：可能仍卡在 import/初始化阶段，或进程启动即异常退出）", flush=True)

    def _wait_for_backend_services_ready(self, runtimes: Dict[str, Dict]) -> bool:
        """
        等待一组后端服务就绪。

        设计目的：
        - 支持“同层级服务并行启动”（例如 outline/content），减少总等待时间
        - readiness 仍以 /healthz 返回 200 为准，避免误判
        """

        pending: Dict[str, Dict] = dict(runtimes)
        poll_interval_s = 0.6

        while pending:
            now = time.monotonic()
            for service_name, runtime in list(pending.items()):
                process: subprocess.Popen = runtime["process"]
                name: str = runtime["name"]
                port: int = runtime["port"]
                log_file: Path = runtime["log_file"]
                ready_url: str = runtime["ready_url"]
                display_url: str = runtime.get("display_url") or f"http://{self.access_host}:{port}"
                timeout_s: int = runtime["timeout_s"]
                deadline: float = runtime["deadline"]

                if process.poll() is not None:
                    self._print_error(f"{name} 进程已退出（exit={process.returncode}），查看日志: {log_file}")
                    self._print_service_fail_tail(log_file)
                    return False

                if now >= deadline:
                    self._print_error(f"{name} 未在 {timeout_s}s 内就绪，查看日志: {log_file}")
                    self._print_service_fail_tail(log_file)
                    # 超时：避免遗留孤儿进程（其余服务由 stop_all_services 统一处理）
                    self._terminate_process(process)
                    return False

                if _http_get_status(ready_url, timeout_s=2.0) == 200:
                    self._print(f"OK {name} 已就绪: {display_url}")
                    self.logger.info(f"{name} 就绪 (PID: {process.pid})")
                    pending.pop(service_name, None)

            time.sleep(poll_interval_s)

        return True

    def start_frontend_server(self):
        """启动前端静态文件服务（开发：vite dev）并等待就绪。"""
        runtime = self._spawn_frontend_process()
        if not runtime:
            return None

        ok = self._wait_for_backend_services_ready({"frontend": runtime})
        if not ok:
            return None
        return runtime["process"]

    def start_all_services(self):
        """启动所有服务"""
        if self.parallel_start:
            self._print("==> 启动所有服务（并行启动进程，等待真实就绪）...")
        else:
            self._print("==> 启动所有服务（按依赖顺序等待就绪）...")

        # 后端依赖关系：
        # - personal_db 必须最先就绪（content 的知识库工具会访问它）
        # - outline 与 content 彼此无硬依赖，可并行启动以减少总等待时间
        # - main_api 依赖 outline + content
        if self.parallel_start:
            runtimes: Dict[str, Dict] = {}
            for service_name in ["personal_db", "outline", "content", "main_api"]:
                config = self.services[service_name]
                runtime = self._spawn_backend_service_process(service_name, config)
                if not runtime:
                    self._print_error(f"服务 {config['name']} 启动失败，正在停止所有服务...")
                    self.stop_all_services()
                    sys.exit(1)
                self.processes[service_name] = runtime["process"]
                runtimes[service_name] = runtime

            frontend_runtime = self._spawn_frontend_process()
            if not frontend_runtime:
                self._print_error("前端启动失败，正在停止所有服务...")
                self.stop_all_services()
                sys.exit(1)
            self.processes["frontend"] = frontend_runtime["process"]
            runtimes["frontend"] = frontend_runtime

            ok = self._wait_for_backend_services_ready(runtimes)
            if not ok:
                self._print_error("服务启动失败，正在停止所有服务...")
                self.stop_all_services()
                sys.exit(1)

            self.show_service_status()
            return

        backend_groups: List[List[str]] = [
            ["personal_db"],
            ["outline", "content"],
            ["main_api"],
        ]

        for group in backend_groups:
            runtimes: Dict[str, Dict] = {}
            for service_name in group:
                config = self.services[service_name]
                runtime = self._spawn_backend_service_process(service_name, config)
                if not runtime:
                    self._print_error(f"服务 {config['name']} 启动失败，正在停止所有服务...")
                    self.stop_all_services()
                    sys.exit(1)

                process: subprocess.Popen = runtime["process"]
                self.processes[service_name] = process
                runtimes[service_name] = runtime

            ok = self._wait_for_backend_services_ready(runtimes)
            if not ok:
                failed_names = "、".join(self.services[name]["name"] for name in group)
                self._print_error(f"服务组启动失败（{failed_names}），正在停止所有服务...")
                self.stop_all_services()
                sys.exit(1)

        # 启动前端服务
        process = self.start_frontend_server()
        if process:
            self.processes["frontend"] = process
        else:
            self._print_error("前端启动失败，正在停止所有服务...")
            self.stop_all_services()
            sys.exit(1)

        # 显示服务状态
        self.show_service_status()

    def show_service_status(self):
        """显示服务状态"""
        print("\n" + "="*80)
        print("所有服务已就绪")
        print("="*80)
        print("服务状态:")

        for service_name, config in self.services.items():
            if service_name in self.processes:
                print(f"  - {config['name']}: http://{self.access_host}:{config['port']}")

        print(f"  - 前端界面: http://{self.frontend_host}:{self.frontend_port}")
        print(f"  - 日志目录: {self.logs_dir}")

        print("\n使用说明:")
        print("  - 按 Ctrl+C 停止所有服务，请耐心等待 5 秒让子进程退出")
        print("  - 在浏览器中访问前端界面开始使用")
        print("  - 主窗口默认不跟随服务日志；实时日志请另开终端执行：python start.py --tail")
        print("="*80)

    def monitor_services(self):
        """监控服务状态"""
        try:
            while self.processes:
                for service_name, process in list(self.processes.items()):
                    exit_code = process.poll()
                    if exit_code is not None:
                        log_file = self.logs_dir / (f"{service_name}.log" if service_name != "frontend" else "frontend.log")
                        display_name = self.services.get(service_name, {}).get("name") if service_name in self.services else "前端"
                        self._print_warn(f"服务已停止: {display_name} ({service_name}) exit={exit_code}，日志: {log_file}")

                        # 关闭对应日志文件句柄（避免长时间运行时泄漏）
                        f = self._log_file_handles.pop(service_name, None)
                        if f:
                            try:
                                f.close()
                            except Exception:
                                pass

                        del self.processes[service_name]
                time.sleep(5)
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在关闭所有服务...")
            self.stop_all_services()

    def stop_all_services(self):
        """停止所有服务"""
        self.logger.info("停止所有服务...")

        # 停止后端/前端服务
        for service_name, process in list(self.processes.items()):
            try:
                self.logger.info(f"停止服务: {service_name}")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning(f"强制终止服务: {service_name}")
                process.kill()
            except Exception as e:
                self.logger.error(f"停止服务 {service_name} 时出错: {e}")

        self.processes.clear()

        # 关闭父进程持有的日志文件句柄
        for f in list(self._log_file_handles.values()):
            try:
                f.close()
            except Exception:
                pass
        self._log_file_handles.clear()

        self.logger.info("所有服务已停止")

    def run(self):
        """主运行函数"""
        self.setup_logging()
        self.print_banner()

        # 环境检查
        self.check_environment()

        # 安装依赖
        self.install_dependencies()

        # 构建前端（如生产需要）
        # self.build_frontend()

        # 检查端口
        self.check_ports()

        # 启动所有服务（逐个等待就绪）
        self.start_all_services()

        # 监控服务
        self.monitor_services()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TeachDo 一键启动脚本（主窗口干净启动，副窗口 tail 日志）")
    parser.add_argument("--tail", action="store_true", help="只做日志聚合跟随（不安装/不启动服务）")
    parser.add_argument("--tail-all", action="store_true", help="--tail 时包含 install_*.log")
    parser.add_argument("--no-install", action="store_true", help="跳过依赖安装（仅启动服务）")
    parser.add_argument("--parallel", action="store_true", help="并行启动所有服务进程（可能更快，但会增加磁盘/CPU 竞争）")
    parser.add_argument("--timeout", type=int, default=None, help="等待服务就绪超时秒数（默认：服务级别 180/600）")
    parser.add_argument(
        "--verbose-install",
        action="store_true",
        help="安装依赖时将输出实时打印到控制台（仍会写入 logs/install_*.log）",
    )
    args = parser.parse_args()

    if args.tail:
        logs_dir = Path(__file__).parent / "logs"
        exclude = [] if args.tail_all else ["install_*.log"]
        tailer = MultiLogTailer(logs_dir, pattern="*.log", poll_interval=1.0, color=True, exclude_globs=exclude)
        print("\n" + "=" * 80)
        print("实时日志聚合（相当于 tail -f logs/*.log）")
        print("   - 每行格式：YYYY-mm-dd HH:MM:SS [文件名] 日志内容")
        if exclude:
            print(f"   - 已默认排除：{', '.join(exclude)}（可用 --tail-all 包含）")
        print("=" * 80 + "\n")
        tailer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n用户中断，停止日志跟随")
            tailer.stop()
        return

    starter = ProductionStarter(
        no_install=args.no_install,
        verbose_install=args.verbose_install,
        timeout_s=args.timeout,
        parallel_start=args.parallel,
    )

    # 注册信号处理器
    def signal_handler(signum, frame):
        print("\n收到信号，正在停止服务...")
        starter.stop_all_services()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        starter.run()
    except KeyboardInterrupt:
        print("\n用户中断")
        starter.stop_all_services()
    except Exception as e:
        print(f"[ERROR] 启动失败: {e}")
        starter.stop_all_services()
        sys.exit(1)

if __name__ == "__main__":
    main()
