from app.services.llm import LLMService
from app.investigator.models import InvestigationPlan
import json


class InvestigationPlanner:

    def __init__(self):
        self.llm = LLMService()

    def create_plan(self, question: str) -> InvestigationPlan:

        messages = [
            {
                "role": "system",
                "content": """
You are the planning component of an AI investigation system.

Your job is to transform an investigation question into a
structured research plan.

DO NOT answer the investigation.

DO NOT invent factual claims.

DO NOT invent arbitrary numerical thresholds.

Separate genuine ambiguities from assumptions that may need
to be made during the investigation.

Return ONLY valid JSON matching this structure:

{
    "objective": "string",
    "sub_questions": ["string"],
    "evidence_required": ["string"],
    "assumptions": ["string"],
    "ambiguities": ["string"],
    "research_strategy": ["string"]
}
"""
            },
            {
                "role": "user",
                "content": question
            }
        ]

        raw_response = self.llm.generate(messages)

        print("\n=== RAW GROQ RESPONSE ===")
        print(repr(raw_response))
        print("=========================\n")

        data = json.loads(raw_response)

        return InvestigationPlan(**data)