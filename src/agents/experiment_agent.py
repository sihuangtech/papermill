import os
import json
import logging
import yaml
import subprocess
import time
from typing import Dict
from .llm_client import call_llm

class ExperimentAgent:
    def __init__(self, config_path: str, prompts_path: str = "prompts.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        with open(prompts_path, 'r', encoding='utf-8') as f:
            self.prompts = yaml.safe_load(f)['experiment']
        self.logger = logging.getLogger(__name__)

    def run_experiment(self, exp_dir: str) -> str:
        """执行实验代码并捕获结果"""
        code_path = os.path.join(exp_dir, "experiment.py")
        results_path = os.path.join(exp_dir, "results.json")

        retries = 0
        max_retries = 3
        timeout = self.config.get('experiment_timeout_minutes', 60) * 60

        while retries <= max_retries:
            self.logger.info(f"正在执行实验 ({retries}/{max_retries}): {code_path}")
            try:
                start_time = time.time()
                script_name = os.path.basename(code_path)
                process = subprocess.Popen(
                    ["python", script_name],
                    cwd=exp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                stdout, stderr = process.communicate(timeout=timeout)

                if process.returncode == 0:
                    self.logger.info("实验执行成功")
                    # 检查结果文件是否存在
                    if os.path.exists(results_path):
                        # 拷贝结果到全局 results 目录
                        idea_id = os.path.basename(exp_dir)
                        global_results_path = f"src/workspace/results/{idea_id}.json"
                        with open(results_path, 'r') as f:
                            res_data = json.load(f)
                        with open(global_results_path, 'w') as f:
                            json.dump(res_data, f, indent=4)
                        return global_results_path
                    else:
                        self.logger.warning("实验完成但未找到 results.json")
                        return None
                else:
                    self.logger.error(f"实验执行失败 (退出码 {process.returncode}):\n{stderr}")
                    if retries < max_retries:
                        self.logger.info("正在尝试自动 debug 并重试...")
                        self._debug_code(code_path, stderr)
                    retries += 1
            except subprocess.TimeoutExpired:
                process.kill()
                self.logger.error(f"实验超时 ({timeout}s)")
                return None
            except Exception as e:
                self.logger.error(f"执行实验时发生错误: {e}")
                retries += 1

        return None

    def _debug_code(self, code_path: str, error_msg: str):
        """调用 LLM 修复代码"""
        with open(code_path, 'r', encoding='utf-8') as f:
            code = f.read()

        prompt = self.prompts['debug_code'].format(error_msg=error_msg, code=code)
        try:
            fixed_code = call_llm(prompt, model=self.config.get('llm_model', 'gpt-4o'))
            if "```python" in fixed_code:
                fixed_code = fixed_code.split("```python")[1].split("```")[0].strip()
            elif "```" in fixed_code:
                fixed_code = fixed_code.split("```")[1].split("```")[0].strip()

            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            self.logger.info("代码已尝试修复")
        except Exception as e:
            self.logger.error(f"Debug 失败: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = ExperimentAgent("config.yaml")
    # agent.run_experiment("src/workspace/experiments/some_exp")
