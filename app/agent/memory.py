from typing import Any

from app.agent.actions import AgentAction
from app.agent.state import AgentObservation


class AgentMemory:

    def __init__(self):
        self.actions: list[AgentAction] = []
        self.observations: list[AgentObservation] = []

    def add_action(self, action: AgentAction):
        self.actions.append(action)

    def add_observation(
        self,
        observation: AgentObservation,
    ):
        self.observations.append(observation)

    def recent_actions(
        self,
        limit: int = 5,
    ):
        return self.actions[-limit:]

    def recent_observations(
        self,
        limit: int = 5,
    ):
        return self.observations[-limit:]

    def summary(self) -> dict[str, Any]:

        return {
            "recent_actions": [
                action.model_dump()
                for action in self.recent_actions()
            ],
            "recent_observations": [
                observation.model_dump()
                for observation in self.recent_observations()
            ],
        }