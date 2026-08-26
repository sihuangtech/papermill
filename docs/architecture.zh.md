# 研序（Agentic Research）系统架构

## 产品边界

研序只有一套科研核心，但有两种运行位置：

| 形态 | 界面 | Agent、检索、实验、文件 | 外部网络 |
| --- | --- | --- | --- |
| 云端 Web | 浏览器 | 全部运行在研序服务器 | 服务器调用模型与文献 API |
| 本地桌面 | Tauri 窗口 | 全部运行在用户设备 | 仅调用模型与文献 API |

桌面端不是网站的遥控器，也不依赖研序云服务器。Tauri 启动本机 FastAPI sidecar，研究数据默认只保存在操作系统应用数据目录。云端 Web 的浏览器只负责交互，不在浏览器中执行实验。

## 共享核心与运行适配器

```text
React / Vite UI
        │ HTTP + SSE
        ▼
FastAPI API ─── RuntimeContext（cloud / desktop）
        │
        ├── DBOS durable dispatcher
        │       ├── SQLite（桌面、单机服务器）
        │       └── PostgreSQL（多实例云部署）
        │
        ▼
Research Workflow
  evidence → hypothesis → plan → approval
           → baseline → candidate → holdout → report
        │
        ├── OpenAI Agents SDK model adapter
        ├── SearchProvider adapters
        ├── ExperimentExecutor
        └── Workspace / RunRepository
```

依赖方向保持单向：API 只提交任务，科研工作流决定阶段，领域模型定义证据和实验契约，基础设施适配器负责模型、检索、进程与文件。云端与桌面端不复制业务逻辑，只替换运行位置和持久化配置。

## 为什么使用 OpenAI Agents SDK

模型调用统一经过 `openai-agents`，不再分别维护三套请求代码：

- OpenAI 官方接口使用 SDK 原生 Responses 或 Chat Completions model；
- OpenAI 兼容网关仍可配置 Base URL 和接口模式；
- Anthropic Claude 与 Google Gemini 使用 Agents SDK 提供的 LiteLLM 适配层；
- 业务服务只依赖 `LlmClient.complete()`，未来可替换模型路由而不改科研协议；
- Agents SDK tracing 默认关闭，避免桌面端额外上传研究内容；只有显式设置 `OPENAI_AGENTS_TRACING_ENABLED=1` 才启用。

Agents SDK 负责模型运行时，不负责决定科研结论。证据绑定、可证伪假设、人工审批、开发种子和留出种子隔离仍由确定性的领域状态机执行。

Pi SDK 适合构建高度交互的 TypeScript coding agent，但当前核心、Notebook 和实验执行均在 Python。为了不增加 Node sidecar 与 JSON-RPC 双运行时，Pi 不进入默认依赖；以后如需独立“代码探索 Agent”，可通过适配器接入，而不改主流程。

## 两层可恢复性

DBOS 负责“任务是否会在进程或服务器重启后继续”，领域状态文件负责“科研上已经完成了什么”：

1. API 使用 DBOS 启动有唯一 workflow ID 的后台任务；
2. DBOS 将调度状态写入 SQLite 或 PostgreSQL；
3. `run.json` 只在阶段成功后更新 `completed_stages`；
4. DBOS 重试时，工作流读取 `run.json`，跳过已经完成的昂贵阶段；
5. 方向任务使用稳定 batch ID，证据、假设和 run ID 可幂等恢复，不会因重试重复建档。

每个研究运行保存在 `<workspace>/runs/<run_id>/`：

```text
run.json          当前状态、阶段、决策、指标和产物索引
events.jsonl      追加式事件时间线
hypothesis.json   本次运行使用的假设快照
evidence.json     本次运行使用的证据快照
approval.json     人工批准记录
experiment/       计划、清单、基线和候选代码
trials/           每个阶段、方案和种子的独立运行目录
validation.json   最终验证门禁报告
```

## 配置与安全边界

- 桌面端允许在设置页写入应用数据目录中的 `.env`；API 永不返回密钥明文。
- 云端网页的供应商凭据和全局实验策略只读，由服务器管理员通过环境变量和 `config.yaml` 管理，避免普通网页用户修改全局密钥。
- Tauri sidecar 只监听 `127.0.0.1`，每次启动生成随机访问令牌。
- 实验子进程会移除模型 API Key，限制超时、内存和日志，并执行 AST 策略检查。
- AST 检查与本地子进程不是强沙箱。运行不可信代码时，生产部署仍应接入容器、MicroVM 或专用计算节点。
- 当前云端形态适合单租户部署。面向多组织公开服务前，还需要加入用户认证、租户级工作区/对象存储隔离和配额；不能只依靠浏览器生成的 workspace ID。

## 扩展点

- `SearchProvider`：PubMed、Crossref、OpenAlex 或内部知识库；
- `LlmClient`：其他 Agents SDK `ModelProvider` 或企业模型网关；
- `ExperimentExecutor`：Docker、Slurm、Kubernetes、远程 GPU 或 MicroVM；
- `ResultValidator`：置信区间、显著性检验、多重比较修正；
- `WritingService`：期刊模板、BibTeX 与人工审稿阶段。
