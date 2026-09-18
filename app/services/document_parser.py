from bs4 import BeautifulSoup


class DocumentParser:

    def parse(self, document):

        soup = BeautifulSoup(
            document.content,
            "html.parser"
        )

        # Remove elements that are not useful
        # for research content.
        for element in soup([
            "script",
            "style",
            "noscript",
            "nav",
            "footer",
            "header",
            "aside",
            "form"
        ]):
            element.decompose()

        text = soup.get_text(
            separator="\n",
            strip=True
        )

        return text