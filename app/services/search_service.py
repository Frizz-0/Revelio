import time
import requests

from app.core.config import settings
from app.investigator.models import SearchResult


class SearchProvider:

    def search(self, query: str, max_results: int = 5):
        raise NotImplementedError


class SearXNGProvider(SearchProvider):

    def __init__(self):
        self.base_url = settings.searxng_url.rstrip("/")

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            )
        })

        # Prevent rapid-fire requests to SearXNG
        self.request_delay = 1.0
        self.last_request_time = 0.0

    def _wait_before_request(self):
        elapsed = time.time() - self.last_request_time

        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)

        self.last_request_time = time.time()

    def search(self, query: str, max_results: int = 5):

        self._wait_before_request()

        try:
            response = self.session.get(
                f"{self.base_url}/search",
                params={
                    "q": query,
                    "format": "json",
                },
                timeout=(5, 15),
            )

            response.raise_for_status()

            data = response.json()

        except requests.exceptions.Timeout:
            print(f"[Search] Timeout: {query}")
            return []

        except requests.exceptions.HTTPError as e:
            print(f"[Search] HTTP error: {e}")
            return []

        except requests.exceptions.RequestException as e:
            print(f"[Search] Request failed: {e}")
            return []

        except ValueError:
            print("[Search] Invalid JSON response")
            return []

        results = []
        seen_urls = set()

        for result in data.get("results", []):

            title = result.get("title", "").strip()
            url = result.get("url", "").strip()
            snippet = result.get("content", "").strip()

            # Ignore malformed results
            if not url:
                continue

            # Remove duplicate URLs
            if url in seen_urls:
                continue

            seen_urls.add(url)

            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                )
            )

            if len(results) >= max_results:
                break

        return results