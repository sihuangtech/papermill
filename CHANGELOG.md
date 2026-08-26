# Changelog

All notable changes to CaiQi Scholar are documented here. This history was reconstructed from repository commits because the project did not tag its early releases.

Chinese changelog: [CHANGELOG.zh.md](CHANGELOG.zh.md)

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## 0.3.0 - 2026-08-26

### Added

- Added OpenAI Agents SDK as the shared agent runtime. OpenAI uses native Responses or Chat Completions adapters; Anthropic and Gemini use the SDK's LiteLLM adapter.
- Added DBOS durable workflows for research-direction runs, approvals, resumptions, and recovery after process restarts.
- Added an explicit cloud/desktop runtime model and a status API that reports compute and data location without exposing credentials.
- Added deterministic batch and run identifiers so recovered workflows do not duplicate completed research work.
- Added runtime tests and shared frontend types for the new execution model.

### Changed

- Reworked the product into one shared research core with two delivery modes: a server-executed Web Agent and a local desktop Agent whose work stays on the user's device except for external model and literature API calls.
- Redesigned the research workspace around pending approvals, the research-stage spine, run health, and a prominent cloud/local location indicator.
- Made cloud provider and model settings read-only in the browser; desktop settings remain locally editable.
- Refined model-output recovery while retaining structured JSON validation for third-party provider compatibility.
- Updated Python, Node.js, React, Vite, Tauri, and Rust dependencies to their latest compatible stable releases.
- Standardized Python installation and execution on `uv`, and updated deployment, desktop, environment, and architecture documentation.
- Renamed the Python command to `agentic-research` and synchronized Python, npm, frontend, Cargo, and Tauri versions.

### Security

- Disabled Agents SDK tracing by default and excluded sensitive trace payloads unless tracing is explicitly enabled.
- Kept API keys out of child experiment processes and public runtime-status responses.
- Prevented ordinary cloud users from changing server-wide model credentials through the Web UI.

## 0.2.0 - 2026-07-20

### Added

- Rebuilt the early prototype as a local-first, auditable workflow covering evidence collection, falsifiable hypotheses, experiment planning, human approval, code or notebook execution, held-out validation, and report generation.
- Added FastAPI REST and SSE endpoints, a React/Vite workspace, process supervision, run artifacts, live logs, and provider configuration.
- Added generated-code policy checks, constrained subprocess execution, run locking, provider validation, and tests for the research and execution layers.
- Added the Tauri 2 desktop application with a bundled Python sidecar, local lifecycle management, generated platform icons, and desktop packaging.
- Added English and Simplified Chinese localization, persisted language and theme preferences, and localization consistency checks.
- Added Docker, Nginx, and non-container deployment materials plus research protocol, security, desktop, and Semantic Scholar documentation.
- Added retry-assisted structured JSON extraction for imperfect model responses.

### Changed

- Replaced the original `src/agents` prototype with domain, infrastructure, research, workflow, and API modules.
- Renamed the product from Papermill to Agentic Research and standardized the package name as `sk-agentic-research`.
- Migrated the frontend from JavaScript to TypeScript and improved navigation, responsive layout, themes, and settings UX.
- Updated provider defaults, environment-driven ports, dependency locks, repository metadata, and deployment guidance.

### Removed

- Removed the original monolithic FARS agents and orchestrator after the auditable workflow architecture replaced them.
- Removed automatic installation of heavyweight system dependencies from the paper-writing path.

## Early development (unversioned)

### 2026-06-22

- Added a dedicated Simplified Chinese README and refreshed the frontend dependency set.

### 2026-03-02

- Created the initial Fully Automated Research System (FARS) prototype with ideation, planning, experiment, writing, and orchestration agents.
- Integrated early literature and repository search adapters and a unified OpenAI, Anthropic, and Google model client.
- Added experiment retries, LaTeX paper generation, plots, and the first automated PDF workflow.
- Added the first FastAPI and React/Vite Web interface, real-time monitoring, Docker, and Nginx configuration.
- Reorganized the prototype into `src/` and extracted prompts into configuration files.
