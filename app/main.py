"""Command-line entry point for Revelio investigations."""

import argparse
from typing import Any, Callable

from app.agent import Agent, AgentAction, AgentObservation, AgentState
from app.investigator.models import Document
from app.tools.calculator import calculate, expression_from_goal


def run(
    goal: str,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    documents: list[Document] | None = None,
    images=None,
) -> AgentState:
    documents = documents or []
    images = images or []
    # Pure arithmetic should not spend an LLM call deciding to use Python.
    expression = expression_from_goal(goal)
    if expression is not None and not documents and not images:
        if on_event:
            on_event({"event": "started", "goal": goal})
            on_event({"event": "tool_started", "tool": "calculator", "arguments": {"expression": expression}})
        print("[Agent] Routed pure arithmetic to Python calculator; no LLM decision needed.")
        print(f"[Tool] calculator started; expression={expression}")
        try:
            result = calculate(expression)
        except ValueError as exc:
            print(f"[Tool] calculator failed; error={exc}")
            result = AgentState(
                goal=goal,
                status="failed",
                final_answer=f"Could not calculate that expression: {exc}",
                observations=[AgentObservation(
                    tool="calculator",
                    success=False,
                    error=str(exc),
                )],
            )
            if on_event:
                on_event({"event": "tool_finished", "tool": "calculator", "success": False, "error": str(exc)})
                on_event({"event": "failed", "error": result.final_answer, "state": result.model_dump(mode="json")})
                on_event({"event": "finished", "status": result.status, "steps": 0})
            return result
        answer = str(result)
        print(f"[Tool] calculator succeeded; output={answer}")
        result = AgentState(
            goal=goal,
            status="completed",
            iteration=0,
            final_answer=answer,
            action_history=[AgentAction(
                action_type="tool",
                tool="calculator",
                arguments={"expression": expression},
                reason="Pure arithmetic is evaluated deterministically.",
            )],
            observations=[AgentObservation(
                tool="calculator",
                success=True,
                output=result,
            )],
        )
        if on_event:
            on_event({"event": "tool_finished", "tool": "calculator", "success": True, "output": result.observations[0].output})
            on_event({"event": "completed", "state": result.model_dump(mode="json")})
            on_event({"event": "finished", "status": result.status, "steps": 0})
        return result

    from app.agent.capabilities import build_capability_registry

    source_items = [
        {
            "title": document.title,
            "url": document.url,
            "snippet": document.content[:1200],
            "truncated": document.truncated or len(document.content) > 24000,
        }
        for document in documents
    ]
    image_items = [
        {"title": image.title, "image_index": index, "media_type": image.media_type}
        for index, image in enumerate(images)
    ]
    initial_observations = []
    if source_items:
        initial_observations.append(AgentObservation(tool="document", success=True, output=source_items))
    if image_items:
        initial_observations.append(AgentObservation(tool="image", success=True, output=image_items))
    state = AgentState(goal=goal, observations=initial_observations)
    registry = build_capability_registry(
        on_event=on_event,
        uploaded_documents={document.url: document for document in documents},
        uploaded_images=images,
    )
    agent = Agent(capabilities=registry, on_event=on_event)
    return agent.run(state)


def main() -> None:
    parser = argparse.ArgumentParser(description="Revelio investigation prototype")
    parser.add_argument("goal", nargs="*", help="Question or task for Revelio")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print the complete action and observation state as JSON.",
    )
    args = parser.parse_args()
    goal = " ".join(args.goal).strip()
    if not goal:
        goal = input("What should Revelio do? ").strip()
    if not goal:
        parser.error("provide a goal")

    result = run(goal)
    if result.final_answer:
        print(result.final_answer)
    elif result.status == "failed":
        failure = next(
            (observation.error for observation in reversed(result.observations)
             if observation.error),
            "The agent stopped without recording an error.",
        )
        print(f"Task failed: {failure}")
    else:
        print(f"Task {result.status} without a final answer.")
    if args.debug:
        print("[Debug] Final investigation state:")
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
