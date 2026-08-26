# 研序：自主科研智能体工作台

研序（Agentic Research）将文献证据、可证伪假设、实验计划、真实代码/Notebook 执行、留出验证和研究报告连接成一条可恢复的科研智能体工作流。它既可作为服务器上的云端 Web Agent，也可作为除外部模型/文献 API 外全部在本机运行的桌面 Agent。

[English documentation](README.md) · [更新日志](CHANGELOG.zh.md)

## 你可以用它做什么

### 1. 把研究方向变成可执行的研究计划

输入一个研究方向，例如“小样本医学影像分割的可靠性”。系统会检索并整理相关证据，提出可被实验推翻的假设，随后生成包含基线、候选方案、评价指标、随机种子和通过门槛的实验计划。计划生成后默认暂停，等你确认再执行。

### 2. 让 AI 编写并运行实验，而不是只写结论

获批后，系统会生成 Python 实验代码或带参数的 Jupyter Notebook，并在本地受控环境中运行。每次运行都会保存代码、输入参数、原始结果、日志、退出状态和耗时；Notebook 还会保存已执行版本，方便复现和检查。

### 3. 用独立验证判断结果是否可靠

系统将用于改进方案的开发种子与最终判断的留出种子分开。它比较基线和候选方案的成功率、最小提升量和波动情况，并给出 `accepted`（接受）、`rejected`（拒绝）、`inconclusive`（证据不足）或 `invalid`（结果无效）四种结论，避免把偶然跑通当成发现。

### 4. 获得可追溯的研究报告

运行完成后可生成 Markdown、LaTeX 和可选 PDF 报告。报告引用来自本次保存的证据快照，并附带实验结果和限制说明；验证未通过时会明确标注，不会包装成正面结论。

### 5. 在云端或本机管理全过程

可通过桌面应用、命令行或 Web 控制台查看研究进度、实时日志、实验指标、假设、报告和待审批计划。云端版由服务器执行 Agent、检索和实验；桌面版由本机 sidecar 执行同一套共享核心，研究文件不上传到研序服务器。DBOS 负责长任务恢复，科研状态文件负责审计每个已完成阶段。

### 6. 选择自己的大模型服务

模型运行时统一使用 OpenAI Agents SDK。OpenAI 走 SDK 原生 Responses/Chat Completions，Anthropic Claude 和 Google Gemini 走 SDK 的 LiteLLM 适配层；每个服务仍可单独配置 Base URL、模型 ID 和 API Key。

## 工作方式与边界

- 每项实验都固定评价指标、门槛和随机种子，基线与候选方案在同一条件下比较；
- 生成代码不会通过 shell 执行，运行时会移除 API Key，并限制超时、内存和日志；
- 这是一套帮助设计、执行和审计研究的工具，不能自动证明实验设计正确、数据没有泄漏或结论具有统计显著性。高风险研究仍应由领域研究者复核。

## 工作流

```text
研究方向
  → 多来源证据检索与去重
  → 可证伪假设 + 多维审核
  → 基线/候选实验计划
  → 人工审批（默认开启）
  → 开发种子上的候选有限迭代
  → 独立留出种子验证
  → accepted / rejected / inconclusive / invalid
  → 带证据和限制说明的 Markdown / LaTeX / 可选 PDF
```

详细设计见：

- [系统架构](docs/architecture.zh.md)
- [科研与实验协议](docs/research-protocol.zh.md)
- [安全边界](docs/security.zh.md)
- [Tauri 桌面架构与打包](docs/desktop.zh.md)

## 安装

要求 Python 3.10+、Node.js 20+。所有依赖均通过官方包管理器命令安装。

```bash
uv sync --extra dev
npm --prefix frontend ci
```

