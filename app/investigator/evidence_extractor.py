import json

from app.services.llm import LLMService
from app.investigator.models import Evidence


response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "evidence_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "evidence": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim": {
                                "type": "string"
                            },
                            "supporting_text": {
                                "type": "string"
                            },
                            "relevance": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1
                            },
                            "evidence_type": {
                            "type": "string",
                            "enum": [
                                "explicit_claim",
                                "reported_statistic",
                                "projection",
                                "source_interpretation"
                            ]
                        }
                        },
                        "required": [
                            "claim",
                            "supporting_text",
                            "relevance",
                            "evidence_type"
                        ],
                        "additionalProperties": False
                    }
                }
                
            },
            "required": [
                "evidence"
            ],
            "additionalProperties": False
        }
    }
}


class EvidenceExtractor:

    def __init__(self):
        self.llm = LLMService()

    def extract(
        self,
        sub_question: str,
        document
    ) -> list[Evidence]:

        messages = [
            {
                "role": "system",
                "content": """
You are the evidence extraction component of an AI investigation system.

Your job is to identify passages from the source document that directly
support or contradict the research question.

STRICT RULES:

1. Use ONLY information explicitly present in the document.

2. Do NOT infer relationships between separate pieces of text.

3. Do NOT infer table column relationships unless the relationship is
explicitly clear from the extracted text.

4. Do NOT calculate, combine, or derive numbers.

5. Do NOT convert projections into current facts.

6. Do NOT convert a source's interpretation into an independently
verified fact.

7. supporting_text must be an exact contiguous passage copied from
the document.

8. The claim must be a faithful paraphrase of that passage.

9. If you cannot find a passage that directly supports a claim,
do not create the evidence.

10. Relevance should reflect usefulness to the research question.
Do not automatically assign 1.0.

11. If the source contains relevant evidence but its wording is
uncertain, preserve that uncertainty.

12. If no directly relevant evidence exists, return an empty list.

13. Do not infer relationships between table values and column headers
when those relationships are not explicitly preserved in the provided text.

The source is evidence to be evaluated later, not established truth.

Return ONLY the structured JSON response.
"""
            },
            {
                "role": "user",
                "content": (
                    f"Research question:\n{sub_question}\n\n"
                    f"Source title:\n{document.title}\n\n"
                    f"Source URL:\n{document.url}\n\n"
                    f"Document:\n{document.content}"
                )
            }
        ]

        raw_response = self.llm.generate(
            messages,
            response_format=response_format
        )

        # print("\n=== RAW EVIDENCE RESPONSE ===")
        # print(repr(raw_response))
        # print("=============================\n")

        data = json.loads(raw_response)

        extracted = []

        for item in data.get("evidence", []):

            extracted.append(
                Evidence(
                    source=document.url,
                    title=document.title,
                    url=document.url,
                    claim=item["claim"],
                    supporting_text=item["supporting_text"],
                    relevance=item["relevance"],
                    evidence_type=item["evidence_type"],
                )
            )

        return extracted