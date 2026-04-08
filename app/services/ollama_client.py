"""
Ollama integration for AI-powered reading analysis and text transformation.

All Ollama calls are optional — the app degrades gracefully when Ollama
is unavailable, falling back to formula-only analysis.
"""

import httpx

from app.core.config import settings

TIMEOUT = 120.0  # Ollama can be slow on first inference


async def is_ollama_available() -> bool:
    """Check whether the Ollama server is reachable."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


async def get_ai_analysis(text: str, scores_summary: str) -> str | None:
    """
    Ask Ollama for a qualitative analysis of the text's reading difficulty.
    Returns None if Ollama is unavailable.
    """
    prompt = f"""You are an expert reading-level analyst. Analyze the following text and provide
a brief (3-5 sentence) qualitative assessment of its reading difficulty. Consider vocabulary
complexity, sentence structure, conceptual density, and assumed background knowledge.

Here are the computed readability scores for context:
{scores_summary}

Text to analyze:
---
{text[:3000]}
---

Provide your analysis in a concise paragraph. Focus on *why* the text is at the difficulty
level it is, and what specific features contribute to its complexity or simplicity."""

    return await _query_ollama(prompt)


async def transform_text(text: str, target_level: str) -> str | None:
    """
    Ask Ollama to rewrite the text at the specified target reading level.
    Returns None if Ollama is unavailable.
    """
    level_descriptions = {
        "elementary": "a 3rd-5th grader (ages 8-11). Use short sentences, common words, and simple ideas.",
        "middle_school": "a 6th-8th grader (ages 11-14). Use clear language and moderate sentence length.",
        "high_school": "a 9th-12th grader (ages 14-18). Standard vocabulary and sentence complexity.",
        "college": "a college student. Use precise academic language while remaining clear.",
    }

    audience = level_descriptions.get(target_level, level_descriptions["high_school"])

    prompt = f"""Rewrite the following text so it is appropriate for {audience}

Important rules:
1. Preserve ALL factual information and key ideas — do not omit anything.
2. Adjust vocabulary, sentence length, and complexity to match the target level.
3. Output ONLY the rewritten text — no explanations, headers, or notes.

Original text:
---
{text[:3000]}
---

Rewritten text:"""

    return await _query_ollama(prompt)


async def _query_ollama(prompt: str) -> str | None:
    """Send a prompt to Ollama and return the response text, or None on failure."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 1024},
                },
                timeout=TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            return None
    except (httpx.ConnectError, httpx.TimeoutException, Exception):
        return None
