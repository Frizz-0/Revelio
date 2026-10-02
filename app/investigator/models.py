from pydantic import BaseModel, Field


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
    truncated: bool = False

class Finding(BaseModel):
    sub_question: str
    conclusion: str
    status: str
    supporting_evidence: list[int]
    contradicting_evidence: list[int]
    caveats: list[str]
