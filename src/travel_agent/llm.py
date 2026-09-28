"""LLM 调用封装。

火山方舟（字节跳动）提供 OpenAI 兼容接口，故用 openai SDK。
统一在这里构造 client，节点调用 ``chat(system, user)`` 拿纯文本。
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from openai import OpenAI

from travel_agent.config import get_settings


@lru_cache
def get_client() -> OpenAI:
    s = get_settings()
    return OpenAI(
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
    )


def chat(system: str, user: str, *, max_tokens: int = 1024, model: str | None = None) -> str:
    """同步调一次 chat completion，返回纯文本。

    节点是 async 但 LLM 调用是同步阻塞；LangGraph 节点本身不在事件循环里跑，
    故直接同步调用即可。若后续要并发可包 asyncio.to_thread。
    """
    s = get_settings()
    client = get_client()
    resp = client.chat.completions.create(
        model=model or s.llm_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


def chat_stream(system: str, user: str, *, max_tokens: int = 1024, model: str | None = None):
    """流式调 chat completion，逐 chunk yield 文本片段。

    用法：
        for chunk in chat_stream(system, user):
            print(chunk, end="", flush=True)
    或在 Streamlit 里：
        st.write_stream(chat_stream(system, user))
    """
    s = get_settings()
    client = get_client()
    stream = client.chat.completions.create(
        model=model or s.llm_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def extract_json(text: str) -> dict:
    """从 LLM 输出里提取 JSON。

    处理：markdown 代码块包裹、前后多余文字、首尾空白、输出截断。
    """
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

    # 尝试找第一个 { 到最后一个 } 之间的内容
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    # 输出可能被截断：尝试补全缺失的引号和括号
    if start != -1:
        snippet = text[start:]
        repaired = _repair_truncated_json(snippet)
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"无法从 LLM 输出提取 JSON（可能被截断）：{text[-300:]}")


def _repair_truncated_json(s: str) -> str | None:
    """尝试修复被截断的 JSON 字符串。

    用栈记录每层开括号类型，末尾按反序补全闭合；
    若截断在字符串中间，先补引号。
    """
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
    # 按栈反序补全（内层先闭）
    result += "".join(reversed(stack))
    return result




