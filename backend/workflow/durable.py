"""用 DBOS 承接长任务；领域状态仍由可审计的 ResearchRun 保存。"""

from __future__ import annotations

import threading
import uuid
from importlib.metadata import version
from typing import Any

from dbos import DBOS, DBOSConfig, SetWorkflowID

from backend.core.runtime import RuntimeContext


@DBOS.step(name="research-direction", retries_allowed=True, max_attempts=3)
def _run_direction_step(direction: str, max_ideas: int | None, batch_id: str) -> list[dict[str, Any]]:
    from backend.workflow.factory import build_runtime

    runtime = build_runtime()
    runs = runtime.engine.run_direction(direction, max_ideas, batch_id=batch_id)
    return [item.model_dump(mode="json") for item in runs]


@DBOS.workflow(name="research-direction-workflow")
def _run_direction_workflow(
    direction: str,
    max_ideas: int | None,
    batch_id: str,
) -> list[dict[str, Any]]:
    return _run_direction_step(direction, max_ideas, batch_id)


@DBOS.step(name="resume-research-run", retries_allowed=True, max_attempts=3)
def _resume_step(run_id: str) -> dict[str, Any]:
    from backend.workflow.factory import build_runtime

    return build_runtime().engine.execute(run_id).model_dump(mode="json")


@DBOS.workflow(name="resume-research-run-workflow")
def _resume_workflow(run_id: str) -> dict[str, Any]:
    return _resume_step(run_id)


@DBOS.step(name="approve-research-run", retries_allowed=True, max_attempts=3)
def _approve_step(run_id: str, reviewer: str) -> dict[str, Any]:
    from backend.workflow.factory import build_runtime

    return build_runtime().engine.approve(run_id, reviewer).model_dump(mode="json")


@DBOS.workflow(name="approve-research-run-workflow")
def _approve_workflow(run_id: str, reviewer: str) -> dict[str, Any]:
    return _approve_step(run_id, reviewer)


class DurableDispatcher:
    """DBOS 单例的窄接口，避免路由和业务服务感知具体调度框架。"""

    def __init__(self) -> None:
        self._configured = False
        self._launched = False
        self._lock = threading.RLock()

    @property
    def ready(self) -> bool:
        return self._launched

    def configure(self, context: RuntimeContext) -> None:
        with self._lock:
            if self._configured:
                return
            config: DBOSConfig = {
                "name": "sk-agentic-research",
                "application_version": version("sk-agentic-research"),
                "system_database_url": context.durable_database_url,
            }
            DBOS(config=config)
            self._configured = True

    def launch(self) -> None:
        with self._lock:
            if not self._launched:
                DBOS.launch()
                self._launched = True

    def shutdown(self) -> None:
        with self._lock:
            if self._configured:
                DBOS.destroy()
            self._configured = False
            self._launched = False

    def submit_direction(self, direction: str, max_ideas: int | None) -> str:
        workflow_id = f"direction-{uuid.uuid4().hex}"
        with SetWorkflowID(workflow_id):
            handle = DBOS.start_workflow(
                _run_direction_workflow,
                direction,
                max_ideas,
                workflow_id,
            )
        return handle.get_workflow_id()

    def submit_resume(self, run_id: str) -> str:
        workflow_id = f"resume-{run_id}-{uuid.uuid4().hex[:10]}"
        with SetWorkflowID(workflow_id):
            handle = DBOS.start_workflow(_resume_workflow, run_id)
        return handle.get_workflow_id()

    def submit_approval(self, run_id: str, reviewer: str) -> str:
        workflow_id = f"approve-{run_id}"
        with SetWorkflowID(workflow_id):
            handle = DBOS.start_workflow(_approve_workflow, run_id, reviewer)
        return handle.get_workflow_id()


dispatcher = DurableDispatcher()
