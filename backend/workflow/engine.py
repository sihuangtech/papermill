"""以持久化状态机编排完整科研流程。"""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.core.config import AppConfig
from backend.core.runs import RunRepository
from backend.core.storage import Workspace, atomic_write_json, read_json, safe_identifier
from backend.domain.models import (
    Evidence,
    ExperimentManifest,
    Hypothesis,
    ResearchRun,
    RunStage,
    RunStatus,
    ValidationReport,
)
from backend.research.experiments import ExperimentService, ResearchCancelled
from backend.research.hypotheses import HypothesisService
from backend.research.literature import LiteratureService
from backend.research.planning import PlanningService
from backend.research.writing import WritingService


class WorkflowEngine:
    def __init__(
        self,
        config: AppConfig,
        workspace: Workspace,
        runs: RunRepository,
        literature: LiteratureService,
        hypotheses: HypothesisService,
        planning: PlanningService,
        experiments: ExperimentService,
        writing: WritingService,
    ):
        self.config = config
        self.workspace = workspace
        self.runs = runs
        self.literature = literature
        self.hypotheses = hypotheses
        self.planning = planning
        self.experiments = experiments
        self.writing = writing
        self.logger = logging.getLogger(__name__)

    def run_direction(
        self,
        direction: str,
        max_ideas: int | None = None,
        batch_id: str | None = None,
    ) -> list[ResearchRun]:
        """从一个研究方向创建若干独立、可恢复的运行。"""
        batch = safe_identifier(batch_id) if batch_id else f"{safe_identifier(direction)}-{uuid.uuid4().hex[:8]}"
        evidence_path = self.workspace.evidence / f"{batch}.json"
        evidence = self._load_or_search_evidence(direction, evidence_path)
        ideas = self._load_or_generate_ideas(direction, evidence, max_ideas, batch)
        created: list[ResearchRun] = []
        for hypothesis in ideas:
            run_id = f"{hypothesis.id}-{batch[-10:]}"
            created.append(self.runs.get(run_id) or self._create_run(direction, hypothesis, evidence, run_id))
        with ThreadPoolExecutor(max_workers=self.config.workflow.max_concurrent_pipelines) as pool:
            return list(pool.map(lambda item: self.execute(item.id), created))

    def execute(self, run_id: str) -> ResearchRun:
        """执行或恢复运行；已完成阶段不会重复执行。"""
        run = self.runs.require(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.CANCELLED}:
            return run
        try:
            run_dir = self.workspace.run_dir(run_id)
            hypothesis = Hypothesis.model_validate(read_json(run_dir / "hypothesis.json"))
            evidence = [Evidence.model_validate(item) for item in read_json(run_dir / "evidence.json", [])]
            bundle_dir = run_dir / "experiment"

            if RunStage.PLANNING not in run.completed_stages:
                self.runs.start_stage(run_id, RunStage.PLANNING)
                bundle = self.planning.create_bundle(hypothesis, evidence, bundle_dir)
                self.runs.finish_stage(
                    run_id,
                    RunStage.PLANNING,
                    {"plan": str(bundle.plan_path), "manifest": str(bundle_dir / "manifest.json")},
                )
                run = self.runs.require(run_id)
                if run.status == RunStatus.CANCELLED:
                    return run

            approval_path = run_dir / "approval.json"
            if self.config.workflow.human_review_before_execution and not approval_path.exists():
                return self.runs.wait_for_review(run_id)

            report_path = run_dir / "validation.json"
            if RunStage.VALIDATION not in run.completed_stages:
                manifest = ExperimentManifest.model_validate(read_json(bundle_dir / "manifest.json"))
                report = self._run_experiments(run_id, manifest, bundle_dir, run_dir)
                self.runs.finish_stage(
                    run_id,
                    RunStage.VALIDATION,
                    {"validation": str(report_path)},
                )
            else:
                report = ValidationReport.model_validate(read_json(report_path))

            run = self.runs.require(run_id)
            if run.status == RunStatus.CANCELLED:
                return run
            run = self.runs.update_summary(
                run_id,
                report.decision,
                {
                    "metric": report.metric_name,
                    "baseline_mean": report.baseline_mean,
                    "candidate_mean": report.candidate_mean,
                    "improvement": report.absolute_delta,
                    "success_rate": report.success_rate,
                },
            )

            if RunStage.WRITING not in run.completed_stages:
                self.runs.start_stage(run_id, RunStage.WRITING)
                artifacts = self.writing.write(
                    hypothesis,
                    evidence,
                    report,
                    self.workspace.papers / run_id,
                )
                self.runs.finish_stage(run_id, RunStage.WRITING, artifacts)
            if self.runs.require(run_id).status == RunStatus.CANCELLED:
                return self.runs.require(run_id)
            return self.runs.complete(run_id, report.decision)
        except ResearchCancelled:
            return self.runs.require(run_id)
        except Exception as error:
            self.logger.exception("科研运行失败: %s", run_id)
            if self.runs.require(run_id).status == RunStatus.CANCELLED:
                return self.runs.require(run_id)
            return self.runs.fail(run_id, str(error))

    def approve(self, run_id: str, reviewer: str = "local-user") -> ResearchRun:
        run = self.runs.approve(run_id)
        atomic_write_json(
            self.workspace.run_dir(run_id) / "approval.json",
            {"reviewer": reviewer, "approved": True},
        )
        return self.execute(run.id)

    def _create_run(
        self,
        direction: str,
        hypothesis: Hypothesis,
        evidence: list[Evidence],
        run_id: str | None = None,
    ) -> ResearchRun:
        run_id = run_id or f"{hypothesis.id}-{uuid.uuid4().hex[:6]}"
        run = ResearchRun(
            id=run_id,
            title=hypothesis.title,
            direction=direction,
            completed_stages=[RunStage.LITERATURE, RunStage.IDEATION],
        )
        self.runs.create(run)
        run_dir = self.workspace.run_dir(run_id)
        atomic_write_json(run_dir / "hypothesis.json", hypothesis.model_dump(mode="json"))
        atomic_write_json(run_dir / "evidence.json", [item.model_dump(mode="json") for item in evidence])
        run.artifacts.update(
            {
                "hypothesis": str(run_dir / "hypothesis.json"),
                "evidence": str(run_dir / "evidence.json"),
            }
        )
        return self.runs.save(run)

    def _load_or_search_evidence(self, direction: str, path: Path) -> list[Evidence]:
        cached = read_json(path)
        if cached:
            return [Evidence.model_validate(item) for item in cached]
        return self.literature.search(direction, path)

    def _load_or_generate_ideas(
        self,
        direction: str,
        evidence: list[Evidence],
        max_ideas: int | None,
        batch: str,
    ) -> list[Hypothesis]:
        index_path = self.workspace.cache / f"{batch}-ideas.json"
        cached = read_json(index_path)
        if cached:
            return [Hypothesis.model_validate(item) for item in cached]
        ideas = self.hypotheses.generate(
            direction,
            evidence,
            max_ideas or self.config.workflow.max_ideas_per_cycle,
            self.workspace.ideas,
        )
        atomic_write_json(index_path, [item.model_dump(mode="json") for item in ideas])
        return ideas

    def _run_experiments(
        self,
        run_id: str,
        manifest: ExperimentManifest,
        bundle_dir: Path,
        run_dir: Path,
    ) -> ValidationReport:
        current: list[RunStage | None] = [None]

        def on_stage(stage_name: str) -> None:
            stage = RunStage(stage_name)
            if current[0] is not None:
                self.runs.finish_stage(run_id, current[0])
            self.runs.start_stage(run_id, stage)
            current[0] = stage

        report = self.experiments.run(
            manifest,
            bundle_dir,
            run_dir,
            on_stage=on_stage,
            is_cancelled=lambda: self.runs.require(run_id).status == RunStatus.CANCELLED,
        )
        if current[0] is not None and current[0] != RunStage.VALIDATION:
            self.runs.finish_stage(run_id, current[0])
        return report
