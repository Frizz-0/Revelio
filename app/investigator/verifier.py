import json

from app.services.llm import LLMService
from app.investigator.models import Evidence, Finding

response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "evidence_verification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "conclusion": {
                    "type": "string"
                },
                "status": {
                    "type": "string",
                    "enum": [
                        "supported",
                        "contradicted",
                        "insufficient"
                    ]
                },
                "supporting_evidence": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "contradicting_evidence": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "caveats": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "conclusion",
                "status",
                "supporting_evidence",
                "contradicting_evidence",
                "caveats"
            ],
            "additionalProperties": False
        }
    }
}

class EvidenceVerifier:

    def __init__(self):
        self.llm = LLMService()

    def verify(
        self,
        sub_question: str,
        evidence: list[Evidence]
    ) -> Finding:

        evidence_text = "\n\n".join(
            f"""
Evidence {i + 1}
Source: {item.title}
Type: {item.evidence_type}
Claim: {item.claim}
Supporting text: {item.supporting_text}
Relevance: {item.relevance}
"""
            for i, item in enumerate(evidence)
        )

        messages = [
            {
                "role": "system",
                "content": """
You are the evidence verification component of an AI investigation system.

Your task is to determine what the collected evidence supports regarding
the research question.

Rules:

1. Use ONLY the provided evidence.
2. Do not use outside knowledge.
3. Do not invent facts, numbers, dates, or sources.
4. Distinguish observed/reported values from projections.
5. Do not treat a source interpretation as independently verified fact.
6. Identify supporting and contradicting evidence separately.
7. If the evidence is insufficient to answer the question, use
   "insufficient".
8. If sources disagree, do not resolve the disagreement using
   outside knowledge. Report the contradiction.

9. If two evidence items report materially different values for
   the same metric, entity, and time period, they are contradictory
   even if both are relevant to the research question.

10. Do not average conflicting values.

11. Do not select one conflicting value as correct unless the
    provided evidence gives an explicit reason for preferring it.

12. An evidence item must not appear in both supporting_evidence
    and contradicting_evidence.

13. If materially conflicting evidence exists, the conclusion must
    explicitly acknowledge the disagreement.

14. "Supporting evidence" means evidence that supports the specific
    conclusion you write, not merely evidence that is relevant to
    the research question.

Return only the structured response.
"""
            },
            {
                "role": "user",
                "content": (
                    f"Research question:\n{sub_question}\n\n"
                    f"Collected evidence:\n{evidence_text}"
                )
            }
        ]

        raw_response = self.llm.generate(
            messages,
            response_format=response_format
        )

        data = json.loads(raw_response)

        return Finding(
            sub_question=sub_question,
            conclusion=data["conclusion"],
            status=data["status"],
            supporting_evidence=data["supporting_evidence"],
            contradicting_evidence=data["contradicting_evidence"],
            caveats=data["caveats"],
        )