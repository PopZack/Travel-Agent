"""聊天 API 的请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChoiceOption(BaseModel):
    """追问选项。"""

    label: str               # 显示文字，如 "东京"
    value: str               # 选中后回传的值，如 "东京"
    description: str | None = None  # 可选描述


class QuestionField(BaseModel):
    """一个缺失字段的追问结构。"""

    field: str               # 字段名，如 "destination"
    question: str            # 提问文字，如 "你想去哪里？"
    options: list[ChoiceOption] = []  # 可选项（选择式追问）
    input_type: str = "select"  # select / text / number


class ChatRequest(BaseModel):
    """POST /api/chat 请求。"""

    message: str = Field(..., description="用户消息")
    conversation_id: str | None = Field(default=None, description="会话 ID，不传则新建")


class ChatResponse(BaseModel):
    """POST /api/chat 响应。"""

    conversation_id: str
    response: str
    status: str = "done"
    plan: dict | None = None
    needs_more_info: bool = False
    missing_fields: list[str] = []
    questions: list[QuestionField] = []  # 结构化追问选项


class SSEEvent(BaseModel):
    """SSE 流式事件。"""

    event: str  # status / chunk / done / error
    data: str | dict | None = None
