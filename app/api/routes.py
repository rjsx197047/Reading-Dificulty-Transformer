"""FastAPI route handlers."""

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.models.schemas import (
    AnalysisResult,
    HealthResponse,
    TextInput,
    TransformRequest,
    TransformResult,
)
from app.services.ollama_client import get_ai_analysis, is_ollama_available, transform_text
from app.services.readability import analyze_text, compute_readability_scores

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    ollama_ok = await is_ollama_available()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        ollama_available=ollama_ok,
    )


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(input_data: TextInput):
    """
    Analyze the reading difficulty of the given text.

    Returns readability scores, text statistics, a difficulty classification,
    and an optional AI-powered qualitative analysis (if Ollama is running).
    """
    text = input_data.text.strip()
    if len(text.split()) < 10:
        raise HTTPException(
            status_code=422,
            detail="Text must contain at least 10 words for meaningful analysis.",
        )

    difficulty, scores, stats, suggestions = analyze_text(text)

    # Try AI analysis (non-blocking; returns None if Ollama is down)
    scores_summary = (
        f"Flesch Reading Ease: {scores.flesch_reading_ease}, "
        f"Flesch-Kincaid Grade: {scores.flesch_kincaid_grade}, "
        f"Gunning Fog: {scores.gunning_fog}, "
        f"SMOG: {scores.smog_index}"
    )
    ai_analysis = await get_ai_analysis(text, scores_summary)

    return AnalysisResult(
        difficulty=difficulty,
        scores=scores,
        statistics=stats,
        ai_analysis=ai_analysis,
        suggestions=suggestions,
    )


@router.post("/transform", response_model=TransformResult)
async def transform(request: TransformRequest):
    """
    Transform text to a target reading level using Ollama.

    Requires Ollama to be running. Falls back to an error if unavailable.
    """
    text = request.text.strip()
    target = request.target_level.lower()

    valid_levels = ["elementary", "middle_school", "high_school", "college"]
    if target not in valid_levels:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid target_level. Must be one of: {', '.join(valid_levels)}",
        )

    if not await is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama is not available. Please start Ollama to use the transform feature.",
        )

    # Get original grade
    original_scores = compute_readability_scores(text)
    original_grade = original_scores.flesch_kincaid_grade

    # Transform
    transformed = await transform_text(text, target)
    if not transformed:
        raise HTTPException(status_code=500, detail="Failed to transform text via Ollama.")

    # Get new grade
    new_scores = compute_readability_scores(transformed)
    new_grade = new_scores.flesch_kincaid_grade

    # Classify original level
    from app.services.readability import classify_difficulty

    original_level = classify_difficulty(original_scores).level

    return TransformResult(
        original_text=text,
        transformed_text=transformed,
        original_level=original_level,
        target_level=target,
        original_grade=round(original_grade, 2),
        new_grade=round(new_grade, 2),
    )
