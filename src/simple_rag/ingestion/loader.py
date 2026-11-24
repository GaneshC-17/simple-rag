"""Ingestion stage 1: load a PDF file and extract its text.

Scope of this stage (deliberately small):
    PDF file in  ->  structured text out

No chunking, no embeddings, no vector store yet.
Library: pdfplumber (MIT licence) - free and open source.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pdfplumber


@dataclass(frozen=True)
class Document:
    """Text extracted from one PDF.

    Pages are kept separate so later stages can point back to a source page.
    """

    source: str            # original file name, e.g. "notes.pdf"
    pages: tuple[str, ...]  # extracted text, one entry per non-empty page

    @property
    def text(self) -> str:
        """All pages joined into a single string."""
        return "\n\n".join(self.pages)

    @property
    def page_count(self) -> int:
        """Number of pages that actually contained text."""
        return len(self.pages)


def load_pdf(path: str | Path) -> Document:
    """Extract text from a PDF file on disk.

    Args:
        path: Path to a .pdf file. This is the "upload" input for now; a web
              upload layer can save the uploaded bytes to disk and call this.

    Raises:
        FileNotFoundError: The file does not exist.
        ValueError: The file is not a PDF, or has no extractable text
                    (an image-only scanned PDF needs OCR, which is a later stage).
    """
    pdf_path = Path(path)

    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got {pdf_path.suffix!r}")

    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if text:  # skip blank / image-only pages
                pages.append(text)

    if not pages:
        raise ValueError(
            f"No extractable text in {pdf_path.name}. "
            "Image-only (scanned) PDFs need OCR, which is a later stage."
        )

    return Document(source=pdf_path.name, pages=tuple(pages))


if __name__ == "__main__":
    # Quick test: uv run python -m simple_rag.ingestion.loader <file.pdf>
    import sys

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: uv run python -m simple_rag.ingestion.loader <file.pdf>"
        )

    doc = load_pdf(sys.argv[1])
    print(f"source          : {doc.source}")
    print(f"pages with text : {doc.page_count}")
    print(f"characters      : {len(doc.text)}")
    print("-" * 40)
    print(doc.text[:500])
