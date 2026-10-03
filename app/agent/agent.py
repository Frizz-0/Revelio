"""The investigation agent loop and its small runtime data models."""

import json
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from app.services.llm import LLMService
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

    def __init__(
        self,
        capabilities,
        max_tool_calls: int = 5,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.capabilities = capabilities
        self.max_tool_calls = max_tool_calls
        self.on_event = on_event
        self.model = LLMService(
            on_usage=lambda details: self._emit("model_usage", stage="agent_decision", **details)
        )

    def _emit(self, event: str, **details: Any) -> None:
        if self.on_event is not None:
            self.on_event({"event": event, **details})

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
                    "and use its observed result. For factual research, inspect "
                    "attached images first when present by calling analyze_image "
                    "with the next unprocessed image_index from its metadata. Analyze "
                    "each attached image once before choosing a follow-up action. Visual observations "
                    "are model-generated and are not independently verified quotes. "
                    "Use outside search when the user asks for facts beyond what is "
                    "visible in the image. Inspect uploaded documents first when present, and search for outside "
                    "corroboration or gaps when useful; otherwise search first and "
                    "research those actual search observations. "
                    "Research fetches source "
                    "pages, extracts exact quotations, and verifies a finding "
                    "against those quotations. Base synthesis on the verified "
                    "finding, cite its source URLs, never present a single-source "
                    "finding as established fact, and state uncertainty or "
                    "insufficient evidence. Do not invent or resend evidence in "
                    "research arguments. "
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
        action = self._normalize_action(AgentAction.model_validate_json(raw))

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
            )
            action = self._normalize_action(AgentAction.model_validate_json(raw))
        if action.action_type == "respond" and action.response and (
            action.tool is not None or action.arguments
        ):
            print("[Agent] Ignoring stray tool fields on a completed response action.")
            action = action.model_copy(update={"tool": None, "arguments": {}})
        return action

    @staticmethod
    def _normalize_action(action: AgentAction) -> AgentAction:
        """Repair the common JSON shape where the model calls respond a tool."""
        if action.action_type == "tool" and action.tool == "respond":
            response = action.response
            if not response:
                response = next(
                    (
                        action.arguments.get(key)
                        for key in ("response", "answer", "content")
                        if isinstance(action.arguments.get(key), str)
                        and action.arguments.get(key).strip()
                    ),
                    None,
                )
            if response:
                print("[Agent] Normalized respond mislabeled as a tool action.")
                return AgentAction(
                    action_type="respond",
                    response=response,
                    reason=action.reason,
                )
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

        available = {item["name"] for item in self.capabilities.describe()}

        def unpack(candidate: Any) -> AgentAction | None:
            if isinstance(candidate, str):
                try:
                    candidate = json.loads(candidate)
                except json.JSONDecodeError:
                    return None
            if not isinstance(candidate, dict):
                return None

            # Recover valid final-answer actions nested in a provider wrapper.
            if candidate.get("action_type") == "respond":
                response = candidate.get("response") or candidate.get("answer")
                if isinstance(response, str) and response.strip():
                    return AgentAction(
                        action_type="respond",
                        response=response,
                        reason=candidate.get("reason", "Recovered final answer from provider output."),
                    )

            # Some Groq responses wrap Revelio's JSON decision as the
            # arguments to a provider-level agent function.
            if candidate.get("action_type") == "tool":
                tool = candidate.get("tool")
                arguments = candidate.get("arguments", {})
                if tool == "respond":
                    response = candidate.get("response")
                    if not response and isinstance(arguments, dict):
                        response = arguments.get("response") or arguments.get("answer") or arguments.get("content")
                    if isinstance(response, str) and response.strip():
                        return AgentAction(
                            action_type="respond",
                            response=response,
                            reason=candidate.get("reason", "Recovered final answer from provider output."),
                        )
                if tool in available and isinstance(arguments, dict):
                    return AgentAction(
                        action_type="tool",
                        tool=tool,
                        arguments=arguments,
                        reason="Recovered a nested Revelio action from provider output.",
                    )

            name = candidate.get("name") or candidate.get("tool")
            arguments = candidate.get("arguments", {})
            if name in available and isinstance(arguments, dict):
                return AgentAction(
                    action_type="tool",
                    tool=name,
                    arguments=arguments,
                    reason="Recovered the registered capability from provider output.",
                )

            for key in ("arguments", "input", "parameters", "action"):
                recovered_action = unpack(candidate.get(key))
                if recovered_action is not None:
                    return recovered_action
            return None

        return unpack(payload)

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
    def _available_sources(state: AgentState) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        # Prefer the latest search results, then include any supplied documents.
        for observation in reversed(state.observations):
            if observation.tool not in {"search", "document"} or not observation.success:
                continue
            if not isinstance(observation.output, list):
                continue
            for item in observation.output:
                if not isinstance(item, dict):
                    continue
                url = item.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    results.append(item)
        return results

    @staticmethod
    def _insufficient_answer(goal: str, research: dict[str, Any]) -> str:
        finding = research.get("finding") or {}
        answer = (
            f"The available evidence does not establish an answer to: {goal}. "
            "The evidence verifier marked this finding insufficient, so I will not present a conclusion as established."
        )
        caveats = finding.get("caveats") or []
        safe_caveats = []
        for caveat in caveats:
            if not isinstance(caveat, str):
                continue
            if "rate_limit_exceeded" in caveat or "Rate limit reached" in caveat:
                safe_caveats.append(
                    "The evidence verifier hit the model provider's rate limit, so the claims were not verified."
                )
            else:
                safe_caveats.append(caveat)
        if safe_caveats:
            answer += "\n\nCaveats: " + " ".join(safe_caveats)
        sources = research.get("sources") or []
        source_links = [
            f"{source.get('title') or source.get('url')}: {source.get('url')}"
            for source in sources
            if isinstance(source, dict) and source.get("url")
        ]
        if source_links:
            answer += "\n\nSources fetched for review: " + "; ".join(source_links)
        return answer

    @staticmethod
    def _preview(value: Any, limit: int = 700) -> str:
        rendered = json.dumps(value, ensure_ascii=False, default=str)
        return rendered if len(rendered) <= limit else rendered[:limit] + "…"

    def run(self, state: AgentState) -> AgentState:
        state.status = "running"
        print(f"[Agent] Goal: {state.goal}")
        self._emit("started", goal=state.goal)
        documents = next(
            (item.output for item in state.observations if item.tool == "document" and item.success),
            [],
        )
        if documents:
            self._emit("documents_loaded", documents=documents)
        images = next(
            (item.output for item in state.observations if item.tool == "image" and item.success),
            [],
        )
        if images:
            self._emit("images_loaded", images=images)

        while not state.finished:
            state.iteration += 1
            self._emit("decision_started", step=state.iteration)
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
                self._emit("failed", error=message, state=state.model_dump(mode="json"))
                break
            analyzed_images = {
                observation.output.get("image_index")
                for observation in state.observations
                if observation.tool == "analyze_image"
                and observation.success
                and isinstance(observation.output, dict)
            }
            next_image_index = next(
                (image.get("image_index") for image in images if image.get("image_index") not in analyzed_images),
                None,
            )
            if next_image_index is not None and (
                action.action_type != "tool"
                or action.tool != "analyze_image"
                or action.arguments.get("image_index") != next_image_index
            ):
                action = AgentAction(
                    action_type="tool",
                    tool="analyze_image",
                    arguments={"image_index": next_image_index, "task": state.goal},
                    reason="Inspect every attached image before choosing follow-up analysis.",
                )
                print(f"[Agent] Routing attached image {next_image_index} through vision analysis before follow-up decisions.")
            self._emit(
                "action_selected",
                step=state.iteration,
                action=action.model_dump(mode="json"),
            )
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
                elif not self._available_sources(state) and not any(
                    o.tool == "analyze_image" and o.success for o in state.observations
                ):
                    error = "Provide documents or search for evidence before answering an investigation goal."
                elif self._available_sources(state) and not any(
                    o.tool == "research" and o.success for o in state.observations
                ):
                    error = "Analyze and verify the collected search evidence with research before answering."
                if error:
                    print(f"[Agent] Rejected response: {error}")
                    state.observations.append(
                        AgentObservation(tool="agent", success=False, error=error)
                    )
                    self._emit("action_rejected", step=state.iteration, error=error)
                    continue

            if (
                action.action_type == "tool"
                and action.tool == "search"
                and any(
                    observation.tool in {"search", "document"} and observation.success
                    for observation in state.observations
                )
                and not any(
                    observation.tool == "research" and observation.success
                    for observation in state.observations
                )
            ):
                print("[Agent] Reusing supplied documents or search results; proceeding to research.")
                action = AgentAction(
                    action_type="tool",
                    tool="research",
                    arguments={"question": state.goal, "data": self._available_sources(state)},
                    reason="Source documents are already available; proceed to research.",
                )

            if action.action_type == "tool" and action.tool == "research":
                evidence = self._available_sources(state)
                if not evidence:
                    error = "Provide documents or search for evidence before invoking research."
                    print(f"[Agent] Rejected action: {error}")
                    state.observations.append(
                        AgentObservation(tool="agent", success=False, error=error)
                    )
                    self._emit("action_rejected", step=state.iteration, error=error)
                    continue
                # Bind research to uploaded or actual search sources, not model-authored data.
                action = action.model_copy(update={
                    "arguments": {
                        "question": action.arguments.get("question") or state.goal,
                        "data": evidence,
                    }
                })

            if action.action_type == "respond":
                research = next(
                    (
                        observation.output
                        for observation in reversed(state.observations)
                        if observation.tool == "research"
                        and observation.success
                        and isinstance(observation.output, dict)
                    ),
                    None,
                )
                finding = research.get("finding") if research else None
                if isinstance(finding, dict) and finding.get("status") == "insufficient":
                    action = action.model_copy(update={
                        "response": self._insufficient_answer(state.goal, research),
                        "tool": None,
                        "arguments": {},
                    })
                    print("[Agent] Replaced speculative synthesis because evidence is insufficient.")
                    self._emit("synthesis_guarded", reason="insufficient_evidence")

            error = self._validate(action)
            if error:
                print(f"[Agent] Invalid action: {error}")
                state.observations.append(AgentObservation(tool="agent", success=False, error=error))
                state.status = "failed"
                state.final_answer = error
                self._emit("failed", error=error, state=state.model_dump(mode="json"))
                break

            if action.action_type in {"respond", "finish"}:
                state.action_history.append(action)
                state.final_answer = action.response
                state.status = "completed"
                self._emit("completed", state=state.model_dump(mode="json"))
                break

            error = self._check_tool_policy(action, state)
            if error:
                print(f"[Agent] Blocked action: {error}")
                state.observations.append(
                    AgentObservation(tool=action.tool or "agent", success=False, error=error)
                )
                state.status = "failed"
                state.final_answer = error
                self._emit("failed", error=error, state=state.model_dump(mode="json"))
                break

            state.action_history.append(action)
            self._emit(
                "tool_started",
                step=state.iteration,
                tool=action.tool,
                arguments=action.arguments,
            )
            print(f"[Tool] {action.tool} started; arguments={self._preview(action.arguments)}")
            try:
                output = self.capabilities.execute(action.tool, action.arguments)
                observation = AgentObservation(tool=action.tool or "", success=True, output=output)
                self._emit(
                    "tool_finished",
                    step=state.iteration,
                    tool=action.tool,
                    success=True,
                    output=output,
                )
                print(f"[Tool] {action.tool} succeeded; output={self._preview(output)}")
            except Exception as exc:
                observation = AgentObservation(
                    tool=action.tool or "",
                    success=False,
                    error=str(exc),
                )
                self._emit(
                    "tool_finished",
                    step=state.iteration,
                    tool=action.tool,
                    success=False,
                    error=str(exc),
                )
                print(f"[Tool] {action.tool} failed; error={exc}")
            state.observations.append(observation)
            if (
                action.tool == "analyze_image"
                and not observation.success
                and ("rate_limit_exceeded" in (observation.error or "") or "429" in (observation.error or ""))
            ):
                state.status = "failed"
                state.final_answer = (
                    "Image analysis was rate-limited by Groq. Wait for the quota window to reset, "
                    "then try again."
                )
                self._emit(
                    "failed",
                    error=state.final_answer,
                    state=state.model_dump(mode="json"),
                )
                break

        if state.status == "running":
            state.status = "failed"
            state.final_answer = f"Stopped after reaching the {state.max_iterations}-step limit."
            self._emit(
                "failed",
                error=state.final_answer,
                state=state.model_dump(mode="json"),
            )

        print(f"[Agent] Finished with status={state.status} after {state.iteration} step(s).")
        self._emit("finished", status=state.status, steps=state.iteration)
        return state
