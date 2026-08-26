"""使用 PyInstaller 构建符合 Tauri target-triple 命名规则的 Python sidecar。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARIES = ROOT / "src-tauri" / "binaries"


def _target_triple() -> str:
    output = subprocess.check_output(["rustc", "-Vv"], text=True)
    for line in output.splitlines():
        if line.startswith("host: "):
            return line.removeprefix("host: ").strip()
    raise RuntimeError("rustc -Vv 没有返回 host target triple")


def _sources() -> list[Path]:
    return [
        *ROOT.joinpath("backend").rglob("*.py"),
        Path(__file__).resolve(),
        ROOT / "config.yaml",
        ROOT / "prompts.yaml",
        ROOT / "pyproject.toml",
    ]


def _is_current(output: Path) -> bool:
    if not output.exists() or os.getenv("PAPERMILL_FORCE_SIDECAR") == "1":
        return False
    built_at = output.stat().st_mtime
    return all(path.stat().st_mtime <= built_at for path in _sources())


def main() -> int:
    triple = _target_triple()
    suffix = ".exe" if sys.platform == "win32" else ""
    name = f"papermill-backend-{triple}"
    output = BINARIES / f"{name}{suffix}"
    if _is_current(output):
        print(f"桌面 sidecar 已是最新版本: {output}")
        return 0

    BINARIES.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        name,
        "--distpath",
        str(BINARIES),
        "--workpath",
        str(ROOT / "build" / "pyinstaller" / "work"),
        "--specpath",
        str(ROOT / "build" / "pyinstaller" / "spec"),
        "--paths",
        str(ROOT),
        "--add-data",
        f"{ROOT / 'config.yaml'}:.",
        "--add-data",
        f"{ROOT / 'prompts.yaml'}:.",
        "--hidden-import",
        "backend.cli",
        "--hidden-import",
        "ipykernel_launcher",
        "--hidden-import",
        "jupyter_client.provisioning.local_provisioner",
        "--collect-all",
        "agents",
        "--collect-all",
        "dbos",
        "--collect-all",
        "litellm",
        "--collect-all",
        "papermill",
        "--recursive-copy-metadata",
        "openai-agents",
        "--recursive-copy-metadata",
        "dbos",
        "--recursive-copy-metadata",
        "litellm",
        "--copy-metadata",
        "sk-agentic-research",
        "--copy-metadata",
        "jupyter_client",
        "--exclude-module",
        "debugpy",
        str(ROOT / "backend" / "desktop.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    output.chmod(output.stat().st_mode | 0o111)
    print(f"已生成 Tauri sidecar: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
