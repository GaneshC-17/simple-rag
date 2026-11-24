"""Ingestion stage 2: clean the text extracted from PDFs.

WHY THIS EXISTS
---------------
PDF text extraction is messy:
  - words split across lines ("Retrieval-\nAugmented")
  - repeated spaces from justified text
  - invisible control characters left by the PDF format
  - ligatures and wide characters (ﬁ, ＡＢＣ)

Feeding that straight into chunking and embeddings wastes tokens and hurts
retrieval quality. This module fixes those problems before later stages.

No new dependencies - this uses only the Python standard library.
"""

from __future__ import annotations

import re
import unicodedata

from simple_rag.ingestion.loader import Document


def clean_text(text: str) -> str:
    """Normalize one piece of extracted text.

    The steps are ordered so each one makes the next one simpler.
    """
    # 1. Unicode compatibility form: ﬁ -> fi, full-width ABC -> ABC, etc.
    text = unicodedata.normalize("NFKC", text)

    # 2. Unify line endings (Windows \r\n and old Mac \r -> \n)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Remove invisible control characters, but keep newlines and tabs
    text = "".join(
        char
        for char in text
        if char in "\n\t" or unicodedata.category(char) != "Cc"
    )

    # 4. Rejoin hyphenated line breaks: "Retrieval-\nAugmented" -> "Retrieval-Augmented"
    text = re.sub(r"-[ \t]*\n[ \t]*", "-", text)

    # 5. Collapse runs of spaces/tabs into one space
    text = re.sub(r"[ \t]+", " ", text)

    # 6. Trim each line, then collapse 3+ blank lines into one blank line
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_document(document: Document) -> Document:
    """Apply clean_text() to every page, keeping the source filename.

    Returns a NEW Document - the original is left untouched, which makes
    debugging easier (you can compare before and after).
    """
    return Document(
        source=document.source,
        pages=tuple(clean_text(page) for page in document.pages),
    )


if __name__ == "__main__":
    # Quick test: uv run python -m simple_rag.ingestion.cleaner
    import sys

    # Windows consoles default to cp1252, which cannot print the ligature below
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    messy = (
        "  Retrieval-\n   Augmented   Generation  \r\n\n\n"
        "Page 1\x0c\n\n  It  combines  retrieval  with  generation.  "
        "The  ﬁnal  step  is  simple.  "
    )
    cleaned = clean_text(messy)

    print("BEFORE:")
    print(repr(messy))
    print("\nAFTER:")
    print(repr(cleaned))
    print("\nRendered:")
    print(cleaned)
