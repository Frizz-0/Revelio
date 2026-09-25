from typing import Any, Callable

from jsonschema import ValidationError, validate


class Capability:

    def __init__(
        self,
        name: str,
        description: str,
        execute: Callable,
        input_schema: dict,
    ):
        self.name = name
        self.description = description
        self.execute_fn = execute
        self.input_schema = input_schema

    def validate_arguments(
        self,
        arguments: dict[str, Any],
    ):
        try:
            validate(
                instance=arguments,
                schema=self.input_schema,
            )

        except ValidationError as e:
            raise ValueError(
                f"Invalid arguments for capability "
                f"'{self.name}': {e.message}"
            )

    def execute(
        self,
        arguments: dict[str, Any],
    ):
        self.validate_arguments(arguments)

        return self.execute_fn(**arguments)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class CapabilityRegistry:

    def __init__(self):
        self.capabilities: dict[str, Capability] = {}

    def register(
        self,
        capability: Capability,
    ):
        if capability.name in self.capabilities:
            raise ValueError(
                f"Capability already registered: "
                f"{capability.name}"
            )

        self.capabilities[capability.name] = capability

    def get(
        self,
        name: str,
    ) -> Capability:

        if name not in self.capabilities:
            raise ValueError(
                f"Unknown capability: {name}"
            )

        return self.capabilities[name]

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ):
        capability = self.get(name)

        return capability.execute(arguments)

    def describe(self) -> list[dict]:
        return [
            capability.describe()
            for capability in self.capabilities.values()
        ]