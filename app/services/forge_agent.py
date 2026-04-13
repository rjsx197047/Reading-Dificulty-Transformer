"""
Forge AI integration module — ReadingDifficultyAgent.

Provides a structured agent interface compatible with multi-agent orchestration
pipelines. All methods are async and return structured dicts suitable for
JSON serialization or downstream agent consumption.

Usage example:
    agent = ReadingDifficultyAgent()
    result = await agent.simplify_text(
        input_text="...",
        target_grade=5.0,
        preserve_keywords=True,
    )
"""

from __future__ import annotations

import httpx

# Default base URL — override via constructor or environment variable
_DEFAULT_API_BASE = "http://localhost:8000/api"


class ReadingDifficultyAgent:
    """
    Agent wrapper around the Reading Difficulty Transformer API.

    Designed for use in multi-agent orchestration pipelines (e.g., Forge AI).
    Each method maps 1-to-1 with a FastAPI endpoint and returns structured dicts.
    """

    def __init__(self, api_base: str = _DEFAULT_API_BASE, timeout: float = 120.0):
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    async def detect_level(self, input_text: str) -> dict:
        """
        Detect the reading level of the given text.

        Returns:
            {
                "difficulty": { "level": str, "grade_range": str, ... },
                "scores": { "flesch_kincaid_grade": float, ... },
                "statistics": { "word_count": int, ... },
                "suggestions": [str, ...],
                "ai_analysis": str | None
            }
        """
        return await self._post("/analyze", {"text": input_text})

    async def simplify_text(
        self,
        input_text: str,
        target_grade: float = 6.0,
        chunking: bool = False,
        preserve_keywords: bool = False,
        mode: str = "standard",
        instruction_mode: bool = False,
        dyslexia_mode: bool = False,
    ) -> dict:
        """
        Simplify text to the target grade level.

        Returns structured result matching SimplifyResult schema:
            {
                "original_level": float,
                "target_level": float,
                "final_level": float,
                "meaning_score": float | None,
                "simplified_text": str,
                "keywords_preserved": [str, ...]
            }
        """
        return await self._post(
            "/simplify",
            {
                "input_text": input_text,
                "target_grade": target_grade,
                "chunking": chunking,
                "preserve_keywords": preserve_keywords,
                "mode": mode,
                "instruction_mode": instruction_mode,
                "dyslexia_mode": dyslexia_mode,
            },
        )

    async def generate_versions(self, worksheet_text: str) -> dict:
        """
        Generate three differentiated versions of a worksheet.

        Returns:
            {
                "advanced_version": str,
                "standard_version": str,
                "simplified_version": str,
                "advanced_grade": float,
                "standard_grade": float,
                "simplified_grade": float
            }
        """
        return await self._post("/worksheet_versions", {"worksheet_text": worksheet_text})

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    async def health(self) -> dict:
        """Return API health status including Ollama and semantic scoring availability."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.api_base}/health")
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _post(self, endpoint: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.api_base}{endpoint}", json=payload)
            resp.raise_for_status()
            return resp.json()
