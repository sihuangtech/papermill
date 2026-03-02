import os
import json
import logging
import yaml
from .llm_client import call_llm

class PlanningAgent:
    def __init__(self, config_path: str, prompts_path: str = "prompts.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        with open(prompts_path, 'r', encoding='utf-8') as f:
            self.prompts = yaml.safe_load(f)['planning']
        self.logger = logging.getLogger(__name__)

    def plan_experiment(self, idea_file: str) -> str:
        """根据 idea.md 制定实验计划并生成代码"""
        with open(idea_file, 'r', encoding='utf-8') as f:
            idea_content = f.read()

        idea_id = os.path.basename(idea_file).replace("idea_", "").replace(".md", "")
        exp_dir = f"src/workspace/experiments/{idea_id}"
        os.makedirs(exp_dir, exist_ok=True)

        prompt = self.prompts['plan_experiment'].format(idea_content=idea_content)
        try:
            response = call_llm(prompt, model=self.config.get('llm_model', 'gpt-4o'))

            plan_content = response.split("===PLAN===")[1].split("===CODE===")[0].strip()
            code_content = response.split("===CODE===")[1].strip()

            if "```python" in code_content:
                code_content = code_content.split("```python")[1].split("```")[0].strip()
            elif "```" in code_content:
                code_content = code_content.split("```")[1].split("```")[0].strip()

            plan_path = os.path.join(exp_dir, "experiment_plan.md")
            with open(plan_path, 'w', encoding='utf-8') as f:
                f.write(plan_content)

            code_path = os.path.join(exp_dir, "experiment.py")
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code_content)

            self.logger.info(f"已生成实验计划和代码: {exp_dir}")
            return exp_dir
        except Exception as e:
            self.logger.error(f"制定实验计划失败: {e}")
            return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = PlanningAgent("config.yaml")
    # agent.plan_experiment("src/workspace/ideas/idea_some_id.md")
