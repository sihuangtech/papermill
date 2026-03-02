import os
import json
import logging
import yaml
from .llm_client import call_llm

class PlanningAgent:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.logger = logging.getLogger(__name__)

    def plan_experiment(self, idea_file: str) -> str:
        """根据 idea.md 制定实验计划并生成代码"""
        with open(idea_file, 'r', encoding='utf-8') as f:
            idea_content = f.read()

        idea_id = os.path.basename(idea_file).replace("idea_", "").replace(".md", "")
        exp_dir = f"research_system/workspace/experiments/{idea_id}"
        os.makedirs(exp_dir, exist_ok=True)

        prompt = f"""
你是一个资深 AI 研究员。基于以下研究假设，制定一个详细的实验计划，并编写 Python 实验代码。

研究假设:
{idea_content}

任务要求:
1. 输出一份实验计划 (Markdown 格式)，包含：数据集选择、模型架构、baseline 方法、评估指标、实验步骤。
2. 编写一个完整的 Python 脚本 `experiment.py`，用于执行实验。脚本应包含数据加载、模型定义、训练/推理循环、评估，并将结果保存为 `results.json`。
3. 脚本应易于通过命令行运行。

请以以下格式输出：
===PLAN===
[实验计划内容]
===CODE===
[实验代码内容]
"""
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
    # agent.plan_experiment("research_system/workspace/ideas/idea_some_id.md")
