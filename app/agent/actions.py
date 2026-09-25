from typing import Any, Literal
from pydantic import BaseModel, Field


class AgentAction(BaseModel):
    action_type: Literal["tool", "respond", "finish"]

    tool: str | None = None

    arguments: dict[str, Any] = Field(default_factory=dict)

    response: str | None = None

    reason: str = ""