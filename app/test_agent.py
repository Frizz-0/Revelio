from app.agent.agent import Agent
from app.agent.state import AgentState
from app.agent.tools import Capability, CapabilityRegistry

from app.services.search_service import SearXNGProvider
from app.tools.calculator import calculate


registry = CapabilityRegistry()

search_provider = SearXNGProvider()


def search_tool(query: str):
    return search_provider.search(query)


registry.register(
    Capability(
        name="search",
        description=(
            "Retrieve information from the web "
            "using a search query."
        ),
        execute=search_tool,
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string"
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    )
)

# registry.register(
#     Tool(
#         name="calculator",
#         description="Perform mathematical calculations.",
#         execute=calculate,
#     )
# )

registry.register(
    Capability(
        name="calculator",
        description=(
            "Perform exact mathematical calculations."
                "Always use this capability for arithmetic. "
    "Do not calculate numerical expressions yourself."
        ),
        execute=calculate,
        input_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string"
                }
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
    )
)

agent = Agent(capabilities =registry)


state = AgentState(
    goal=   "Search for NVIDIA AI GPU market share in 2024. "
    "Then calculate 87 - 75."
    )


result = agent.run(state)


print(result.model_dump_json(indent=2))