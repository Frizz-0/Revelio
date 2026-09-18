from app.investigator.planner import InvestigationPlanner
from app.services.search_service import SearXNGProvider
from app.services.document_service import DocumentFetcher


class Investigator:

    def __init__(self):
        self.planner = InvestigationPlanner()
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

            results = self.search.search(
                sub_question,
                max_results=3
            )

            print(f"\nFound {len(results)} sources")

            for result in results:

                print("\nSOURCE:")
                print(result.title)
                print(result.url)

                try:
                    document = self.fetcher.fetch(result)

                    if document is None:
                        print("Skipping source.")
                        continue

                    print(
                        f"Downloaded "
                        f"{len(document.content)} characters"
                    )

                except Exception as e:
                    print(f"Failed to fetch: {e}")

        return plan