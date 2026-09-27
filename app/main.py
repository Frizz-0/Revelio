"""Command-line entry point for the Revelio V1 agent."""

import argparse

from app.agent import Agent, AgentAction, AgentObservation, AgentState
from app.tools.calculator import calculate, expression_from_goal


def run(goal: str) -> AgentState:
    # Pure arithmetic should not spend an LLM call deciding to use Python.
    expression = expression_from_goal(goal)
    if expression is not None:
        print("[Agent] Routed pure arithmetic to Python calculator; no LLM decision needed.")
        print(f"[Tool] calculator started; expression={expression}")
        try:
            result = calculate(expression)
        except ValueError as exc:
            print(f"[Tool] calculator failed; error={exc}")
            return AgentState(
                goal=goal,
                status="failed",
                final_answer=f"Could not calculate that expression: {exc}",
                observations=[AgentObservation(
                    tool="calculator",
                    success=False,
                    error=str(exc),
                )],
            )
        answer = str(result)
        print(f"[Tool] calculator succeeded; output={answer}")
        return AgentState(
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

    from app.agent.capabilities import build_capability_registry

    agent = Agent(capabilities=build_capability_registry())
    return agent.run(AgentState(goal=goal))


def main() -> None:
    parser = argparse.ArgumentParser(description="Revelio V1 research agent")
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
