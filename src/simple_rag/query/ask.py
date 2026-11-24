"""User question feature: collect a question from the user.

This stage only handles INPUT. It does not embed the question or call an LLM
yet - those are separate stages added later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

EXIT_WORDS = {"q", "quit", "exit"}


@dataclass(frozen=True)
class Question:
    """A validated question typed by the user."""

    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("question must not be empty")


def read_question(
    prompt: str = "Ask a question (or 'quit' to exit): ",
) -> Question | None:
    """Read one question from the terminal.

    Returns None when the user wants to quit. Empty input is ignored and the
    prompt is shown again.
    """
    while True:
        raw = input(prompt).strip()
        if raw.lower() in EXIT_WORDS:
            return None
        if raw:
            return Question(raw)
        print("(empty question ignored - please try again)")


def iter_questions(
    prompt: str = "Ask a question (or 'quit' to exit): ",
) -> Iterator[Question]:
    """Keep asking until the user types a quit word."""
    while True:
        question = read_question(prompt)
        if question is None:
            break
        yield question
