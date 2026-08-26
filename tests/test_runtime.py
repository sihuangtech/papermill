from pathlib import Path

import pytest

from backend.core.runtime import RuntimeMode, build_runtime_context
from backend.workflow import factory


def test_web_process_uses_server_compute_and_workspace_sqlite(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AGENTIC_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("PAPERMILL_DESKTOP_MODE", raising=False)
    monkeypatch.delenv("DBOS_SYSTEM_DATABASE_URL", raising=False)

    context = build_runtime_context(tmp_path)

    assert context.mode is RuntimeMode.CLOUD
    assert context.compute_location == "server"
    assert context.provider_settings_mutable is False
    assert Path(context.durable_database_url.removeprefix("sqlite:///")).parent == tmp_path / "cache"


def test_desktop_sidecar_keeps_compute_and_storage_on_device(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPERMILL_DESKTOP_MODE", "1")
    monkeypatch.setenv("AGENTIC_RUNTIME_MODE", "desktop")

    context = build_runtime_context(tmp_path)

    assert context.mode is RuntimeMode.DESKTOP
    assert context.compute_location == "local_device"
    assert context.storage_location == "local_device"
    assert context.provider_settings_mutable is True


def test_postgres_url_is_not_exposed_to_frontend(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DBOS_SYSTEM_DATABASE_URL", "postgresql://user:secret@db/research")

    payload = build_runtime_context(tmp_path).public_dict()

    assert payload["durable_backend"] == "postgresql"
    assert "secret" not in str(payload)


def test_invalid_runtime_mode_fails_explicitly(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_RUNTIME_MODE", "hybrid")

    with pytest.raises(RuntimeError, match="AGENTIC_RUNTIME_MODE"):
        build_runtime_context(tmp_path)


def test_new_desktop_runtime_starts_before_provider_is_configured(tmp_path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(factory, "load_dotenv", lambda: False)
    monkeypatch.setenv("AGENTIC_RUNTIME_MODE", "desktop")
    for provider in ("OPENAI", "ANTHROPIC", "GOOGLE"):
        for suffix in ("MODEL_ID", "API_KEY", "BASE_URL"):
            monkeypatch.delenv(f"{provider}_{suffix}", raising=False)
    monkeypatch.delenv("OPENAI_API_MODE", raising=False)

    runtime = factory.build_runtime(root / "config.yaml", root / "prompts.yaml")

    assert runtime.context.mode is RuntimeMode.DESKTOP
    assert runtime.workspace.root.exists()
