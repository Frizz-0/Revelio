import json

from app.services.model_router import ModelRouter


class Analyzer:
    def __init__(self):
        self.model_router = ModelRouter()

    def analyze(self, question: str, data: str):

        messages = [
            {
                "role": "system",
                "content": (
                    "You are Revelio's analysis capability.\n"
                    "Analyze the supplied information only.\n"
                    "Extract relevant factual claims.\n"
                    "Identify contradictions or uncertainty.\n"
                    "Do not invent facts.\n"
                    "Return valid JSON only.\n\n"
                    "Return this structure:\n"
                    "{"
                    "\"claims\": [],"
                    "\"uncertainties\": [],"
                    "\"contradictions\": []"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "data": data,
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