import json

from app.services.llm import LLMService


class QueryGenerator:

    def __init__(self):
        self.llm = LLMService()

    def generate_queries(
        self,
        sub_question: str,
        max_queries: int = 4,
        time_context: str = "current"
    ) -> list[str]:

        messages = [
            {
                "role": "system",
                "content": """
        You are the search-query generation component of an AI
        investigation system.

        Your job is to transform a research sub-question into
        multiple targeted web search queries.

        DO NOT answer the question.

        DO NOT make factual claims.

        Generate queries that investigate the subject from
        different evidence angles.

        Use these angles where relevant:

        1. Primary sources
        - company filings
        - official company statements
        - government documents
        - regulatory documents

        2. Quantitative evidence
        - market share
        - revenue
        - sales
        - financial data
        - market statistics

        3. Competitors and alternatives
        - competing companies
        - competing technologies
        - substitute products

        4. Risks and constraints
        - regulation
        - export controls
        - supply chain
        - geopolitical factors
        - technical constraints

        5. Independent analysis
        - reputable financial publications
        - industry research
        - academic or technical sources

        IMPORTANT:

        Do not introduce dates, investigations, sanctions,
        regulations, organizations, events, or other factual
        claims that are not supported by the sub-question or
        explicitly provided context.

        When investigating whether an event or action exists,
        phrase the query neutrally rather than presupposing it.
        
        Do not assume a historical time period unless the
        sub-question explicitly specifies one.

        If the sub-question concerns the current situation,
        prefer queries containing terms such as:
        "current", "latest", or the current year.

        Do not insert specific events, organizations, investigations,
        regulations, or factual claims that are not implied by the
        sub-question.

        Avoid:
        - vague queries
        - duplicate queries
        - conversational questions
        - queries that contain conclusions
        - unnecessarily long queries

        Each query should be concise and search-engine friendly.

        Return ONLY valid JSON:

        {
            "queries": [
                "query 1",
                "query 2",
                "query 3",
                "query 4"
            ]
        }
        """
            },
            {
                "role": "user",
                "content": (
                    f"Research sub-question:\n{sub_question}\n\n"
                    f"Time context: {time_context}\n\n"
                    "Generate targeted search queries for investigating "
                    "this sub-question. Do not introduce dates that are "
                    "not present in the time context."
                )
            }
        ]

        raw_response = self.llm.generate(messages)

        data = json.loads(raw_response)

        queries = data.get("queries", [])

        # Remove duplicates while preserving order
        unique_queries = []

        for query in queries:
            query = query.strip()

            if query and query not in unique_queries:
                unique_queries.append(query)

        return unique_queries[:max_queries]