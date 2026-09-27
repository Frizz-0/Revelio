import json

from app.agent.actions import AgentAction
from app.agent.state import AgentState
from app.agent.memory import AgentMemory
from app.services.model_router import ModelRouter


class AgentDecisionService:

    def __init__(self):
        self.model_router = ModelRouter()

    def decide(
        self,
        state: AgentState,
        capabilities: list[dict],
        memory: AgentMemory,
    ) -> AgentAction:

        capability_descriptions = json.dumps(
            capabilities,
            ensure_ascii=False,
        )

        messages = [
    {
        "role": "system",
        "content": (
            "You are the decision component of Revelio.\n"
            "You only return a JSON decision.\n\n"

            "IMPORTANT:\n"
            "You are NOT using function calling or tool calling.\n"
            "Do NOT emit a tool call.\n"
            "Do NOT emit a function call.\n"
            "Do NOT wrap the JSON in an assistant/tool/function structure.\n"
            "Return the AgentAction JSON object directly.\n\n"

            "Available capabilities:\n"
            f"{capability_descriptions}\n\n"

            "Rules:\n"
            "1. Return a JSON object describing the next action.\n"
            "2. If information or computation is required, "
            "set action_type='tool'.\n"
            "3. The tool field must exactly match an available capability.\n"
            "4. The arguments object must match that capability's schema.\n"
            "5. Do not invent argument names.\n"
            "6. Use action_type='respond' when you can answer directly.\n"
            "7. For respond, tool must be null and arguments must be {}.\n"
            "8. Use action_type='finish' when the goal is complete.\n"
            "9. For finish, tool must be null and arguments must be {}.\n"
            "10. Never perform exact arithmetic yourself. "
            "Use the calculator capability.\n\n"

            "Return ONLY the AgentAction JSON object."
        ),
    },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "goal": state.goal,
                        "status": state.status,
                        "iteration": state.iteration,
                        "memory": memory.summary(),
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        response_format = {
            "type": "json_object"
        }

        raw = self.model_router.generate(
            messages,
            response_format=response_format,
            capability="reasoning",
        )

        return AgentAction.model_validate_json(raw)