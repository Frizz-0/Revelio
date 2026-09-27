"""The investigation agent loop and its small runtime data models."""

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.tools.calculator import goal_requires_calculator


class AgentAction(BaseModel):
    action_type: Literal["tool", "respond", "finish"]
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    response: str | None = None
    reason: str = ""


class AgentObservation(BaseModel):
    tool: str
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    goal: str
    final_answer: str | None = None
    status: Literal["idle", "running", "completed", "failed"] = "idle"
    observations: list[AgentObservation] = Field(default_factory=list)
    action_history: list[AgentAction] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 10

    @property
    def finished(self) -> bool:
        return self.status in {"completed", "failed"} or self.iteration >= self.max_iterations


class Agent:
    """Choose, execute, and observe capability actions until answering."""

    def __init__(self, capabilities, max_tool_calls: int = 5):
        from app.services.model_router import ModelRouter

        self.capabilities = capabilities
        self.max_tool_calls = max_tool_calls
        self.model = ModelRouter()

    def _decide(self, state: AgentState) -> AgentAction:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Revelio's investigation agent. Choose one next action; "
                    "capabilities execute outside the model. Do NOT use native "
                    "function calling or emit a provider tool call. Do NOT return "
                    "a function/tool wrapper. Capabilities are names in Revelio's "
                    "JSON action protocol only. Return only a JSON "
                    "AgentAction with action_type tool/respond, tool, arguments, "
                    "response, and reason. For tool actions, name an available "
                    "capability and follow its input schema. For respond, provide "
                    "a complete non-empty response, tool=null, and arguments={}. "
                    "Never calculate exact arithmetic yourself: call calculator "
                    "and use its observed result. For factual research, use the "
                    "search capability first, then use research on those actual "
                    "search observations before answering. Research performs both "
                    "analysis and evidence verification. Do not invent or resend "
                    "evidence in research arguments. "
                    "Do not use finish; respond with the answer."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "goal": state.goal,
                        "step": state.iteration,
                        "capabilities": self.capabilities.describe(),
                        "actions": [a.model_dump(mode="json") for a in state.action_history[-5:]],
                        "observations": [o.model_dump(mode="json") for o in state.observations[-5:]],
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        try:
            raw = self.model.generate(
                messages,
                response_format={"type": "json_object"},
                capability="reasoning",
            )
        except Exception as exc:
            recovered = self._recover_provider_tool_call(exc)
            if recovered is None:
                raise
            print(
                f"[Agent] Converted provider tool-call format to Revelio action: "
                f"{recovered.tool}"
            )
            return recovered
        action = AgentAction.model_validate_json(raw)

        if action.action_type == "respond" and not action.response:
            correction = messages + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        "The previous JSON omitted the required answer. Return a "
                        "corrected respond action with a non-empty response based "
                        "on the observations. Do not return another action."
                    ),
                },
            ]
            raw = self.model.generate(
                correction,
                response_format={"type": "json_object"},
                capability="reasoning",
            )
            action = AgentAction.model_validate_json(raw)
        return action

    def _recover_provider_tool_call(self, error: Exception) -> AgentAction | None:
        """Convert a provider's failed native-call payload to our JSON action."""
        body = getattr(error, "body", None)
        error_body = body.get("error", body) if isinstance(body, dict) else {}
        generation = (
            error_body.get("failed_generation")
            if isinstance(error_body, dict)
            else None
        )
        if not isinstance(generation, str):
            return None
        try:
            payload = json.loads(generation)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None

        name = payload.get("name") or payload.get("tool")
        arguments = payload.get("arguments", {})
        available = {item["name"] for item in self.capabilities.describe()}
        if name not in available or not isinstance(arguments, dict):
            return None
        return AgentAction(
            action_type="tool",
            tool=name,
            arguments=arguments,
            reason="Recovered the registered capability from provider output.",
        )

    @staticmethod
    def _validate(action: AgentAction) -> str | None:
        if action.action_type == "tool":
            if not action.tool:
                return "Tool action requires a capability name."
            if not action.arguments:
                return "Tool action requires arguments."
        elif action.action_type == "respond":
            if not action.response:
                return "Respond action requires a response."
            if action.tool is not None or action.arguments:
                return "Respond action cannot include a tool or arguments."
        elif action.action_type == "finish":
            if not action.response:
                return "Finish action requires a final response."
            if action.tool is not None or action.arguments:
                return "Finish action cannot include a tool or arguments."
        return None

    def _check_tool_policy(self, action: AgentAction, state: AgentState) -> str | None:
        tool_actions = [a for a in state.action_history if a.action_type == "tool"]
        if len(tool_actions) >= self.max_tool_calls:
            return f"Tool-call limit reached ({self.max_tool_calls})."
        if any(a.tool == action.tool and a.arguments == action.arguments for a in tool_actions):
            return "Duplicate tool action detected."
        return None

    @staticmethod
    def _search_evidence(state: AgentState) -> list[dict[str, Any]]:
        return [
            item
            for observation in state.observations
            if observation.tool == "search" and observation.success
            and isinstance(observation.output, list)
            for item in observation.output
            if isinstance(item, dict)
        ]

    @staticmethod
    def _preview(value: Any, limit: int = 700) -> str:
        rendered = json.dumps(value, ensure_ascii=False, default=str)
        return rendered if len(rendered) <= limit else rendered[:limit] + "…"

    def run(self, state: AgentState) -> AgentState:
        state.status = "running"
        print(f"[Agent] Goal: {state.goal}")

        while not state.finished:
            state.iteration += 1
            try:
                action = self._decide(state)
            except Exception as exc:
                message = f"Decision model failed: {exc}"
                print(f"[Agent] {message}")
                state.observations.append(
                    AgentObservation(tool="agent", success=False, error=message)
                )
                state.final_answer = message
                state.status = "failed"
                break
            print(
                f"[Agent] Step {state.iteration}: {action.action_type}"
                + (f" {action.tool}" if action.tool else "")
                + (f" — {action.reason}" if action.reason else "")
            )

            if action.action_type == "respond":
                error = None
                if goal_requires_calculator(state.goal) and not any(
                    o.tool == "calculator" and o.success for o in state.observations
                ):
                    error = "Use calculator and observe its result before answering the requested calculation."
                elif not self._search_evidence(state):
                    error = "Search for evidence before answering an investigation goal."
                elif not any(
                    o.tool == "research" and o.success for o in state.observations
                ):
                    error = "Analyze and verify the collected search evidence with research before answering."
                if error:
                    print(f"[Agent] Rejected response: {error}")
                    state.observations.append(
                        AgentObservation(tool="agent", success=False, error=error)
                    )
                    continue

            if action.action_type == "tool" and action.tool == "research":
                evidence = self._search_evidence(state)
                if not evidence:
                    error = "Search for evidence before invoking research."
                    print(f"[Agent] Rejected action: {error}")
                    state.observations.append(
                        AgentObservation(tool="agent", success=False, error=error)
                    )
                    continue
                # Bind research to actual search results, not model-authored data.
                action = action.model_copy(update={
                    "arguments": {
                        "question": action.arguments.get("question") or state.goal,
                        "data": evidence,
                    }
                })

            error = self._validate(action)
            if error:
                print(f"[Agent] Invalid action: {error}")
                state.observations.append(AgentObservation(tool="agent", success=False, error=error))
                state.status = "failed"
                break

            if action.action_type in {"respond", "finish"}:
                state.action_history.append(action)
                state.final_answer = action.response
                state.status = "completed"
                break

            error = self._check_tool_policy(action, state)
            if error:
                print(f"[Agent] Blocked action: {error}")
                state.observations.append(
                    AgentObservation(tool=action.tool or "agent", success=False, error=error)
                )
                state.status = "failed"
                break

            state.action_history.append(action)
            print(f"[Tool] {action.tool} started; arguments={self._preview(action.arguments)}")
            try:
                output = self.capabilities.execute(action.tool, action.arguments)
                observation = AgentObservation(tool=action.tool or "", success=True, output=output)
                print(f"[Tool] {action.tool} succeeded; output={self._preview(output)}")
            except Exception as exc:
                observation = AgentObservation(
                    tool=action.tool or "",
                    success=False,
                    error=str(exc),
                )
                print(f"[Tool] {action.tool} failed; error={exc}")
            state.observations.append(observation)

        if state.status == "running":
            state.status = "failed"
            state.final_answer = f"Stopped after reaching the {state.max_iterations}-step limit."

        print(f"[Agent] Finished with status={state.status} after {state.iteration} step(s).")
        return state
