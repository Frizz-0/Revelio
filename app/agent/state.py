from typing import Any, Literal
from pydantic import BaseModel, Field


class AgentObservation(BaseModel):
    tool: str
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    goal: str

    status: Literal[
        "idle",
        "running",
        "completed",
        "failed",
    ] = "idle"

    plan: list[str] = Field(default_factory=list)

    observations: list[AgentObservation] = Field(
        default_factory=list
    )

    action_history: list["AgentAction"] = Field(
        default_factory=list
    )

    iteration: int = 0

    max_iterations: int = 10

    def add_observation(self, observation: AgentObservation):
        self.observations.append(observation)

    def add_action(self, action: "AgentAction"):
        self.action_history.append(action)

    @property
    def finished(self) -> bool:
        return self.status in {"completed", "failed"} \
            or self.iteration >= self.max_iterations


from app.agent.actions import AgentAction
AgentState.model_rebuild()