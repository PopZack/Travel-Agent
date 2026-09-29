"""自定义异常。"""

from __future__ import annotations


class TravelAgentError(Exception):
    """Travel Agent 基础异常。"""


class LLMError(TravelAgentError):
    """LLM 调用失败。"""


class ToolError(TravelAgentError):
    """工具调用失败。"""


class ValidationError(TravelAgentError):
    """数据校验失败。"""


class NotFoundError(TravelAgentError):
    """资源不存在。"""
