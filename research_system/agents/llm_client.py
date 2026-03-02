import os
from typing import Optional
import openai
from anthropic import Anthropic
import google.generativeai as genai

def call_llm(prompt: str, model: str = "gpt-4o", max_tokens: int = 4000) -> str:
    """
    统一的 LLM 调用接口，支持 OpenAI, Anthropic 和 Google Gemini。
    """
    if model.startswith("gpt"):
        return _call_openai(prompt, model, max_tokens)
    elif model.startswith("claude"):
        return _call_anthropic(prompt, model, max_tokens)
    elif model.startswith("gemini"):
        return _call_gemini(prompt, model, max_tokens)
    else:
        # 默认使用 OpenAI
        return _call_openai(prompt, model, max_tokens)

def _call_openai(prompt: str, model: str, max_tokens: int) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 未设置")
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def _call_anthropic(prompt: str, model: str, max_tokens: int) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY 未设置")
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def _call_gemini(prompt: str, model: str, max_tokens: int) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY 未设置")
    genai.configure(api_key=api_key)
    # 转换模型名称，如果是 gemini-1.5-flash 之类的
    model_instance = genai.GenerativeModel(model)
    response = model_instance.generate_content(prompt)
    return response.text
