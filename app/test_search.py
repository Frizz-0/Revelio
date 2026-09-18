from app.services.search_service import SearXNGProvider


search = SearXNGProvider()

results = search.search(
    "NVIDIA AI GPU market share",
    max_results=5
)

print("\nRESULTS:")
print("=" * 60)

for result in results:
    print(result.title)
    print(result.url)
    print(result.snippet)
    print("-" * 60)