import os
import json
import logging
import yaml
import subprocess
import matplotlib.pyplot as plt
import pandas as pd
from typing import Dict
from .llm_client import call_llm

class WritingAgent:
    def __init__(self, config_path: str, prompts_path: str = "prompts.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        with open(prompts_path, 'r', encoding='utf-8') as f:
            self.prompts = yaml.safe_load(f)['writing']
        self.logger = logging.getLogger(__name__)
        self._check_pdflatex()

    def _check_pdflatex(self):
        """检查 pdflatex 是否可用"""
        try:
            subprocess.run(["pdflatex", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.logger.info("pdflatex 已就绪")
        except:
            self.logger.warning("pdflatex 未找到，尝试安装 texlive-full...")
            try:
                # 注意：在某些环境下可能需要 sudo，这里假设环境允许 apt-get
                subprocess.run(["apt-get", "update"], check=True)
                subprocess.run(["apt-get", "install", "-y", "texlive-full"], check=True)
                self.logger.info("texlive-full 安装成功")
            except Exception as e:
                self.logger.error(f"无法安装 texlive-full: {e}. 将无法编译 PDF。")

    def write_paper(self, idea_file: str, results_file: str) -> str:
        """撰写短论文并编译为 PDF"""
        with open(idea_file, 'r', encoding='utf-8') as f:
            idea_content = f.read()

        with open(results_file, 'r', encoding='utf-8') as f:
            results_data = json.load(f)

        idea_id = os.path.basename(results_file).replace(".json", "")
        latex_dir = f"src/workspace/latex/{idea_id}"
        os.makedirs(latex_dir, exist_ok=True)

        # 生成图表
        self._generate_plots(results_data, latex_dir)

        prompt = self.prompts['write_paper'].format(
            idea_content=idea_content,
            results_data=json.dumps(results_data, indent=2)
        )
        try:
            latex_code = call_llm(prompt, model=self.config.get('llm_model', 'gpt-4o'))
            if "```latex" in latex_code:
                latex_code = latex_code.split("```latex")[1].split("```")[0].strip()
            elif "```" in latex_code:
                latex_code = latex_code.split("```")[1].split("```")[0].strip()

            tex_path = os.path.join(latex_dir, f"paper_{idea_id}.tex")
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(latex_code)

            self.logger.info(f"LaTeX 源码已生成: {tex_path}")

            # 编译 PDF
            self._compile_pdf(tex_path, latex_dir)

            return tex_path
        except Exception as e:
            self.logger.error(f"撰写论文失败: {e}")
            return None

    def _generate_plots(self, results_data: Dict, output_dir: str):
        """根据结果生成图表"""
        try:
            # 简单的自动绘图逻辑，假设结果中有可绘图的数据
            plt.figure(figsize=(10, 6))
            if isinstance(results_data, dict):
                keys = list(results_data.keys())
                values = [v for v in results_data.values() if isinstance(v, (int, float))]
                if values:
                    plt.bar(keys[:len(values)], values)
                    plt.title("Experiment Results")
                    plt.savefig(os.path.join(output_dir, "plot.png"))
            plt.close()
            self.logger.info("图表已生成")
        except Exception as e:
            self.logger.warning(f"自动生成图表失败: {e}")

    def _compile_pdf(self, tex_path: str, working_dir: str):
        """调用 pdflatex 编译 PDF"""
        try:
            # 运行两次以处理引用
            for _ in range(2):
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", os.path.basename(tex_path)],
                    cwd=working_dir,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            self.logger.info(f"PDF 编译成功")
        except Exception as e:
            self.logger.error(f"PDF 编译失败: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = WritingAgent("config.yaml")
    # agent.write_paper("src/workspace/ideas/idea_some.md", "src/workspace/results/some.json")
