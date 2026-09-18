from app.services.document_service import DocumentFetcher
from app.services.search_service import SearXNGProvider
from app.services.document_parser import DocumentParser


search = SearXNGProvider()
fetcher = DocumentFetcher()
parser = DocumentParser()

results = search.search(
    "NVIDIA AI GPU market share",
    max_results=1
)

if not results:
    print("No search results.")
    raise SystemExit

result = results[0]

print("\nSEARCH RESULT")
print(result.title)
print(result.url)

document = fetcher.fetch(result)

if document is None:
    print("Could not fetch document.")
    raise SystemExit

print("\nRAW HTML")
print(f"{len(document.content):,} characters")

text = parser.parse(document)

print("\nPARSED TEXT")
print(f"{len(text):,} characters")

print("\nFIRST 3000 CHARACTERS")
print("=" * 60)
print(text[:3000])