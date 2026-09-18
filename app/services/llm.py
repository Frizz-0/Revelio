import hashlib
import json
from pathlib import Path

from groq import Groq

from app.core.config import settings


class LLMService:

    def __init__(self):
        self.client = Groq(
            api_key=settings.groq_api_key
        )

        self.model = "openai/gpt-oss-20b"

        self.cache_enabled = settings.llm_cache_enabled

        self.cache_dir = Path("app/cache/llm")
        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def _cache_key(self, messages, response_format=None):
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": response_format,
        }

        serialized = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    def generate(self, messages, response_format=None):

        # -------------------------
        # Check local cache
        # -------------------------

        cache_key = self._cache_key(
            messages,
            response_format=response_format
        )

        cache_file = self.cache_dir / f"{cache_key}.json"

        if self.cache_enabled and cache_file.exists():

            print("[LLM] Cache hit")

            with open(
                cache_file,
                "r",
                encoding="utf-8"
            ) as f:
                cached_response = json.load(f)

            return cached_response["content"]

        # -------------------------
        # Call Groq
        # -------------------------

        print("[LLM] Cache miss → calling Groq")

        request = {
            "model": self.model,
            "messages": messages,
        }

        if response_format is not None:
            request["response_format"] = response_format

        response = self.client.chat.completions.create(
            **request
        )

        content = response.choices[0].message.content

        # -------------------------
        # Save response locally
        # -------------------------

        if self.cache_enabled:

            with open(
                cache_file,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    {
                        "content": content
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            print("[LLM] Response cached")

        return content