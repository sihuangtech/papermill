# 研序（Agentic Research）Tauri 桌面架构

## 目标

桌面版保留 React/Vite 界面和 FastAPI 科研工作流，不复制前端、不把业务逻辑重写成 Rust。Tauri 负责原生窗口、应用生命周期、本地数据目录和 sidecar 管理；Python 中的 OpenAI Agents SDK 负责模型运行时，DBOS 使用本地 SQLite 恢复长任务，科研核心继续负责文献、实验、Notebook 与报告。

```text
Tauri 2 / Rust 主进程
  ├─ 原生窗口 → frontend/dist
  ├─ 随机回环端口 + 临时访问令牌
  ├─ 启动/回收 Python sidecar
  └─ backend_connection IPC
          ↓
React/Vite 前端
  ├─ Axios → http://127.0.0.1:<随机端口>/api/v1
  ├─ SSE 实时运行/日志流
  └─ 报告下载
          ↓
PyInstaller FastAPI sidecar
  ├─ 原有 workflow 与 REST API
  ├─ 应用数据目录中的配置/密钥/工作区
  ├─ Python 脚本与 Notebook 执行
  └─ 父进程消失时自退出
```

## 目录职责

- `frontend/`：以 TypeScript/TSX 维护的 React/Vite 前端，Web 与桌面共同使用；
- `frontend/src/i18n/`：基于 i18next/react-i18next 的中英文资源，首次启动跟随系统语言并在本机保存用户选择；
- `frontend/src/theme.js`：外观偏好支持跟随系统、浅色和深色三档，并保存在本机；
- `src-tauri/`：Tauri 2 配置、Rust 生命周期代码、权限与图标；
- `assets/brand/`：研序（Agentic Research）品牌源图与透明应用图标，平台图标由 Tauri CLI 统一生成；
- `backend/desktop.py`：桌面 sidecar 入口及冻结后的 Python 执行桥；
- `scripts/build_desktop_sidecar.py`：使用 PyInstaller 生成 Tauri target-triple sidecar；
- `scripts/run-python.mjs`：在 macOS/Linux 与 Windows 上选择项目虚拟环境中的 Python；
- `src-tauri/binaries/`：本机生成的 sidecar 构建产物，Git 只保留 `.gitkeep`。

## 开发与构建

依赖必须通过各生态的官方命令维护：JavaScript 使用 `npm install`/`npm uninstall`，Rust 使用 `cargo add`/`cargo remove`，Python 使用 `python -m pip install`/`python -m pip uninstall`。

```bash
# Python 与 PyInstaller
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'

# Tauri 根项目与复用的前端
npm install
npm --prefix frontend install

# 开发
npm run desktop:dev

# 当前平台安装包
npm run desktop:build
```

`desktop:dev` 和 `desktop:build` 都会先检查 sidecar。只有 `backend/`、构建脚本、默认配置或 Python 依赖发生变化时才重新执行耗时的 PyInstaller 构建；需要强制重建可设置 `PAPERMILL_FORCE_SIDECAR=1`。

Tauri 安装包必须在目标操作系统上分别构建。macOS 产出 `.app`/`.dmg`，Windows 产出 MSI/NSIS，Linux 按安装的打包工具产出对应格式。当前 macOS 开发包使用 ad-hoc 签名并关闭 hardened runtime，以兼容 PyInstaller one-file 解压出的 Python 动态库。正式分发时应让 Tauri 与 PyInstaller 使用同一个 Developer ID 对内部二进制签名，恢复 hardened runtime，再进行 Apple 公证；其他平台同样需要相应的签名与发布凭据。

## 数据与升级

首次启动会将默认 `config.yaml` 和 `prompts.yaml` 复制到系统应用数据目录，此后不覆盖用户修改。模型密钥由设置页写入同一目录的 `.env`，研究产物位于其 `data/workspace/` 下，DBOS 的 SQLite 文件位于工作区 `cache/`。除外部模型与文献 API 外，这些计算和文件都留在用户设备。

典型位置：

- macOS：`~/Library/Application Support/cn.skstudio.papermill/`
- Windows：`%APPDATA%\\cn.skstudio.papermill\\`
- Linux：`$XDG_DATA_HOME/cn.skstudio.papermill/`（通常为 `~/.local/share/...`）

开发或自动化测试可用 `PAPERMILL_DESKTOP_DATA_DIR` 覆盖位置。这样应用更新、源码目录变化和安装包替换都不会删除用户研究数据。

## 安全边界

桌面后端只绑定 `127.0.0.1`。Rust 每次启动生成新的随机令牌，Axios 使用 `X-Papermill-Token`，SSE 与下载链接使用查询令牌；桌面 sidecar 关闭访问日志，避免令牌进入日志。前端没有开放 shell 插件权限，只有 Rust 主进程可以启动固定 sidecar。

这层保护用于防止同机网页随意调用本地 API，不是实验代码沙箱。当前 `LocalProcessRunner` 仍依赖静态代码策略、环境变量清理、超时、内存和输出限制。下一阶段如需执行来源不可信的代码，应在统一 `Sandbox` 接口下增加 Docker、Cube Sandbox 或 MicroVM 后端，不应让前端直接获得宿主机 shell 权限。
