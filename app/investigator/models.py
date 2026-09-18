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

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class Document(BaseModel):
    title: str
    url: str
    content: str