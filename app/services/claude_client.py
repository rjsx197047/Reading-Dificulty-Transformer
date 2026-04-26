"""
Claude API client — optional stronger backend for analysis and transformation.

Used when the caller supplies a Claude API key (via request body or header).
When no key is present, all requests fall back to the local Ollama client.

No key is ever persisted server-side. Keys travel per-request in memory only.

Uses raw httpx calls against the Anthropic Messages API to avoid adding a
heavy SDK dependency to the project.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

# Default model — latest Sonnet for a strong balance of cost and quality.
# Users can override by editing this constant or adding an env setting.
CLAUDE_MODEL = "claude-sonnet-4-5"
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_API_VERSION = "2023-06-01"
TIMEOUT = 60.0
MAX_TOKENS = 1500


def is_valid_api_key_format(api_key: str | None) -> bool:
    """
    Lightweight format check for an Anthropic API key.
    Real validation happens on the first request. This just filters out
    obvious garbage before we even try.
    """
    if not api_key or not isinstance(api_key, str):
        return False
    key = api_key.strip()
    return key.startswith("sk-ant-") and len(key) > 20


async def _query_claude(
    prompt: str,
    api_key: str,
    system: str | None = None,
    max_tokens: int = MAX_TOKENS,
) -> str | None:
    """
    Send a single-turn message to Claude and return the response text.
    Returns None on any failure (invalid key, network error, API error).
    Errors are logged but never raised to the caller.
    """
    if not is_valid_api_key_format(api_key):
        return None

    headers = {
        "x-api-key": api_key,
        "anthropic-version": CLAUDE_API_VERSION,
        "content-type": "application/json",
    }
    body: dict = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                CLAUDE_API_URL, headers=headers, json=body, timeout=TIMEOUT
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", [])
                if content and isinstance(content, list):
                    return content[0].get("text", "").strip()
                return None

            logger.warning("Claude API returned %s: %s", resp.status_code, resp.text[:200])
            return None

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning("Claude API network error: %s", e)
        return None
    except Exception as e:
        logger.warning("Claude API unexpected error: %s", e)
        return None


async def get_ai_analysis_claude(
    text: str, scores_summary: str, api_key: str
) -> str | None:
    """Claude-powered qualitative readability analysis."""
    system = (
        "You are an expert reading-level analyst. Provide concise, insightful "
        "assessments of text complexity grounded in measurable features."
    )
    prompt = f"""Analyze the following text and provide a brief (3–5 sentence) qualitative
assessment of its reading difficulty. Consider vocabulary complexity, sentence
structure, conceptual density, and assumed background knowledge.

Computed readability scores (context):
{scores_summary}

Text to analyze:
---
{text[:3000]}
---

Focus on *why* the text is at the difficulty level it is, and what specific
features contribute to its complexity or simplicity."""
    return await _query_claude(prompt, api_key, system=system)


async def detect_text_type_claude(text: str, api_key: str) -> str | None:
    """
    Ask Claude to classify what *kind* of text the passage is
    (article, news story, play, novel excerpt, essay, etc.).
    Returns a short label (2–5 words) or None on failure.
    """
    system = (
        "You classify short passages of text by their genre and format. "
        "You return only the label — no explanations, no punctuation other than "
        "the label itself."
    )
    prompt = f"""Classify the following text into ONE short label describing its type.

Valid examples include (but are not limited to):
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
    result = await _query_claude(prompt, api_key, system=system, max_tokens=40)
    if result:
        # Strip any trailing period, quotes, or stray whitespace
        return result.strip().strip(".'\" \n").split("\n")[0][:60]
    return None


async def transform_text_claude(text: str, target_level: str, api_key: str, aggressiveness: int = 1) -> str | None:
    """
    Claude-powered transform to a named reading level.

    Args:
        text: Text to rewrite
        target_level: elementary, middle_school, high_school, or college
        api_key: Anthropic API key
        aggressiveness: 1 (normal), 2 (more aggressive), 3 (very aggressive)
    """
    level_descriptions = {
        "elementary": "a 3rd–5th grader (ages 8–11). Use short sentences, common words, simple ideas.",
        "middle_school": "a 6th–8th grader (ages 11–14). Use clear language and moderate sentence length.",
        "high_school": "a 9th–12th grader (ages 14–18). Standard vocabulary and sentence complexity.",
        "college": "a college student. Use precise academic language while remaining clear.",
    }
    audience = level_descriptions.get(target_level, level_descriptions["high_school"])

    # Add aggressiveness instructions
    aggressiveness_instructions = {
        1: "Adjust vocabulary, sentence length, and complexity to match the target level.",
        2: "Simplify significantly. Use very short sentences and replace complex terms with simple ones.",
        3: "Simplify VERY aggressively. Use only simple words and very short sentences. Avoid any complex phrasing.",
    }
    aggressiveness_instr = aggressiveness_instructions.get(aggressiveness, aggressiveness_instructions[1])

    system = "You rewrite text to a target reading level without losing factual content."
    prompt = f"""Rewrite the following text so it is appropriate for {audience}

Rules:
1. Preserve ALL factual information and key ideas — do not omit anything.
2. {aggressiveness_instr}
3. Output ONLY the rewritten text — no explanations, headers, or notes.

Original text:
---
{text[:3000]}
---

Rewritten text:"""
    return await _query_claude(prompt, api_key, system=system)


async def simplify_text_claude(prompt: str, api_key: str) -> str | None:
    """
    Send a pre-built simplification prompt to Claude.
    The caller constructs the prompt via simplifier.build_simplify_prompt().
    """
    system = (
        "You are an expert reading-level adapter for educators and students. "
        "Follow the rules exactly. Output only the rewritten text."
    )
    return await _query_claude(prompt, api_key, system=system)


async def generate_worksheet_versions_claude(
    text: str, api_key: str
) -> dict[str, str] | None:
    """Claude-powered three-version worksheet differentiation."""
    system = "You are a curriculum designer creating differentiated classroom materials."
    prompt = f"""Rewrite the following text into THREE versions at different reading levels.

Rules for each version:
- ADVANCED (Grade 10–12): Rich vocabulary, complex sentences, full academic register.
- STANDARD (Grade 6–8): Clear language, moderate sentence length, common vocabulary.
- SIMPLIFIED (Grade 3–5): Very simple words, short sentences (under 15 words), concrete ideas.

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
    response = await _query_claude(prompt, api_key, system=system, max_tokens=2500)
    if not response:
        return None

    # Reuse the same parser shape as the Ollama client
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

    if not all(k in result and result[k] for k in ("advanced", "standard", "simplified")):
        return None

    return result
