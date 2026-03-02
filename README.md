# Papermill: 全自动 AI 科研流水线系统 (FARS-like)

Papermill 是一个受 FARS（Fully Automated Research System）启发而构建的全自动科研系统。它旨在实现从文献检索、假设构思、实验规划、代码实现、实验执行到论文撰写的完整科研闭环，无需任何人工干预。

## 核心理念

本系统的核心哲学是**回归知识生产的第一性原理**。我们不追求复杂的排版或论文格式的冗余，而是聚焦于每一个明确的研究假设。无论实验结果是正面还是负面，只要假设具有科学价值且验证过程严谨，系统就会产出一篇短小精悍的论文，记录这一科学发现。

## 系统架构

Papermill 采用四 Agent 协同工作的架构，通过共享文件系统进行通信：

1. **构思 Agent (`ideation_agent.py`)**：
    - 从 `config.yaml` 预设的方向出发。
    - 集成 arXiv、Semantic Scholar、Google Scholar、GitHub 和 HuggingFace 进行多维度文献检索。
    - 利用 LLM 生成具有创新性的研究假设（Problem Statement, Hypothesis, Proposed Verification, Novelty）。
    - 内置自评审机制，只有高分想法才会进入后续流水线。

2. **规划 Agent (`planning_agent.py`)**：
    - 基于研究想法，制定详细的实验计划（数据集、模型架构、基准方法、评估指标）。
    - 自动生成完整的 Python 实验代码框架。

3. **实验 Agent (`experiment_agent.py`)**：
    - 并发执行实验代码，捕获实验日志与结果（JSON 格式）。
    - **自修复机制**：当代码运行报错时，利用 LLM 自动分析错误原因并修复代码，最多支持 3 次重试。
    - 超时控制与结果自动归档。

4. **写作 Agent (`writing_agent.py`)**：
    - 读取实验结果，自动绘制可视化图表（matplotlib）。
    - 撰写短论文（LaTeX 格式），如实报告实验发现。
    - 自动调用 `pdflatex` 将论文编译为 PDF（若环境缺失会自动尝试安装 `texlive-full`）。

## 目录结构

```text
src/
├── workspace/
│   ├── ideas/          # 构思 Agent 输出 of idea.md 文件
│   ├── memory/         # 已处理论文 ID 与知识库
│   ├── experiments/    # 每个想法对应的实验代码与临时文件
│   ├── results/        # 实验产出的 JSON 结果
│   ├── references/     # 下载的参考资料
│   └── latex/          # 生成的 LaTeX 源码与编译出的 PDF
├── agents/
│   ├── llm_client.py   # 统一的 LLM 接入层 (OpenAI/Claude/Gemini)
│   ├── ideation_agent.py
│   ├── planning_agent.py
│   ├── experiment_agent.py
│   └── writing_agent.py
├── orchestrator.py     # 主调度器，管理并发流水线
├── config.yaml         # 全局配置文件
└── requirements.txt    # 依赖库列表
```

## 快速开始

### 1. 环境准备

- 确保已安装 Python 3.9+。
- 设置 API 密钥：建议在根目录下创建 `.env` 文件（可参考 `.env.example`）：

    ```bash
    # 复制模板
    cp .env.example .env
    # 然后编辑 .env 填写你的 Key
    ```

    或者手动设置环境变量：

    ```bash
    export OPENAI_API_KEY="your_openai_key"
    ...
    ```

### 2. 创建并安装虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活环境 (macOS/Linux)
source venv/bin/activate

# 升级 pip 并安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 配置系统

编辑 `config.yaml` 调整研究方向、并发数和模型选择。

### 4. 运行系统

```bash
# 确保已在虚拟环境下
source venv/bin/activate

# 启动主调度循环
python -m src.orchestrator
```

系统将启动主调度循环，持续进行科研产出。

## 关键技术点

- **多模型支持**：内置统一 LLM 调用接口，无缝切换主流大模型。
- **并行流水线**：使用 `ThreadPoolExecutor` 支持多条研究路径并发进行。
- **鲁棒性设计**：各 Agent 间松耦合，单点失败不影响整体系统。
- **全自动编译**：集成 LaTeX 编译环境，产出标准的学术 PDF 文档。
