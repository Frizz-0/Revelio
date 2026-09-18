from pydantic import BaseModel, Field
from typing import List


class Finding(BaseModel):
    claim: str
    evidence: str
    confidence: float = Field(ge=0, le=1)


class InvestigationResult(BaseModel):
    question: str
    interpretation: str
    sub_questions: List[str]
    findings: List[Finding]
    uncertainties: List[str]
    next_actions: List[str]