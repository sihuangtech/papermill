"""在一个组合根中装配依赖，业务模块不直接创建基础设施。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from backend.core.config import AppConfig, load_config
from backend.core.runs import RunRepository
from backend.core.runtime import RuntimeContext, build_runtime_context
from backend.core.storage import Workspace
from backend.infrastructure.code_policy import PythonCodePolicy
from backend.infrastructure.executors import ExperimentExecutor
from backend.infrastructure.llm import AgentsSdkLlmClient
from backend.infrastructure.process import LocalProcessRunner
from backend.infrastructure.prompts import PromptRepository
from backend.infrastructure.search import build_providers
from backend.research.experiments import ExperimentService
from backend.research.hypotheses import HypothesisService
from backend.research.improvement import CandidateImprover
from backend.research.literature import LiteratureService
from backend.research.planning import PlanningService
from backend.research.validation import ResultValidator
from backend.research.writing import WritingService
from backend.workflow.engine import WorkflowEngine


@dataclass(frozen=True)
class Runtime:
    config: AppConfig
    context: RuntimeContext
    workspace: Workspace
    runs: RunRepository
    engine: WorkflowEngine


def build_runtime(config_path: str = "config.yaml", prompts_path: str = "prompts.yaml") -> Runtime:
    load_dotenv()
    config = load_config(config_path)
    workspace = Workspace(config.workspace_dir)
    workspace.ensure()
    context = build_runtime_context(workspace.root)
    runs = RunRepository(workspace)
    prompts = PromptRepository(prompts_path)
    generator_model = _provider_model(config.llm.provider)
    reviewer_provider = config.llm.reviewer_provider
    reviewer_model = config.llm.reviewer_model
    generator = AgentsSdkLlmClient(
        generator_model,
        config.llm.max_tokens,
        config.llm.provider,
        role="research-generator",
    )
    reviewer = AgentsSdkLlmClient(
        reviewer_model,
        config.llm.max_tokens,
        reviewer_provider,
        role="skeptical-reviewer",
    )
    policy = PythonCodePolicy(
        blocked_modules=config.security.blocked_modules if not config.security.allow_network else [],
    )
    process_runner = LocalProcessRunner(
        timeout_seconds=config.experiment.timeout_minutes * 60,
        max_memory_mb=config.security.max_memory_mb,
        max_output_kb=config.security.max_output_kb,
    )
    executor = ExperimentExecutor(process_runner, policy)
    validator = ResultValidator(
        config.experiment.minimum_success_rate,
        config.experiment.maximum_coefficient_of_variation,
    )
    literature = LiteratureService(
        build_providers(config.search.providers, config.search.request_timeout_seconds),
        config.search.results_per_provider,
    )
    hypotheses = HypothesisService(
        generator,
        reviewer,
        prompts,
        config.workflow.hypothesis_review_threshold,
    )
    planning = PlanningService(generator, prompts, config.experiment, policy)
    experiments = ExperimentService(
        executor,
        validator,
        CandidateImprover(generator, prompts, policy),
    )
    writing = WritingService(generator, prompts)
    engine = WorkflowEngine(
        config,
        workspace,
        runs,
        literature,
        hypotheses,
        planning,
        experiments,
        writing,
    )
    return Runtime(config, context, workspace, runs, engine)


def _provider_model(provider: str) -> str:
    env_name = f"{provider.upper()}_MODEL_ID"
    # 新安装需要先启动设置界面；真正运行 Agent 时由 SDK 客户端给出缺项提示。
    return (os.getenv(env_name) or "").strip()
