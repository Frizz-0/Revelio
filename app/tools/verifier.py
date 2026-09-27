import json

from app.services.model_router import ModelRouter


class Verifier:
    def __init__(self):
        self.model_router = ModelRouter()

    def verify(self, claims, evidence):

        messages = [
            {
                "role": "system",
                "content": (
                    "You are Revelio's verification capability.\n"
                    "Evaluate claims only against the supplied evidence.\n"
                    "Do not use outside knowledge.\n"
                    "Do not invent evidence.\n\n"
                    "For each claim, classify it as:\n"
                    "- supported\n"
                    "- contradicted\n"
                    "- unresolved\n\n"
                    "Return JSON only using this structure:\n"
                    "{"
                    "\"results\": ["
                    "{"
                    "\"claim\": \"...\","
                    "\"status\": \"supported|contradicted|unresolved\","
                    "\"evidence\": \"...\","
                    "\"reason\": \"...\""
                    "}"
                    "]"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "claims": claims,
                        "evidence": evidence,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        response = self.model_router.generate(
            messages,
            response_format={"type": "json_object"},
            capability="reasoning",
        )

        return json.loads(response)