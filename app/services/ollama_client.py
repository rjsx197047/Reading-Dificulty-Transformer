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


async def detect_text_type(text: str) -> str | None:
    """
    Ask Ollama to classify what kind of text a passage is
    (article, news, play, novel excerpt, essay, etc.).
    Returns a short label (2–5 words) or None on failure.
    """
    prompt = f"""Classify the following text into ONE short label describing its type.

Valid examples (but not limited to):
  News Article, Academic Paper, Textbook Chapter, Play / Drama,
  Novel Excerpt, Short Story, Personal Essay, Opinion Editorial,
  Technical Documentation, Scientific Abstract, Legal Document,
  Recipe, Letter / Correspondence, Poem, Song Lyrics, Speech,
  Homework Instructions, Blog Post, Advertisement, Dialogue Excerpt

Respond with ONLY the label (no extra words, no punctuation beyond the label).

Text:
---
{text[:2500]}
---

Label:"""
    result = await _query_ollama(prompt)
    if result:
        return result.strip().strip(".'\" \n").split("\n")[0][:60]
    return None


async def simplify_text(prompt: str) -> str | None:
    """
    Send a fully-built simplification prompt to Ollama and return the response.
    The caller (routes.py) is responsible for constructing the prompt via
    app.services.simplifier.build_simplify_prompt().
    Returns None if Ollama is unavailable.
    """
    return await _query_ollama(prompt)


async def generate_worksheet_versions(text: str) -> dict[str, str] | None:
    """
    Ask Ollama to produce three differentiated versions of the given worksheet text:
    advanced (Grade 10+), standard (Grade 6-8), and simplified (Grade 3-5).
    Returns a dict with keys 'advanced', 'standard', 'simplified', or None on failure.
    """
    prompt = f"""You are an experienced curriculum designer creating differentiated materials.

Rewrite the following text into THREE versions at different reading levels.

Rules for each version:
- ADVANCED (Grade 10-12): Rich vocabulary, complex sentences, full academic register.
- STANDARD (Grade 6-8): Clear language, moderate sentence length, common vocabulary.
- SIMPLIFIED (Grade 3-5): Very simple words, short sentences (under 15 words), concrete ideas.

All versions must preserve the same factual content and meaning.

Original text:
---
{text[:3000]}
---

Respond in EXACTLY this format with no extra text:
ADVANCED:
<advanced version here>

STANDARD:
<standard version here>

SIMPLIFIED:
<simplified version here>"""

    response = await _query_ollama(prompt)
    if not response:
        return None

    result: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in response.splitlines():
        upper = line.strip().upper()
        if upper.startswith("ADVANCED:"):
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = "advanced"
            current_lines = [line[line.upper().find("ADVANCED:") + 9:].strip()]
        elif upper.startswith("STANDARD:"):
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = "standard"
            current_lines = [line[line.upper().find("STANDARD:") + 9:].strip()]
        elif upper.startswith("SIMPLIFIED:"):
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = "simplified"
            current_lines = [line[line.upper().find("SIMPLIFIED:") + 11:].strip()]
        elif current_key is not None:
            current_lines.append(line)

    if current_key:
        result[current_key] = "\n".join(current_lines).strip()

    # Ensure all three keys are present
    if not all(k in result and result[k] for k in ("advanced", "standard", "simplified")):
        return None

    return result


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
