from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.api.dependencies import get_runtime
from backend.api.routers import providers
from backend.api.webapp import create_app
from backend.core.provider_settings import PROVIDER_ENV, ProviderSettingsStore
from backend.core.runtime import RuntimeContext, RuntimeMode


def test_missing_provider_settings_remain_empty(tmp_path) -> None:
    settings = {item["id"]: item for item in ProviderSettingsStore(tmp_path / ".env", {}).list_sanitized()}
    for provider in settings.values():
        assert provider["model_id"] == ""
        assert provider["base_url"] == ""
    assert settings["openai"]["api_mode"] == ""


def test_all_providers_persist_keys_and_custom_base_urls(tmp_path) -> None:
    environment = {}
    store = ProviderSettingsStore(tmp_path / ".env", environment)

    for provider, spec in PROVIDER_ENV.items():
        result = store.update(
            provider,
            f"{provider}-secret",
            f"https://{provider}.local/v1/",
            f"{provider}-model",
            "responses" if provider == "openai" else None,
        )
        assert result["api_key_configured"] is True
        assert result["base_url"] == f"https://{provider}.local/v1"
        assert result["model_id"] == f"{provider}-model"
        assert environment[spec["api_key"]] == f"{provider}-secret"
        assert environment[spec["base_url"]] == f"https://{provider}.local/v1"
        assert "secret" not in str(result)

    content = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in content
    assert "ANTHROPIC_BASE_URL" in content
    assert "GOOGLE_BASE_URL" in content


def test_provider_api_never_returns_key_and_rejects_invalid_url(tmp_path, monkeypatch) -> None:
    store = ProviderSettingsStore(tmp_path / ".env", {})
    monkeypatch.setattr(providers, "store", store)
    app = create_app()
    app.dependency_overrides[get_runtime] = lambda: SimpleNamespace(
        context=RuntimeContext(
            mode=RuntimeMode.DESKTOP,
            compute_location="local_device",
            storage_location="local_device",
            provider_settings_mutable=True,
            durable_database_url="sqlite:///test.sqlite",
        )
    )
    client = TestClient(app)

    response = client.put(
        "/api/v1/providers/openai",
        json={
            "base_url": "https://gateway.local/v1",
            "model_id": "gpt-custom",
            "api_mode": "responses",
            "api_key": "top-secret",
        },
    )
    assert response.status_code == 200
    assert response.json()["provider"]["api_key_configured"] is True
    assert response.json()["provider"]["api_mode"] == "responses"
    assert "top-secret" not in response.text

    invalid = client.put(
        "/api/v1/providers/google",
        json={"base_url": "file:///tmp/not-allowed", "model_id": "gemini-test"},
    )
    assert invalid.status_code == 422
