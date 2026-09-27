"""Capability definitions, registry, and the default V1 investigation tools."""

from typing import Any, Callable

from jsonschema import ValidationError, validate

from app.services.search_service import SearXNGProvider
from app.tools.analyzer import Analyzer
from app.tools.calculator import calculate
from app.tools.verifier import Verifier


class Capability:
    def __init__(
        self,
        name: str,
        description: str,
        execute: Callable[..., Any],
        input_schema: dict[str, Any],
    ):
        self.name = name
        self.description = description
        self.execute_fn = execute
        self.input_schema = input_schema

    def execute(self, arguments: dict[str, Any]) -> Any:
        try:
            validate(instance=arguments, schema=self.input_schema)
        except ValidationError as exc:
            raise ValueError(
                f"Invalid arguments for capability '{self.name}': {exc.message}"
            ) from exc
        return self.execute_fn(**arguments)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class CapabilityRegistry:
    def __init__(self):
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        if capability.name in self._capabilities:
            raise ValueError(f"Capability already registered: {capability.name}")
        self._capabilities[capability.name] = capability

    def describe(self) -> list[dict[str, Any]]:
        return [item.describe() for item in self._capabilities.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        try:
            capability = self._capabilities[name]
        except KeyError as exc:
            raise ValueError(f"Unknown capability: {name}") from exc
        return capability.execute(arguments)


def build_capability_registry() -> CapabilityRegistry:
    """Wire the three capabilities used by the V1 investigation agent."""
    registry = CapabilityRegistry()
    search_provider = SearXNGProvider()
    analyzer = Analyzer()
    verifier = Verifier()

    def search(query: str):
        return [result.model_dump() for result in search_provider.search(query)]

    def research(question: str, data: list[dict]):
        analysis = analyzer.analyze(question, data)
        verification = verifier.verify(analysis.get("claims", []), data)
        return {"analysis": analysis, "verification": verification}

    registry.register(Capability(
        name="search",
        description="Search the web and return source titles, URLs, and snippets.",
        execute=search,
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    ))
    registry.register(Capability(
        name="research",
        description=(
            "Analyze supplied search evidence for claims, uncertainties, and "
            "contradictions, then verify the claims against that evidence."
        ),
        execute=research,
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "data": {"type": "array", "items": {}},
            },
            "required": ["question", "data"],
            "additionalProperties": False,
        },
    ))
    registry.register(Capability(
        name="calculator",
        description="Evaluate exact arithmetic expressions deterministically.",
        execute=calculate,
        input_schema={
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
            "additionalProperties": False,
        },
    ))
    return registry
