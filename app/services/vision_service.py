"""Vision-language analysis for user-supplied image files."""

import base64
import json
from time import perf_counter
from typing import Callable

from groq import Groq

from app.core.config import settings


class VisionService:
    """Analyze an image once and return observations with clear uncertainty."""

    model = "qwen/qwen3.8-27b"

    def __init__(self, on_usage: Callable[[dict], None] | None = None):
        self.client = Groq(api_key=settings.groq_api_key)
        self.on_usage = on_usage

    def analyze(self, filename: str, media_type: str, content: bytes, task: str) -> dict:
        encoded = base64.b64encode(content).decode("ascii")
        prompt = (
            "Analyze the attached image for the user's task. Return one JSON object with exactly these keys: "
            "summary (string), visible_text (array of strings), visual_findings (array of strings), "
            "uncertainties (array of strings), suggested_route (one of visual_qa, ocr, chart_reading, "
            "diagram, object_detection, external_research), and route_reason (string). "
            "Report only what is visible. Preserve uncertain or unreadable text as uncertain; do not guess. "
            "For charts, distinguish visible labels/values from interpretation. suggested_route is guidance, "
            "not permission to call tools. The application decides whether outside search is needed. "
            "Be concise: summary at most 60 words, and at most 4 items in each array; "
            "keep each array item under 20 words. "
            f"Image filename: {filename}\nUser task: {task}"
        )
        started = perf_counter()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:{media_type};base64,{encoded}"
                        }},
                    ],
                }],
                response_format={"type": "json_object"},
                temperature=0,
                max_completion_tokens=450,
            )
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
        raw = response.choices[0].message.content
        if not raw:
            raise RuntimeError("Vision model returned an empty response.")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("Vision model response must be a JSON object.")
        for key in ("summary", "visible_text", "visual_findings", "uncertainties", "suggested_route", "route_reason"):
            if key not in result:
                result[key] = [] if key in {"visible_text", "visual_findings", "uncertainties"} else ""
        for key in ("visible_text", "visual_findings", "uncertainties"):
            if not isinstance(result[key], list):
                result[key] = [str(result[key])] if result[key] else []
        allowed_routes = {"visual_qa", "ocr", "chart_reading", "diagram", "object_detection", "external_research"}
        if result["suggested_route"] not in allowed_routes:
            result["suggested_route"] = "visual_qa"
        return result

    def _report_usage(self, details: dict) -> None:
        if self.on_usage is not None:
            try:
                self.on_usage(details)
            except Exception as exc:
                print(f"[Vision] Could not report usage telemetry: {exc}")
