from app.services.llm import LLMService


class ModelRouter:

    def __init__(self):
        self.llm = LLMService()

    def generate(
        self,
        messages,
        response_format=None,
        capability: str = "general",
    ):

        # For now everything uses the same model.
        # The routing layer exists so model selection
        # can evolve independently of the Agent.

        return self.llm.generate(
            messages,
            response_format=response_format,
        )