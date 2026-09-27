"""Dependency-light HTML and plain-text parser for fetched sources."""

import re
from html import unescape
from html.parser import HTMLParser


class _ReadableText(HTMLParser):
    _ignored = {"script", "style", "noscript", "nav", "footer", "header", "aside", "form"}
    _breaks = {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "section", "article"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignore_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._ignored:
            self.ignore_depth += 1
        elif self.ignore_depth == 0 and tag in self._breaks:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._ignored and self.ignore_depth:
            self.ignore_depth -= 1
        elif self.ignore_depth == 0 and tag in self._breaks:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.ignore_depth == 0:
            self.parts.append(data)


class DocumentParser:
    def parse(self, document) -> str:
        content = document.content or ""
        if not re.search(r"<(html|body|main|article|p|div|h[1-6]|section|li)\b", content, re.I):
            return unescape(content).strip()

        parser = _ReadableText()
        parser.feed(content)
        text = "".join(parser.parts)
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)
