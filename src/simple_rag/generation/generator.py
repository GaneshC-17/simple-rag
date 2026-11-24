"""Generation stage: ask the LLM to answer using the retrieved context.

The LLM is reached through freellmapi, a router running locally on this
machine that forwards to free cloud models. We use the official OpenAI SDK
with a custom base_url and the unified freellmapi key from .env.
"""

from __future__ import annotations

from openai import APIConnectionError, APIStatusError, OpenAI

from simple_rag.config import get_settings
from simple_rag.prompts.context import Context
from simple_rag.prompts.templates import SYSTEM_PROMPT, USER_TEMPLATE


def _client() -> OpenAI:
    """Build an OpenAI SDK client pointed at the local freellmapi router."""
    settings = get_settings()
    if not settings.llm_api_key.startswith("freellmapi-"):
        raise RuntimeError(
            "LLM_API_KEY does not look like a freellmapi key "
            "(expected 'freellmapi-...'). Check your .env file."
        )
    return OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


def generate_answer(question: str, context: Context) -> str:
    """Answer a question grounded in the provided context.

    Returns a short 'I don't know' message if there is no context at all, so
    we never spend a token asking the model to answer from nothing.
    """
    if not context.text.strip():
        return "I don't know based on the provided documents."

    settings = get_settings()
    user_message = USER_TEMPLATE.format(context=context.text, question=question)

    try:
        response = _client().chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
        )
    except APIConnectionError as exc:
        raise RuntimeError(
            f"Cannot reach freellmapi at {settings.llm_base_url}. "
            "Is the freellmapi desktop app running?"
        ) from exc
    except APIStatusError as exc:
        raise RuntimeError(
            f"freellmapi returned HTTP {exc.status_code}: {exc.message}"
        ) from exc

    return (response.choices[0].message.content or "").strip()


if __name__ == "__main__":
    # Quick test: uv run python -m simple_rag.generation.generator
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from simple_rag.pipeline import context_for

    query = "What is heredity?"
    built = context_for(query, top_k=3)
    print(f"context: {built.chunk_count} chunks, {built.token_count} tokens")
    print("-" * 60)
    print(generate_answer(query, built))
