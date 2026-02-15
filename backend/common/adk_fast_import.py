"""
google-adk 冷启动导入加速工具。

背景
----
google-adk 的部分子包（artifacts/sessions/memory/tools）在 `__init__.py` 里
无条件导入了 GCS/Vertex/OpenAPI 等“可选能力”的实现，进而触发 `google-cloud-*`
等庞大依赖的导入。

在 WSL + /mnt/* 目录下，这类重型导入可能耗时数分钟，导致服务启动和健康探针超时。

本项目实际只使用这些子包里的 in-memory 实现和基础接口，因此可以通过“预先注入
stub package”的方式跳过 `__init__.py`，显著降低冷启动时间。

注意：必须在首次 `import google.adk` 之前调用才有效。
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
import types
from pathlib import Path
from typing import Iterable


_DEFAULT_STUB_SUBPACKAGES: tuple[str, ...] = (
    # 这些包的 __init__.py 会导入 GCS/Vertex/OpenAPI 等可选能力，代价很高。
    "artifacts",
    "sessions",
    "memory",
    "tools",
    # 该包的 __init__.py 会尝试导入 VertexAiCodeExecutor（若安装了 vertexai 则会成功），
    # 进而触发 google-cloud-aiplatform 的重型导入。
    "code_executors",
    # 该包的 __init__.py 会尝试导入 VertexAiExampleStore（若安装了 vertexai 则会成功），
    # 同样会触发 google-cloud-aiplatform 的重型导入。
    "examples",
)


def _install_stub_package(fullname: str, package_dir: Path) -> None:
    """在 sys.modules 注入一个“空 package”，仅提供 __path__ 用于子模块解析。"""

    if fullname in sys.modules:
        return
    if not package_dir.is_dir():
        return

    mod = types.ModuleType(fullname)
    mod.__file__ = str(package_dir / "__init__.py")
    mod.__package__ = fullname
    mod.__path__ = [str(package_dir)]

    spec = importlib.machinery.ModuleSpec(fullname, loader=None, is_package=True)
    spec.submodule_search_locations = [str(package_dir)]
    mod.__spec__ = spec

    sys.modules[fullname] = mod


def patch_google_adk_imports(*, stub_subpackages: Iterable[str] | None = None) -> None:
    """
    预注入 stub package，跳过 google-adk 某些子包的 `__init__.py` 执行。

    这可以避免在导入 Runner/LlmAgent 等核心对象时，间接把 `google-cloud-aiplatform`,
    `google-cloud-storage` 等重型依赖也一并导入，从而让服务更快进入可用状态。
    """

    # 若 google.adk 已经被导入，说明 heavy import 可能已经发生；此时再 patch 意义不大。
    # 仍然允许继续注入 stub，以避免后续 import 触发更多副作用。
    spec = importlib.util.find_spec("google.adk")
    if spec is None or not spec.origin:
        return

    adk_root = Path(spec.origin).resolve().parent
    wanted = tuple(stub_subpackages) if stub_subpackages is not None else _DEFAULT_STUB_SUBPACKAGES

    for sub in wanted:
        sub = str(sub).strip()
        if not sub:
            continue
        _install_stub_package(f"google.adk.{sub}", adk_root / sub)
