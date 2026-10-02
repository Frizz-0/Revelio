"""Capability definitions, registry, and default V2 investigation tools."""

from typing import Any, Callable

from jsonschema import ValidationError, validate

from app.investigator.evidence_extractor import EvidenceExtractor
from app.investigator.models import Document, Evidence, Finding, SearchResult
from app.investigator.verifier import EvidenceVerifier
from app.services.document_parser import DocumentParser
from app.services.document_service import DocumentFetcher
from app.services.search_service import SearXNGProvider
from app.tools.calculator import calculate


class Capability:
    def __init__(
        self,
        name: str,
        description: str,
        execute: Callable[..., Any],
        input_schema: dict[str, Any],
    ):
        self.name = name
        self.description = description
        self.execute_fn = execute
        self.input_schema = input_schema

    def execute(self, arguments: dict[str, Any]) -> Any:
        try:
            validate(instance=arguments, schema=self.input_schema)
        except ValidationError as exc:
            raise ValueError(
                f"Invalid arguments for capability '{self.name}': {exc.message}"
            ) from exc
        return self.execute_fn(**arguments)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class CapabilityRegistry:
    def __init__(self):
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        if capability.name in self._capabilities:
            raise ValueError(f"Capability already registered: {capability.name}")
        self._capabilities[capability.name] = capability

    def describe(self) -> list[dict[str, Any]]:
        return [item.describe() for item in self._capabilities.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        try:
            capability = self._capabilities[name]
        except KeyError as exc:
            raise ValueError(f"Unknown capability: {name}") from exc
        return capability.execute(arguments)


def build_capability_registry(
    on_event: Callable[[dict[str, Any]], None] | None = None,
    uploaded_documents: dict[str, Document] | None = None,
) -> CapabilityRegistry:
    """Wire the three capabilities used by the V2 investigation agent."""
    registry = CapabilityRegistry()
    search_provider = SearXNGProvider()
    fetcher = DocumentFetcher()
    parser = DocumentParser()
    extractor = EvidenceExtractor()
    verifier = EvidenceVerifier()
    uploaded_documents = uploaded_documents or {}

    def emit(event: str, **details: Any) -> None:
        if on_event is not None:
            on_event({"event": event, **details})

    def search(query: str):
        results = [result.model_dump() for result in search_provider.search(query)]
        emit("search_finished", query=query, result_count=len(results))
        return results

    def research(question: str, data: list[dict]):
        """Fetch sources, extract traceable evidence, then verify the finding."""
        extracted: list[Evidence] = []
        sources: list[dict[str, str]] = []
        truncated_sources: list[str] = []

        # Uploaded documents are processed as supplied (up to the API limit);
        # web research stays limited to two readable pages to control cost.
        has_uploads = any(
            isinstance(item, dict) and item.get("url") in uploaded_documents
            for item in data
        )
        source_limit = 3 if has_uploads else 2
        for item in data[:source_limit]:
            result = SearchResult.model_validate(item)
            print(f"[Research] Fetching source: {result.url}")
            emit("research_source_started", title=result.title, url=result.url)
            document = uploaded_documents.get(result.url)
            if document is None:
                document = fetcher.fetch(result)
            if document is None:
                emit("research_source_finished", title=result.title, url=result.url, success=False, error="Could not fetch source")
                continue

            text = document.content if result.url in uploaded_documents else parser.parse(document)
            if not text.strip():
                print(f"[Research] No readable text: {result.url}")
                emit("research_source_finished", title=result.title, url=result.url, success=False, error="No readable text")
                continue
            document = Document(
                title=document.title,
                url=document.url,
                content=text[:24000],
                truncated=document.truncated or len(text) > 24000,
            )
            if document.truncated:
                truncated_sources.append(document.title)
            sources.append({"title": document.title, "url": document.url})
            emit("research_source_finished", title=document.title, url=document.url, success=True)
            print(f"[Research] Extracting evidence from {document.title}")
            emit("evidence_extraction_started", title=document.title, url=document.url)
            try:
                source_evidence = extractor.extract(question, document)
            except Exception as exc:
                # A malformed model response for one page should not discard
                # evidence already collected or prevent trying another source.
                print(f"[Research] Evidence extraction failed for {document.url}: {exc}")
                emit("evidence_extraction_finished", title=document.title, url=document.url, success=False, error=str(exc))
                continue
            emit("evidence_extraction_finished", title=document.title, url=document.url, success=True, count=len(source_evidence))
            for evidence in source_evidence:
                # The extractor is instructed to copy exact source passages;
                # enforce that claim in code before evidence reaches verification.
                if evidence.supporting_text and evidence.supporting_text in document.content:
                    extracted.append(evidence)
                else:
                    print(f"[Research] Discarded non-matching quote: {document.url}")
            if len(sources) >= source_limit:
                break

        if not sources:
            raise RuntimeError("Could not fetch readable source documents for verification.")

        if extracted:
            print(f"[Research] Verifying {len(extracted)} evidence item(s)")
            emit("verification_started", evidence_count=len(extracted), source_count=len(sources))
            try:
                finding = verifier.verify(question, extracted)
            except Exception as exc:
                print(f"[Research] Verification failed: {exc}")
                finding = Finding(
                    sub_question=question,
                    conclusion="The collected evidence could not be verified in this run.",
                    status="insufficient",
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    caveats=[f"Verification failed: {exc}"],
                )
        else:
            finding = Finding(
                sub_question=question,
                conclusion="The fetched pages did not yield exact, relevant evidence to answer this question.",
                status="insufficient",
                supporting_evidence=[],
                contradicting_evidence=[],
                caveats=["No source passage passed exact-quote validation."],
            )
        independent_source_count = len({item.url for item in extracted})
        if truncated_sources:
            finding.caveats.append(
                "Only the first 24,000 extracted characters were reviewed for: "
                + ", ".join(truncated_sources)
                + "."
            )
        if independent_source_count < 2:
            only_uploaded_evidence = bool(extracted) and all(
                item.url in uploaded_documents for item in extracted
            )
            if only_uploaded_evidence:
                finding.caveats.append(
                    "This finding is based only on the uploaded document(s) and "
                    "has not been checked against independent outside sources."
                )
            else:
                finding.status = "insufficient"
                finding.caveats.append(
                    "Evidence came from fewer than two independent source URLs; "
                    "it is not independently corroborated."
                )
        emit("verification_finished", status=finding.status, evidence_count=len(extracted), source_count=independent_source_count)
        return {
            "finding": finding.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in extracted],
            "sources": sources,
        }

    registry.register(Capability(
        name="search",
        description="Search the web and return source titles, URLs, and snippets.",
        execute=search,
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    ))
    registry.register(Capability(
        name="research",
        description=(
            "Read uploaded documents or search-result pages, extract exact quoted "
            "evidence with source URLs, then verify the finding against those passages."
        ),
        execute=research,
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "data": {"type": "array", "items": {}},
            },
            "required": ["question", "data"],
            "additionalProperties": False,
        },
    ))
    registry.register(Capability(
        name="calculator",
        description="Evaluate exact arithmetic expressions deterministically.",
        execute=calculate,
        input_schema={
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
            "additionalProperties": False,
        },
    ))
    return registry
