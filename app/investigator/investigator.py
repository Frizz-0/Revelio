from app.investigator.planner import InvestigationPlanner
from app.investigator.query_generator import QueryGenerator
from app.services.search_service import SearXNGProvider
from app.services.document_service import DocumentFetcher


class Investigator:

    def __init__(self):
        self.planner = InvestigationPlanner()
        self.query_generator = QueryGenerator()
        self.search = SearXNGProvider()
        self.fetcher = DocumentFetcher()

    def investigate(self, question: str):

        print("Creating investigation plan...", flush=True)
        plan = self.planner.create_plan(question)

        print("\n=== INVESTIGATION PLAN ===")
        print(plan)

        for sub_question in plan.sub_questions:

            print("\n" + "=" * 60)
            print("SUB-QUESTION:")
            print(sub_question)

            # -----------------------------------------
            # Generate targeted search queries
            # -----------------------------------------

            print("\nGenerating search queries...", flush=True)

            queries = self.query_generator.generate_queries(
                sub_question,
                max_queries=2,
                time_context="current"
            )

            print("\n=== SEARCH QUERIES ===")

            for i, query in enumerate(queries, 1):
                print(f"{i}. {query}")

            # -----------------------------------------
            # Search using generated queries
            # -----------------------------------------

            all_results = []

            for query in queries:

                print(
                    f"\nSearching: {query}",
                    flush=True
                )

                results = self.search.search(
                    query,
                    max_results=3
                )

                print(
                    f"[Investigator] Query={query!r}, "
                    f"returned={len(results)}"
                )
                
                all_results.extend(results)

            # -----------------------------------------
            # Deduplicate search results
            # -----------------------------------------

            unique_results = []
            seen_urls = set()

            for result in all_results:

                if result.url in seen_urls:
                    continue

                seen_urls.add(result.url)
                unique_results.append(result)

            print(
                f"\nFound {len(unique_results)} unique sources"
            )

            # -----------------------------------------
            # Fetch documents
            # -----------------------------------------

            # for result in unique_results:

            #     print("\nSOURCE:")
            #     print(result.title)
            #     print(result.url)

            #     try:

            #         document = self.fetcher.fetch(result)

            #         if document is None:
            #             print("Skipping source.")
            #             continue

            #         print(
            #             f"Downloaded "
            #             f"{len(document.content)} characters"
            #         )

            #     except Exception as e:

            #         print(f"Failed to fetch: {e}")

        return plan