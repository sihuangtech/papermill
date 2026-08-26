"""模型供应商密钥与 Base URL 配置接口。"""

from typing import Literal

from fastapi import APIRouter, HTTPException

from backend.api.dependencies import ProcessManagerDep, RuntimeDep
from backend.api.schemas import ProviderCredentialUpdate
from backend.core.provider_settings import ProviderSettingsStore
from backend.core.runtime import RuntimeMode

router = APIRouter(tags=["providers"])
store = ProviderSettingsStore()


@router.get("/providers")
def list_providers() -> list[dict]:
    return store.list_sanitized()


@router.put("/providers/{provider}")
def update_provider(
    provider: Literal["openai", "anthropic", "google"],
    payload: ProviderCredentialUpdate,
    manager: ProcessManagerDep,
    runtime: RuntimeDep,
) -> dict:
    if runtime.context.mode is RuntimeMode.CLOUD:
        raise HTTPException(status_code=403, detail="云端模型凭据由服务器环境变量管理")
    try:
        result = store.update(
            provider,
            payload.api_key,
            payload.base_url,
            payload.model_id,
            payload.api_mode,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    restarted = manager.status == "running"
    if restarted:
        manager.restart()
    return {"provider": result, "restarted": restarted}
