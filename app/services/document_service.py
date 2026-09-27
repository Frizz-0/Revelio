import requests

from app.investigator.models import Document


class DocumentFetcher:

    def __init__(self):
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

    def fetch(self, result):

        try:

            response = self.session.get(
                result.url,
                timeout=(5, 15)
            )

            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            if "application/pdf" in content_type or result.url.lower().endswith(".pdf"):
                try:
                    import fitz
                except ImportError as exc:
                    raise RuntimeError("PDF support requires PyMuPDF.") from exc

                with fitz.open(stream=response.content, filetype="pdf") as pdf:
                    content = "\n".join(page.get_text() for page in pdf)
            else:
                content = response.text

            return Document(
                title=result.title,
                url=result.url,
                content=content,
            )

        except requests.exceptions.Timeout:

            print(f"Timeout while fetching: {result.url}")
            return None

        except requests.exceptions.HTTPError as e:

            print(f"HTTP error while fetching {result.url}: {e}")
            return None

        except requests.exceptions.RequestException as e:

            print(f"Request failed for {result.url}: {e}")
            return None
