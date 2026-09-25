from pydantic import BaseModel, Field


class InvestigationPlan(BaseModel):
    objective: str

    sub_questions: list[str]

    evidence_required: list[str]

    assumptions: list[str]

    ambiguities: list[str]

    research_strategy: list[str]

class Evidence(BaseModel):
    source: str
    title: str
    url: str
    claim: str
    supporting_text: str
    relevance: float = Field(ge=0, le=1)
    evidence_type: str

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class Document(BaseModel):
    title: str
    url: str
    content: str

class Finding(BaseModel):
    sub_question: str
    conclusion: str
    status: str
    supporting_evidence: list[int]
    contradicting_evidence: list[int]
    caveats: list[str]

class Claim(BaseModel):
    entity: str
    metric: str
    value: float | None
    unit: str | None
    time_period: str | None
    claim_type: str