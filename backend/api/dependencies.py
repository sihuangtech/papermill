"""API 依赖和运行时缓存。"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from backend.api.process_manager import OrchestratorProcess
from backend.workflow.durable import DurableDispatcher, dispatcher
from backend.workflow.factory import Runtime, build_runtime


@lru_cache(maxsize=1)
def get_runtime() -> Runtime:
    return build_runtime()


def refresh_runtime() -> Runtime:
    get_runtime.cache_clear()
    return get_runtime()


@lru_cache(maxsize=1)
def get_process_manager() -> OrchestratorProcess:
    return OrchestratorProcess()


def get_dispatcher() -> DurableDispatcher:
    return dispatcher


RuntimeDep = Annotated[Runtime, Depends(get_runtime)]
ProcessManagerDep = Annotated[OrchestratorProcess, Depends(get_process_manager)]
DispatcherDep = Annotated[DurableDispatcher, Depends(get_dispatcher)]
