import requests

from app.investigator.models import SearchResult
from app.services.search.base import SearchProvider
from app.core.config import settings


class SearXNGProvider(SearchProvider):

    def __init__(self):
        self.base_url = settings.searxng_url

    def search(
        self,
        query: str,
        max_results: int = 5
    ):

        response = requests.get(
            f"{self.base_url}/search",
            params={
                "q": query,
                "format": "json"
            },
            timeout=(5, 15)
        )

        response.raise_for_status()

        data = response.json()

        return [
            SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                snippet=result.get("content", "")
            )
            for result in data.get("results", [])[:max_results]
        ]