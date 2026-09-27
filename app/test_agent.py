from app.agent.agent import Agent
from app.agent.state import AgentState
from app.agent.tools import Capability, CapabilityRegistry

from app.services.search_service import SearXNGProvider
from app.tools.calculator import calculate
from app.tools.analyzer import Analyzer
from app.tools.verifier import Verifier


verifier = Verifier()

analyzer = Analyzer()

registry = CapabilityRegistry()

search_provider = SearXNGProvider()

def search_tool(query: str):
    return search_provider.search(query)

registry.register(
    Capability(
        name="analyze",
        description=(
            "Analyze information retrieved by other capabilities. "
            "Extract relevant claims, uncertainties, and contradictions."
        ),
        execute=analyzer.analyze,
        input_schema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string"
                },
                "data": {
                    "type": "array"
                }
            },
            "required": ["question", "data"],
            "additionalProperties": False,
        },
    )
)

registry.register(
    Capability(
        name="verify",
        description=(
            "Verify factual claims against supplied evidence. "
            "Classify claims as supported, contradicted, or unresolved."
        ),
        execute=verifier.verify,
        input_schema={
            "type": "object",
            "properties": {
                "claims": {
                    "type": "array"
                },
                "evidence": {
                    "type": "array"
                }
            },
            "required": ["claims", "evidence"],
            "additionalProperties": False,
        },
    )
)


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
    goal= '''Search for NVIDIA AI GPU market share in 2024,
analyze the search results'''
    )


result = agent.run(state)

claims = [
    "NVIDIA held 87% of the AI accelerator market in 2024."
]

evidence = [
    {
        "title": "Example source",
        "snippet": "NVIDIA peaked at 87% in 2024."
    }
]

print(verifier.verify(claims, evidence))

print(result.model_dump_json(indent=2))