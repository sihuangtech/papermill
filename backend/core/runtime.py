"""描述当前进程的部署边界，供云端与桌面端共享同一套业务核心。"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path


class RuntimeMode(str, Enum):
    CLOUD = "cloud"
    DESKTOP = "desktop"


@dataclass(frozen=True)
class RuntimeContext:
    mode: RuntimeMode
    compute_location: str
    storage_location: str
    provider_settings_mutable: bool
    durable_database_url: str

    def public_dict(self) -> dict[str, str | bool]:
        """返回不包含数据库口令的前端运行信息。"""
        payload = asdict(self)
        payload["mode"] = self.mode.value
        payload["durable_backend"] = (
            "postgresql" if self.durable_database_url.startswith("postgresql") else "sqlite"
        )
        payload.pop("durable_database_url")
        return payload


def build_runtime_context(workspace_dir: str | Path) -> RuntimeContext:
    """桌面 sidecar 自动识别；普通 ASGI 进程按云端服务器运行。"""
    configured = os.getenv("AGENTIC_RUNTIME_MODE", "").strip().lower()
    desktop_sidecar = os.getenv("PAPERMILL_DESKTOP_MODE") == "1"
    if configured and configured not in {item.value for item in RuntimeMode}:
        raise RuntimeError("AGENTIC_RUNTIME_MODE 必须是 cloud 或 desktop")
    mode = RuntimeMode.DESKTOP if desktop_sidecar else RuntimeMode(configured or "cloud")

    workspace = Path(workspace_dir).resolve()
    database_url = os.getenv("DBOS_SYSTEM_DATABASE_URL", "").strip()
    if not database_url:
        # SQLite 文件随工作区移动：桌面版留在设备上，单机云部署留在服务器上。
        database_url = f"sqlite:///{workspace / 'cache' / 'durable-workflows.sqlite'}"

    return RuntimeContext(
        mode=mode,
        compute_location="local_device" if mode is RuntimeMode.DESKTOP else "server",
        storage_location="local_device" if mode is RuntimeMode.DESKTOP else "server",
        provider_settings_mutable=mode is RuntimeMode.DESKTOP,
        durable_database_url=database_url,
    )
