from app.agent.actions import AgentAction
from app.agent.state import AgentState


class ActionGuard:

    def validate(
        self,
        action: AgentAction,
        state: AgentState,
    ) -> str | None:

        if action.action_type == "tool":

            if not action.tool:
                return "Tool action requires a capability name."

            if not action.arguments:
                return "Tool action requires arguments."

        if action.action_type == "respond":

            if not action.response:
                return "Respond action requires a response."

            if action.tool is not None:
                return "Respond action cannot specify a capability."

            if action.arguments:
                return "Respond action must have empty arguments."

        if action.action_type == "finish":

            if action.tool is not None:
                return "Finish action cannot specify a capability."

            if action.arguments:
                return "Finish action must have empty arguments."

        return None