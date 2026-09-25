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
            "You only return a JSON decision.\n"
            "You do not execute capabilities yourself.\n"
            "Do not explain your reasoning.\n"
            "Do not write prose before or after the JSON.\n"
            "Do not use markdown.\n\n"

            "Available capabilities:\n"
            f"{capability_descriptions}\n\n"

            "Rules:\n"
            "1. Use action_type='tool' when a capability is required.\n"
            "2. The tool field must exactly match one available capability.\n"
            "3. The arguments object must match the input_schema.\n"
            "4. Never invent argument names.\n"
            "5. Use action_type='respond' when you can answer directly.\n"
            "6. For respond, tool must be null and arguments must be {}.\n"
            "7. Use action_type='finish' when the goal is complete.\n"
            "8. For finish, tool must be null and arguments must be {}.\n\n"
            "10. Never perform exact arithmetic yourself. "
            "Always use the calculator capability for arithmetic.\n"

            "Valid JSON formats:\n"
            '{"action_type":"tool","tool":"<capability_name>",'
            '"arguments":{...},"response":null,"reason":""}\n'
            '{"action_type":"respond","tool":null,"arguments":{},'
            '"response":"...","reason":""}\n'
            '{"action_type":"finish","tool":null,"arguments":{},'
            '"response":null,"reason":""}\n\n'

            "Your entire response must be valid JSON and nothing else."
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