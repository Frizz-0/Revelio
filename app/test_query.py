from app.investigator.query_generator import QueryGenerator


generator = QueryGenerator()

queries = generator.generate_queries(
    "What regulatory and geopolitical developments could affect NVIDIA's AI GPU dominance?"
)

print("\n=== GENERATED QUERIES ===")

for i, query in enumerate(queries, 1):
    print(f"{i}. {query}")