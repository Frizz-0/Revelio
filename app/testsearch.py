# from app.services.search_service import SearXNGProvider
# from app.services.document_service import DocumentFetcher

# search = SearXNGProvider()
# document = DocumentFetcher()

# results = search.search(
#     "NVIDIA AI GPU market share",
#     max_results=5
# )

# for result in results:
#     print()
#     print("TITLE:", result.get("title"))
#     print("URL:", result.get("url"))
#     print("CONTENT:", result.get("content", "")[:500])
from app.services.search_service import SearXNGProvider


search = SearXNGProvider()

results = search.search(
    "NVIDIA AI GPU market share",
    max_results=5
)

print(f"\nFound {len(results)} results\n")

for result in results:
    print(result.title)
    print(result.url)
    print(result.snippet)
    print("-" * 60)