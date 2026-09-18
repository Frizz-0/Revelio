from app.services.search_service import SearXNGProvider
from app.services.document_service import DocumentFetcher
from app.services.document_parser import DocumentParser
from app.investigator.evidence_extractor import EvidenceExtractor


search = SearXNGProvider()
fetcher = DocumentFetcher()
parser = DocumentParser()
extractor = EvidenceExtractor()


sub_question = (
    "What is NVIDIA's current market share in the AI GPU "
    "segment, and how has it evolved over the last 5 years?"
)


# -------------------------
# Search
# -------------------------

results = search.search(
    "NVIDIA AI GPU market share",
    max_results=1
)

if not results:
    print("No search results.")
    raise SystemExit


result = results[0]

print("\nSOURCE")
print(result.title)
print(result.url)


# -------------------------
# Fetch
# -------------------------

document = fetcher.fetch(result)

if document is None:
    print("Could not fetch document.")
    raise SystemExit


# -------------------------
# Parse
# -------------------------

document.content = parser.parse(document)

print(
    f"\nParsed document: "
    f"{len(document.content):,} characters"
)


# -------------------------
# Extract evidence
# -------------------------

evidence = extractor.extract(
    sub_question,
    document
)


# -------------------------
# Display
# -------------------------

print("\n=== EXTRACTED EVIDENCE ===")

for i, item in enumerate(evidence, 1):

    print(f"\nEvidence {i}")
    print("-" * 60)

    print("Claim:")
    print(item.claim)

    print("\nSupporting text:")
    print(item.supporting_text)

    print("\nRelevance:")
    print(item.relevance)

    print("\nSource:")
    print(item.url)