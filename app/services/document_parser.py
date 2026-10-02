"""Dependency-light HTML and plain-text parser for fetched sources."""

import re
import io
import zipfile
from html import unescape
from html.parser import HTMLParser
from pathlib import PurePath
from xml.etree import ElementTree

from app.investigator.models import Document


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
        return self._parse_content(document.content or "")

    def _parse_content(self, content: str) -> str:
        if not re.search(r"<(html|body|main|article|p|div|h[1-6]|section|li)\b", content, re.I):
            return unescape(content).strip()

        parser = _ReadableText()
        parser.feed(content)
        text = "".join(parser.parts)
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    def parse_upload(self, filename: str, content: bytes) -> Document:
        """Read a supported user-uploaded document without saving it to disk."""
        name = PurePath(filename.replace("\\", "/")).name
        suffix = PurePath(name).suffix.lower()
        if not name or not content:
            raise ValueError("The uploaded document is empty.")

        if suffix == ".pdf":
            try:
                import fitz
            except ImportError as exc:
                raise ValueError("PDF uploads require PyMuPDF.") from exc
            try:
                with fitz.open(stream=content, filetype="pdf") as pdf:
                    text = "\n".join(page.get_text() for page in pdf)
            except Exception as exc:
                raise ValueError("Could not read this PDF file.") from exc
        elif suffix == ".docx":
            text = self._read_docx(content)
        elif suffix in {".txt", ".md", ".html", ".htm"}:
            decoded = content.decode("utf-8-sig", errors="replace")
            text = self._parse_content(decoded)
        else:
            raise ValueError("Supported uploads are PDF, DOCX, TXT, MD, and HTML.")

        text = text.strip()
        if not text:
            raise ValueError(f"No readable text was found in {name}.")
        return Document(
            title=name,
            url=f"upload://{name}",
            content=text[:100_000],
            truncated=len(text) > 100_000,
        )

    @staticmethod
    def _read_docx(content: bytes) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                xml = ElementTree.fromstring(archive.read("word/document.xml"))
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
            raise ValueError("Could not read this DOCX file.") from exc
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for paragraph in xml.findall(".//w:p", namespace):
            value = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
            if value.strip():
                paragraphs.append(value)
        return "\n".join(paragraphs)
