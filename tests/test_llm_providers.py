from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.infrastructure import llm


def _openai_environment(monkeypatch, api_mode: str = "responses") -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openai.local/v1")
    monkeypatch.setenv("OPENAI_API_MODE", api_mode)


def test_openai_responses_uses_agents_sdk_model(monkeypatch) -> None:
    _openai_environment(monkeypatch)
    async_client = MagicMock()
    monkeypatch.setattr(llm, "AsyncOpenAI", MagicMock(return_value=async_client))
    constructor = MagicMock(return_value="responses-model")
    monkeypatch.setattr(llm, "OpenAIResponsesModel", constructor)

    client = llm.AgentsSdkLlmClient("gpt-test", 100, "openai")

    assert client.sdk_model == "responses-model"
    constructor.assert_called_once_with(model="gpt-test", openai_client=async_client)
    llm.AsyncOpenAI.assert_called_once_with(
        api_key="secret",
        base_url="https://openai.local/v1",
    )


def test_openai_chat_completions_uses_compatible_sdk_model(monkeypatch) -> None:
    _openai_environment(monkeypatch, "chat_completions")
    async_client = MagicMock()
    monkeypatch.setattr(llm, "AsyncOpenAI", MagicMock(return_value=async_client))
    constructor = MagicMock(return_value="chat-model")
    monkeypatch.setattr(llm, "OpenAIChatCompletionsModel", constructor)

    client = llm.AgentsSdkLlmClient("gateway-model", 100, "openai")

    assert client.sdk_model == "chat-model"
    constructor.assert_called_once_with(model="gateway-model", openai_client=async_client)


def test_openai_rejects_missing_api_mode(monkeypatch) -> None:
    _openai_environment(monkeypatch)
    monkeypatch.delenv("OPENAI_API_MODE")

    with pytest.raises(RuntimeError, match="OPENAI_API_MODE"):
        llm.AgentsSdkLlmClient("gpt-test", 100, "openai").sdk_model


def test_provider_configuration_is_lazy_until_first_model_use(monkeypatch) -> None:
    for name in ("OPENAI_MODEL_ID", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_API_MODE"):
        monkeypatch.delenv(name, raising=False)

    client = llm.AgentsSdkLlmClient("", 100, "openai")

    with pytest.raises(RuntimeError, match="OPENAI_MODEL_ID"):
        _ = client.sdk_model


@pytest.mark.parametrize(
    ("provider", "model", "expected"),
    [
        ("anthropic", "claude-test", "anthropic/claude-test"),
        ("google", "gemini-test", "gemini/gemini-test"),
    ],
)
def test_non_openai_models_use_litellm_adapter(monkeypatch, provider, model, expected) -> None:
    monkeypatch.setenv(f"{provider.upper()}_API_KEY", "secret")
    monkeypatch.setenv(f"{provider.upper()}_BASE_URL", f"https://{provider}.local/v1")
    constructor = MagicMock(return_value="litellm-model")
    monkeypatch.setattr(llm, "LitellmModel", constructor)

    client = llm.AgentsSdkLlmClient(model, 100, provider)

    assert client.sdk_model == "litellm-model"
    constructor.assert_called_once_with(
        model=expected,
        api_key="secret",
        base_url=f"https://{provider}.local/v1",
    )


def test_complete_runs_one_turn_without_sensitive_tracing(monkeypatch) -> None:
    _openai_environment(monkeypatch)
    monkeypatch.setattr(llm.AgentsSdkLlmClient, "_build_model", lambda _: "sdk-model")
    runner = MagicMock(return_value=SimpleNamespace(final_output="agent-ok"))
    monkeypatch.setattr(llm.Runner, "run_sync", runner)

    result = llm.AgentsSdkLlmClient("gpt-test", 100, "openai").complete("hello", 80)

    assert result == "agent-ok"
    assert runner.call_args.kwargs["max_turns"] == 1
    assert runner.call_args.kwargs["run_config"].tracing_disabled is True
    assert runner.call_args.kwargs["run_config"].trace_include_sensitive_data is False
