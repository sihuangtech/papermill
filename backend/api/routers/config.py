"""经过完整模型校验的配置读写接口。"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from backend.api.dependencies import ProcessManagerDep, RuntimeDep, refresh_runtime
from backend.core.config import AppConfig, save_config
from backend.core.runtime import RuntimeMode

router = APIRouter(tags=["config"])


@router.get("/config")
def get_config(runtime: RuntimeDep) -> dict:
    return runtime.config.model_dump(mode="json")


@router.put("/config")
def update_config(
    payload: dict[str, Any],
    runtime: RuntimeDep,
    manager: ProcessManagerDep,
) -> dict:
    if runtime.context.mode is RuntimeMode.CLOUD:
        raise HTTPException(status_code=403, detail="云端工作流配置由服务器管理员管理")
    merged = _deep_merge(runtime.config.model_dump(mode="json"), payload)
    try:
        config = AppConfig.model_validate(merged)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors()) from error
    was_running = manager.status == "running"
    save_config(config)
    refresh_runtime()
    if was_running:
        manager.restart()
    return {
        "message": "配置已保存并生效",
        "restarted": was_running,
        "config": config.model_dump(mode="json"),
    }


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
