"""Papermill 命令行入口。"""

from __future__ import annotations

import argparse
import json
import logging
import time

from backend.demo import run_demo
from backend.doctor import diagnose
from backend.workflow.factory import build_runtime


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.FileHandler("system.log", encoding="utf-8"), logging.StreamHandler()],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cloud-or-local AI research automation workflow")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--prompts", default="prompts.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="从研究方向启动一轮工作流")
    run.add_argument("--direction", required=True)
    run.add_argument("--max-ideas", type=int)
    resume = subparsers.add_parser("resume", help="恢复失败或暂停的运行")
    resume.add_argument("run_id")
    approve = subparsers.add_parser("approve", help="批准实验计划并继续执行")
    approve.add_argument("run_id")
    cancel = subparsers.add_parser("cancel", help="取消未完成的运行")
    cancel.add_argument("run_id")
    subparsers.add_parser("status", help="列出运行状态")
    subparsers.add_parser("daemon", help="按配置持续生成研究任务")
    subparsers.add_parser("demo", help="运行无需模型的真实实验演示")
    subparsers.add_parser("doctor", help="检查本地环境")
    return parser


def main() -> int:
    configure_logging()
    args = build_parser().parse_args()
    runtime = build_runtime(args.config, args.prompts)
    if args.command == "run":
        runs = runtime.engine.run_direction(args.direction, args.max_ideas)
        print(json.dumps([item.model_dump(mode="json") for item in runs], ensure_ascii=False, indent=2))
    elif args.command == "resume":
        print(runtime.engine.execute(args.run_id).model_dump_json(indent=2))
    elif args.command == "approve":
        print(runtime.engine.approve(args.run_id).model_dump_json(indent=2))
    elif args.command == "cancel":
        print(runtime.runs.cancel(args.run_id).model_dump_json(indent=2))
    elif args.command == "status":
        print(json.dumps([item.model_dump(mode="json") for item in runtime.runs.list()], ensure_ascii=False, indent=2))
    elif args.command == "demo":
        print(run_demo(runtime.workspace).model_dump_json(indent=2))
    elif args.command == "doctor":
        print(json.dumps(diagnose(runtime.config, runtime.context), ensure_ascii=False, indent=2))
    elif args.command == "daemon":
        _daemon(runtime)
    return 0


def _daemon(runtime: object) -> None:
    logger = logging.getLogger(__name__)
    while True:
        for direction in runtime.config.research_directions:
            try:
                runtime.engine.run_direction(direction)
            except Exception:
                logger.exception("研究方向执行失败: %s", direction)
        time.sleep(runtime.config.workflow.daemon_interval_minutes * 60)


if __name__ == "__main__":
    raise SystemExit(main())
