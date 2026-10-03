import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Callable

from groq import Groq

from app.core.config import settings


class LLMService:

    def __init__(self, on_usage: Callable[[dict], None] | None = None):
        self.client = Groq(
            api_key=settings.groq_api_key
        )

        self.model = "openai/gpt-oss-20b"

        self.cache_enabled = settings.llm_cache_enabled
        self.on_usage = on_usage

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

            self._report_usage({
                "model": self.model,
                "cache_hit": True,
                "latency_seconds": 0,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
            })

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

        started = perf_counter()
        try:
            response = self.client.chat.completions.create(**request)
        except Exception as exc:
            error_body = getattr(exc, "body", None)
            details = error_body.get("error", error_body) if isinstance(error_body, dict) else {}
            error_code = details.get("code") if isinstance(details, dict) else None
            if response_format and response_format.get("type") == "json_schema" and error_code == "json_validate_failed":
                # Some provider/model responses fail strict schema validation
                # despite returning usable JSON. Retry in JSON mode; callers
                # still parse and validate the resulting object themselves.
                print("[LLM] Schema validation failed; retrying in JSON object mode")
                request["response_format"] = {"type": "json_object"}
                try:
                    response = self.client.chat.completions.create(**request)
                except Exception:
                    self._report_usage({
                        "model": self.model,
                        "cache_hit": False,
                        "failed": True,
                        "latency_seconds": round(perf_counter() - started, 3),
                        "prompt_tokens": None,
                        "completion_tokens": None,
                        "total_tokens": None,
                    })
                    raise
            else:
                self._report_usage({
                    "model": self.model,
                    "cache_hit": False,
                    "failed": True,
                    "latency_seconds": round(perf_counter() - started, 3),
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                })
                raise

        content = response.choices[0].message.content
        usage = response.usage
        self._report_usage({
            "model": self.model,
            "cache_hit": False,
            "failed": False,
            "latency_seconds": round(perf_counter() - started, 3),
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        })

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

    def _report_usage(self, details: dict) -> None:
        if self.on_usage is not None:
            try:
                self.on_usage(details)
            except Exception as exc:
                print(f"[LLM] Could not report usage telemetry: {exc}")
