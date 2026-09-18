from groq import Groq

from app.core.config import settings


class LLMService:

    def __init__(self):
        self.client = Groq(
            api_key=settings.groq_api_key
        )

    def generate(self, messages):
        response = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
        )

        return response.choices[0].message.content