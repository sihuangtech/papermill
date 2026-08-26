"""系统进程与环境诊断接口。"""

from fastapi import APIRouter

from backend.api.dependencies import ProcessManagerDep, RuntimeDep
from backend.doctor import diagnose

router = APIRouter(tags=["system"])


@router.get("/system/status")
def status(manager: ProcessManagerDep, runtime: RuntimeDep) -> dict:
    return {
        "status": manager.status,
        "pid": manager.pid,
        "runtime": runtime.context.public_dict(),
    }


@router.post("/system/start")
def start(manager: ProcessManagerDep) -> dict:
    pid = manager.start()
    return {"message": "持续科研调度已启动", "pid": pid}


@router.post("/system/stop")
def stop(manager: ProcessManagerDep) -> dict:
    manager.stop()
    return {"message": "持续科研调度已停止"}


@router.get("/system/doctor")
def doctor(runtime: RuntimeDep) -> dict:
    return diagnose(runtime.config, runtime.context)
