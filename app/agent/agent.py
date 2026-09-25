from app.agent.actions import AgentAction
from app.agent.state import (
    AgentState,
    AgentObservation,
)
from app.agent.decision import AgentDecisionService
from app.agent.tools import CapabilityRegistry
from app.agent.guards import ActionGuard
from app.agent.policy import ActionPolicy
from app.agent.memory import AgentMemory


class Agent:

    def __init__(
        self,
        capabilities : CapabilityRegistry | None = None,
    ):
        self.capabilities  = capabilities  or CapabilityRegistry()

        self.decision_service = AgentDecisionService()

        self.guard = ActionGuard()

        self.policy = ActionPolicy(
            max_tool_calls=5
        )

        self.memory = AgentMemory()

    def decide(
        self,
        state: AgentState,
    ) -> AgentAction:

        return self.decision_service.decide(
            state=state,
            capabilities =self.capabilities.describe(),
            memory=self.memory,
        )

    def execute(
        self,
        action: AgentAction,
    ) -> AgentObservation:

        try:

            output = self.capabilities.execute(
                action.tool,
                action.arguments,
            )

            return AgentObservation(
                tool=action.tool or "",
                success=True,
                output=output,
            )

        except Exception as e:

            return AgentObservation(
                tool=action.tool or "",
                success=False,
                error=str(e),
            )

    def run(
        self,
        state: AgentState,
    ) -> AgentState:

        state.status = "running"

        while not state.finished:

            state.iteration += 1

            action = self.decide(state)

            error = self.guard.validate(
                action,
                state,
            )

            if error:

                observation = AgentObservation(
                    tool=action.tool or "",
                    success=False,
                    error=error,
                )

                state.add_observation(observation)
                self.memory.add_observation(observation)

                state.status = "failed"

                break

            if action.action_type == "respond":

                state.add_action(action)
                self.memory.add_action(action)
                

                state.status = "completed"

                break

            if action.action_type == "finish":
                state.add_action(action)
                self.memory.add_action(action)
                
                state.status = "completed"

                break

            error = self.policy.check(
                action,
                state,
            )

            if error:

                observation = AgentObservation(
                    tool=action.tool or "",
                    success=False,
                    error=error,
                )

                state.add_observation(observation)
                self.memory.add_observation(observation)

                state.status = "failed"

                break

            state.add_action(action)
            self.memory.add_action(action)

            observation = self.execute(action)

            state.add_observation(observation)
            self.memory.add_observation(observation)

            if not observation.success:

                state.status = "failed"

                break

        return state