"""OpenAI Agents SDK 模型适配器；业务层只依赖窄 LlmClient 协议。"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Protocol

from agents import (
    Agent,
    AsyncOpenAI,
    ModelSettings,
    OpenAIChatCompletionsModel,
    OpenAIResponsesModel,
    RunConfig,
    Runner,
)
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger(__name__)


class LlmClient(Protocol):
    def complete(self, prompt: str, max_tokens: int = 6000) -> str:
        """返回模型生成的纯文本。"""


ROLE_INSTRUCTIONS = {
    "research-generator": "你是严谨的科研生成 Agent。只依据输入证据工作，并严格遵守用户要求的输出格式。",
    "skeptical-reviewer": "你是独立的科研审稿 Agent。优先寻找不可证伪、证据不足和实验泄漏问题。",
}


class AgentsSdkLlmClient:
    """统一使用 Agents SDK；第三方模型交给 SDK 自带的 LiteLLM 适配层。"""

    def __init__(
        self,
        model: str,
        default_max_tokens: int,
        provider: str,
        role: str = "research-generator",
    ):
        self.model = model
        self.default_max_tokens = default_max_tokens
        self.provider = provider
        self.role = role
        self._sdk_model = None

    @property
    def sdk_model(self):
        """首次真正调用模型时再校验凭据，允许新安装先进入设置页。"""
        if self._sdk_model is None:
            self._sdk_model = self._build_model()
        return self._sdk_model

    def complete(self, prompt: str, max_tokens: int = 6000) -> str:
        max_tokens = min(max_tokens, self.default_max_tokens)
        agent = Agent(
            name=self.role,
            instructions=ROLE_INSTRUCTIONS.get(self.role, ROLE_INSTRUCTIONS["research-generator"]),
            model=self.sdk_model,
            model_settings=ModelSettings(max_tokens=max_tokens, include_usage=True),
        )
        tracing_enabled = (
            self.provider == "openai" and os.getenv("OPENAI_AGENTS_TRACING_ENABLED") == "1"
        )
        result = Runner.run_sync(
            agent,
            prompt,
            max_turns=1,
            run_config=RunConfig(
                tracing_disabled=not tracing_enabled,
                trace_include_sensitive_data=False,
                workflow_name=f"Agentic Research · {self.role}",
            ),
        )
        return str(result.final_output or "")

    def _build_model(self):
        model = self.model or _required_env(f"{self.provider.upper()}_MODEL_ID")
        if self.provider == "openai":
            return self._build_openai_model(model)
        if self.provider not in {"anthropic", "google"}:
            raise RuntimeError(f"不支持的模型供应商: {self.provider}")
        prefix = "anthropic" if self.provider == "anthropic" else "gemini"
        model_name = model if "/" in model else f"{prefix}/{model}"
        return LitellmModel(
            model=model_name,
            base_url=_required_env(f"{self.provider.upper()}_BASE_URL"),
            api_key=_required_env(f"{self.provider.upper()}_API_KEY"),
        )

    def _build_openai_model(self, model: str):
        client = AsyncOpenAI(
            api_key=_required_env("OPENAI_API_KEY"),
            base_url=_required_env("OPENAI_BASE_URL"),
        )
        api_mode = _required_env("OPENAI_API_MODE")
        if api_mode == "responses":
            return OpenAIResponsesModel(model=model, openai_client=client)
        if api_mode == "chat_completions":
            return OpenAIChatCompletionsModel(model=model, openai_client=client)
        raise RuntimeError("OPENAI_API_MODE 必须是 responses 或 chat_completions")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"缺少 {name}")
    return value.strip()


# ---------------------------------------------------------------------------
# JSON 解析与修复
# ---------------------------------------------------------------------------

def _repair_truncated_json(text: str) -> str | None:
    if not (repaired := (text or "").rstrip()):
        return None
    stack, in_str, i = [], False, 0
    while i < len(repaired):
        if repaired[i] == "\\" and in_str:
            i += 2
            continue
        if repaired[i] == '"':
            in_str = not in_str
        elif not in_str:
            if repaired[i] in "{[":
                stack.append(repaired[i])
            elif (
                repaired[i] == "}" and stack and stack[-1] == "{"
            ) or (
                repaired[i] == "]" and stack and stack[-1] == "["
            ):
                stack.pop()
        i += 1
    if in_str:
        repaired += '"'
    if repaired and repaired[-1] == ",":
        repaired = repaired[:-1]
    return repaired + "".join("}" if b == "{" else "]" for b in reversed(stack))



def extract_json(text: str) -> Any:
    """从模型回复中提取 JSON，支持截断修复。"""
    stripped = text.strip()

    # 去除 markdown 代码块标记
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()

    # 1) 直接解析
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 2) 定位 JSON 起始位置后解析
    starts = [index for index in (stripped.find("{"), stripped.find("[")) if index >= 0]
    if not starts:
        raise ValueError("模型回复中没有 JSON") from None

    json_text = stripped[min(starts):]
    decoder = json.JSONDecoder()
    try:
        payload, _ = decoder.raw_decode(json_text)
        return payload
    except json.JSONDecodeError:
        pass

    # 3) 尝试修复截断的 JSON
    repaired = _repair_truncated_json(json_text)
    if repaired:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        # 修复后再尝试 raw_decode
        try:
            payload, _ = decoder.raw_decode(repaired)
            return payload
        except json.JSONDecodeError:
            pass

    # 所有尝试均失败
    raise ValueError("模型回复中没有合法 JSON（已尝试自动修复）") from None


def extract_json_with_retry(
    client: LlmClient,
    prompt: str,
    *,
    max_retries: int = 2,
    max_tokens: int = 6000,
) -> Any:
    """调用 LLM 并提取 JSON，失败时带错误反馈重试。

    每次重试会将上次的错误信息追加到 prompt 中，
    引导模型纠正输出格式。
    """
    last_error: Exception | None = None
    current_prompt = prompt

    for attempt in range(1 + max_retries):
        try:
            response = client.complete(current_prompt, max_tokens=max_tokens)
            return extract_json(response)
        except (ValueError, json.JSONDecodeError) as error:
            last_error = error
            logger.warning(
                "JSON 解析失败（第 %d/%d 次尝试）: %s",
                attempt + 1,
                1 + max_retries,
                error,
            )
            if attempt < max_retries:
                # 构造带有错误反馈的重试 prompt
                current_prompt = (
                    f"{prompt}\n\n"
                    f"【重要纠正】你上一次的回复无法被解析为合法 JSON。"
                    f"错误信息：{error}\n"
                    f"请严格修正格式，只输出合法 JSON，不要包含任何其他文本。"
                    f"确保所有字符串正确闭合，所有括号正确匹配。"
                )

    raise ValueError(f"经过 {1 + max_retries} 次尝试仍无法获取合法 JSON: {last_error}") from last_error


class FakeLlmClient:
    """测试使用的确定性模型，不发起网络请求。"""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def complete(self, prompt: str, max_tokens: int = 6000) -> str:
        self.prompts.append(prompt)
        if not self.responses:
            raise RuntimeError("FakeLlmClient 没有剩余回复")
        return self.responses.pop(0)
