"""LLM 调用封装。

用 AsyncOpenAI 替代同步 OpenAI，适配 FastAPI 异步环境。
复用 extract_json / _repair_truncated_json 逻辑。
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from openai import AsyncOpenAI

from app.common.config import get_settings


@lru_cache
def get_client() -> AsyncOpenAI:
    s = get_settings()
    return AsyncOpenAI(
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
    )


async def chat(system: str, user: str, *, max_tokens: int = 1024, model: str | None = None) -> str:
    """异步调一次 chat completion，返回纯文本。"""
    s = get_settings()
    client = get_client()
    resp = await client.chat.completions.create(
        model=model or s.llm_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


async def chat_stream(system: str, user: str, *, max_tokens: int = 1024, model: str | None = None):
    """异步流式 chat completion，逐 chunk yield 文本片段。"""
    s = get_settings()
    client = get_client()
    stream = await client.chat.completions.create(
        model=model or s.llm_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def extract_json(text: str) -> dict:
    """从 LLM 输出里提取 JSON。处理代码块包裹、前后多余文字、截断。"""
    text = text.strip()

    # 去掉 markdown 代码块
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()

    # 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 找第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    # 尝试修复截断
    if start != -1:
        snippet = text[start:]
        repaired = _repair_truncated_json(snippet)
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"无法从 LLM 输出提取 JSON：{text[-300:]}")


def _repair_truncated_json(s: str) -> str | None:
    """尝试修复被截断的 JSON：按栈补全闭合括号。"""
    stack: list[str] = []
    in_string = False
    escape = False

    for ch in s:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in ("}", "]"):
            if stack and stack[-1] == ch:
                stack.pop()

    result = s
    if in_string:
        result += '"'
    result += "".join(reversed(stack))
    return result
