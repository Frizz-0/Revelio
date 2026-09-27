"""Manual end-to-end runner for the V1 investigation agent."""

from app.agent import Agent, AgentState
from app.agent.capabilities import build_capability_registry


def main() -> None:
    goal = input("What should Revelio investigate? ").strip()
    result = Agent(build_capability_registry()).run(AgentState(goal=goal))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