只使用 Web/CLI 时，上述依赖已经足够。开发桌面版还需要安装 Rust stable 和 [Tauri 2 的系统依赖](https://v2.tauri.app/start/prerequisites/)，然后在项目根目录安装 Tauri 依赖：

```bash
npm install
npm --prefix frontend install
```

复制环境变量模板并填写至少一个模型密钥：

```bash
cp .env.example .env
```

桌面版可在设置页填写 Base URL、模型 ID 和 API Key，配置写入应用数据目录的 `.env`。云端网页只读，供应商凭据由服务器管理员设置 `OPENAI_*`、`ANTHROPIC_*`、`GOOGLE_*` 环境变量；密钥不会由接口返回。

默认模型为 `gpt-5.6-terra`（Responses API）、`claude-sonnet-5` 和 `gemini-3.5-flash`。使用第三方兼容网关时，应以该网关实际开放的模型 ID 和接口模式为准。

`OPENAI_API_MODE` 仅接受 `responses`（调用 `/v1/responses`，默认）或 `chat_completions`（调用 `/v1/chat/completions`）。如果中转服务只声明“OpenAI 兼容”但没有实现 Responses API，应选择 `chat_completions`。

## 第一次运行

先做不会访问模型和网络的环境诊断与真实实验演示：

```bash
uv run python -m backend.cli doctor
uv run python -m backend.cli demo
uv run pytest
```

`demo` 会实际运行 3 个开发种子和 3 个留出种子下的基线/候选实验，共 12 个独立子进程，并在 `data/workspace/runs/` 保存审计产物。

## 启动一项研究

```bash
uv run python -m backend.cli run --direction "小样本医学影像分割的可靠性" --max-ideas 2
uv run python -m backend.cli status
```

默认配置会在规划完成后进入 `waiting_review`：

```bash
uv run python -m backend.cli approve <run_id>
```

失败后可恢复，未完成运行可取消：

```bash
uv run python -m backend.cli resume <run_id>
uv run python -m backend.cli cancel <run_id>
```

需要持续探索配置中的研究方向时：

```bash
uv run python -m backend.cli daemon
```

## Web 控制台

```bash
./start.sh
```

浏览器打开 `.env` 中 `BACKEND_PORT` 对应的地址（示例为 `http://127.0.0.1:4019`）。控制台提供运行状态、真实指标、假设、研究报告、实时日志和人工审批；云端全局配置由服务器管理员管理。

## Tauri 桌面应用

桌面版直接复用 `frontend/` 中的 React/Vite 前端，并将 FastAPI 后端打包成随应用启动的 Python sidecar；最终用户不需要另装 Python、Node.js 或手工启动 API 服务。

开发运行：

```bash
npm run desktop:dev
```

生成当前操作系统的安装包：

```bash
npm run desktop:build
```

构建前会自动运行前端构建和 `scripts/build_desktop_sidecar.py`。sidecar 文件按 Tauri 要求生成在 `src-tauri/binaries/`，并带当前 Rust target triple；该二进制属于构建产物，不提交到 Git。

桌面版特性：

- Rust 主进程自动选择空闲回环端口并启动/回收 FastAPI sidecar；
- 每次启动生成临时访问令牌，后端拒绝没有令牌的 `/api/v1` 请求；
- `config.yaml`、`prompts.yaml`、`.env` 和 `data/workspace/` 位于系统应用数据目录，更新应用不会覆盖研究数据；
- 浏览器 Web 模式保持兼容，仍可使用 `./start.sh`；
- 当前实验执行仍是受限的本地子进程，不等同于 Docker/虚拟机级强隔离。运行不可信代码时仍应使用专用容器或虚拟机。

## 实验代码协议

Python 实验必须：

1. 从 `PAPERMILL_SEED` 读取随机种子（实验协议兼容变量名）；
2. 从 `PAPERMILL_OUTPUT` 读取结果文件位置（实验协议兼容变量名）；
3. 输出符合清单 `metric.json_path` 的有限数值；
4. 不安装依赖、不启动子进程，默认不能联网；
5. 单个生成代码文件不超过 250 行。

Notebook 使用带 `parameters` 标签的参数单元。执行器会注入 `seed` 和 `results_path`，并保存 `executed.ipynb`。

## 结果为什么更可信

- 开发种子和验证种子在配置校验阶段就必须完全分离；
- 基线和候选必须采用相同指标与种子集合；
- 最小提升量在实验前写入 `manifest.json`；
- 最终决策只读取留出验证结果；
- 任一试验的原始输出、日志、退出码和耗时均可回溯；
- 结果缺失、波动过大或成功率不足不会被包装成阳性结论。

这仍然不能自动证明实验设计科学、数据没有泄漏或结果具有统计显著性。高风险科研必须由领域研究者审核数据、方法和结论。

## Docker

```bash
cp .env.example .env
docker compose up --build
```

服务只绑定本机 `127.0.0.1:8000`。容器以非 root 用户运行，工作区持久化到宿主机。Docker 镜像默认不包含 LaTeX；没有 `pdflatex` 时仍会生成 Markdown 和 `.tex`，不会在运行时自动安装系统软件。
