import os
import yaml
import logging
import time
import concurrent.futures
from typing import List
import subprocess

try:
    from agents.ideation_agent import IdeationAgent
    from agents.planning_agent import PlanningAgent
    from agents.experiment_agent import ExperimentAgent
    from agents.writing_agent import WritingAgent
except ImportError:
    from .agents.ideation_agent import IdeationAgent
    from .agents.planning_agent import PlanningAgent
    from .agents.experiment_agent import ExperimentAgent
    from .agents.writing_agent import WritingAgent

class Orchestrator:
    def __init__(self, config_path: str = "config.yaml"):
        self._ensure_directories()
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        self.ideation_agent = IdeationAgent(config_path)
        self.planning_agent = PlanningAgent(config_path)
        self.experiment_agent = ExperimentAgent(config_path)
        self.writing_agent = WritingAgent(config_path)

        self.max_concurrent = self.config.get('max_concurrent_pipelines', 3)
        self.auto_commit = self.config.get('auto_commit', True)

    def _ensure_directories(self):
        """确保工作目录存在"""
        dirs = [
            "research_system/workspace/ideas",
            "research_system/workspace/memory",
            "research_system/workspace/experiments",
            "research_system/workspace/results",
            "research_system/workspace/references",
            "research_system/workspace/latex"
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("system.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def run_pipeline(self, idea_file: str):
        """执行单条研究流水线"""
        try:
            self.logger.info(f"开始流水线: {idea_file}")

            # 1. Planning
            exp_dir = self.planning_agent.plan_experiment(idea_file)
            if not exp_dir:
                self.logger.error(f"Planning 失败: {idea_file}")
                return

            # 2. Experiment
            results_file = self.experiment_agent.run_experiment(exp_dir)
            if not results_file:
                self.logger.error(f"Experiment 失败: {idea_file}")
                return

            # 3. Writing
            paper_path = self.writing_agent.write_paper(idea_file, results_file)
            if not paper_path:
                self.logger.error(f"Writing 失败: {idea_file}")
                return

            self.logger.info(f"流水线完成: {idea_file}. 论文产出: {paper_path}")

            if self.auto_commit:
                self._git_commit(idea_file)

        except Exception as e:
            self.logger.error(f"流水线执行过程中发生异常: {e}", exc_info=True)

    def _git_commit(self, idea_file: str):
        """提交实验结果"""
        try:
            idea_id = os.path.basename(idea_file).replace(".md", "")
            subprocess.run(["git", "add", "research_system/workspace/"], check=True)
            subprocess.run(["git", "commit", "-m", f"Completed research pipeline for {idea_id}"], check=True)
            self.logger.info(f"Git commit 成功: {idea_id}")
        except Exception as e:
            self.logger.error(f"Git commit 失败: {e}")

    def start(self):
        """启动主循环"""
        self.logger.info("FARS 系统已启动")
        while True:
            try:
                # 批量生成想法
                self.logger.info("正在生成新想法...")
                self.ideation_agent.generate_ideas()

                # 获取待处理的想法文件
                idea_files = [
                    os.path.join("research_system/workspace/ideas", f)
                    for f in os.listdir("research_system/workspace/ideas")
                    if f.endswith(".md")
                ]

                # 过滤掉已经处理过的 (这里简单起见，通过检查 latex/ 是否存在同名目录)
                pending_ideas = []
                for f in idea_files:
                    idea_id = os.path.basename(f).replace("idea_", "").replace(".md", "")
                    if not os.path.exists(f"research_system/workspace/latex/{idea_id}"):
                        pending_ideas.append(f)

                if not pending_ideas:
                    self.logger.info("没有待处理的想法，等待 1 小时...")
                    time.sleep(3600)
                    continue

                self.logger.info(f"发现 {len(pending_ideas)} 个待处理的想法。启动并发流水线 (max={self.max_concurrent})...")

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                    executor.map(self.run_pipeline, pending_ideas)

                self.logger.info("当前轮次流水线处理完毕，等待新想法生成...")
                time.sleep(60) # 休息一下

            except Exception as e:
                self.logger.error(f"主调度循环异常: {e}", exc_info=True)
                time.sleep(60)

if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.start()
