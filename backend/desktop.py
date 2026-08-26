"""Tauri 桌面应用使用的 FastAPI sidecar 入口。"""

from __future__ import annotations

import argparse
import multiprocessing
import os
import runpy
import shutil
import sys
import threading
import time
from pathlib import Path

import psutil


def _run_embedded_python() -> int | None:
    """让冻结后的 sidecar 继续承担实验脚本和 Python 模块执行。"""
    if len(sys.argv) >= 3 and sys.argv[1] == "__run_python__":
        script, *arguments = sys.argv[2:]
        sys.argv = [script, *arguments]
        runpy.run_path(script, run_name="__main__")
        return 0
    if len(sys.argv) >= 3 and sys.argv[1] == "__run_module__":
        module, *arguments = sys.argv[2:]
        sys.argv = [module, *arguments]
        runpy.run_module(module, run_name="__main__", alter_sys=True)
        return 0
    return None


def _bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def _prepare_data_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    source_root = _bundle_root()
    for filename in ("config.yaml", "prompts.yaml"):
        target = data_dir / filename
        if not target.exists():
            shutil.copy2(source_root / filename, target)
    os.chdir(data_dir)


def _stop_with_parent(parent_pid: int) -> None:
    while True:
        if not psutil.pid_exists(parent_pid):
            current = psutil.Process()
            descendants = current.children(recursive=True)
            for process in descendants:
                process.terminate()
            psutil.wait_procs(descendants, timeout=3)
            os._exit(0)
        time.sleep(1)


def _write_embedded_kernel_spec(data_dir: Path) -> None:
    """使 Notebook 在安装后的桌面包内仍能启动内嵌 Python kernel。"""
    import json

    kernel_dir = data_dir / "jupyter" / "kernels" / "papermill-desktop"
    kernel_dir.mkdir(parents=True, exist_ok=True)
    kernel = {
        "argv": [
            sys.executable,
            "__run_module__",
            "ipykernel_launcher",
            "-f",
            "{connection_file}",
        ],
        "display_name": "Agentic Research Desktop Python",
        "language": "python",
    }
    (kernel_dir / "kernel.json").write_text(
        json.dumps(kernel, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.environ["JUPYTER_PATH"] = str(data_dir / "jupyter")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agentic Research desktop sidecar")
    subparsers = parser.add_subparsers(dest="command", required=True)
    serve = subparsers.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", required=True, type=int)
    serve.add_argument("--data-dir", required=True, type=Path)
    serve.add_argument("--token", required=True)
    serve.add_argument("--parent-pid", required=True, type=int)
    return parser


def main() -> int:
    multiprocessing.freeze_support()
    embedded_result = _run_embedded_python()
    if embedded_result is not None:
        return embedded_result

    args = _parser().parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    _prepare_data_dir(data_dir)
    _write_embedded_kernel_spec(data_dir)
    os.environ["PAPERMILL_DESKTOP_MODE"] = "1"
    os.environ["AGENTIC_RUNTIME_MODE"] = "desktop"
    os.environ["PAPERMILL_DESKTOP_TOKEN"] = args.token
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", str(data_dir / "matplotlib"))
    threading.Thread(target=_stop_with_parent, args=(args.parent_pid,), daemon=True).start()

    import uvicorn

    from backend.api.webapp import create_app

    # SSE 的查询令牌不应出现在 access log 中。
    uvicorn.run(
        create_app(enable_durable=True),
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
