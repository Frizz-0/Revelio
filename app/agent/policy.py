from app.agent.actions import AgentAction
from app.agent.state import AgentState


class ActionPolicy:

    def __init__(self, max_tool_calls: int = 5):
        self.max_tool_calls = max_tool_calls

    def check(
        self,
        action: AgentAction,
        state: AgentState,
    ) -> str | None:

        if action.action_type != "tool":
            return None

        tool_calls = sum(
            1
            for a in state.action_history
            if a.action_type == "tool"
        )

        if tool_calls >= self.max_tool_calls:
            return (
                f"Tool-call limit reached "
                f"({self.max_tool_calls})."
            )

        # Prevent exact duplicate tool calls.
        for previous in state.action_history:

            if (
                previous.action_type == "tool"
                and previous.tool == action.tool
                and previous.arguments == action.arguments
            ):
                return (
                    "Duplicate tool action detected."
                )

        return None