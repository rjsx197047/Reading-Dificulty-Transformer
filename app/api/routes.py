"""FastAPI route handlers."""

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.readability import detect_readability
from app.core.semantic_similarity import semantic_preservation_score
from app.models.schemas import (
    AnalysisResult,
    HealthResponse,
    ReadabilityDetectionResult,
    SimplifyRequest,
    SimplifyResult,
    TextInput,
    TransformRequest,
    TransformResult,
    WorksheetRequest,
    WorksheetResult,
)
from app.services import semantic as semantic_svc
from app.services.ollama_client import (
    generate_worksheet_versions,
    get_ai_analysis,
    is_ollama_available,
    simplify_text,
    transform_text,
)
from app.services.readability import (
    analyze_text,
    classify_difficulty,
    compute_readability_scores,
    get_composite_grade,
)
from app.services.simplifier import (
    apply_chunking,
    apply_dyslexia_formatting,
    apply_vocab_replacements,
    build_simplify_prompt,
    extract_keywords,
)

router = APIRouter()

# Tolerance for the readability verification loop (±grade levels)
_GRADE_TOLERANCE = 0.5
# Maximum rewrite attempts in the verification loop
_MAX_RETRIES = 3


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    ollama_ok = await is_ollama_available()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        ollama_available=ollama_ok,
        semantic_scoring_available=semantic_svc.is_available(),
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

    Requires Ollama to be running.
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

    original_scores = compute_readability_scores(text)
    original_grade = original_scores.flesch_kincaid_grade

    transformed = await transform_text(text, target)
    if not transformed:
        raise HTTPException(status_code=500, detail="Failed to transform text via Ollama.")

    new_scores = compute_readability_scores(transformed)
    new_grade = new_scores.flesch_kincaid_grade
    original_level = classify_difficulty(original_scores).level

    return TransformResult(
        original_text=text,
        transformed_text=transformed,
        original_level=original_level,
        target_level=target,
        original_grade=round(original_grade, 2),
        new_grade=round(new_grade, 2),
    )


@router.post("/simplify", response_model=SimplifyResult)
async def simplify(request: SimplifyRequest):
    """
    Full simplification pipeline with grade-level targeting.

    Pipeline steps:
    1. Detect original reading level (composite grade).
    2. Apply vocabulary pre-processing (replacement dictionary).
    3. Extract and lock keywords if preserve_keywords=True.
    4. Send to Ollama with a grade-targeted prompt.
    5. Verify achieved grade level; retry up to 3 times if outside ±0.5 tolerance.
    6. Apply chunking / dyslexia formatting if requested.
    7. Compute semantic similarity score if sentence-transformers is available.
    8. Return structured JSON result.
    """
    text = request.input_text.strip()
    if len(text.split()) < 5:
        raise HTTPException(
            status_code=422,
            detail="input_text must contain at least 5 words.",
        )

    valid_modes = ("standard", "esl")
    if request.mode not in valid_modes:
        raise HTTPException(
            status_code=422,
            detail=f"mode must be one of: {', '.join(valid_modes)}",
        )

    if not await is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama is not available. Please start Ollama to use /simplify.",
        )

    # Step 1: detect original level
    original_scores = compute_readability_scores(text)
    original_level = get_composite_grade(original_scores)

    # Step 2: vocabulary pre-processing
    preprocessed = apply_vocab_replacements(text)

    # Step 3: keyword extraction
    keywords: list[str] = []
    if request.preserve_keywords:
        keywords = extract_keywords(text)

    # Steps 4 + 5: rewrite with verification loop
    current_text = preprocessed
    final_text = preprocessed
    final_grade = original_level

    for attempt in range(_MAX_RETRIES):
        prompt = build_simplify_prompt(
            text=current_text,
            target_grade=request.target_grade,
            keywords=keywords,
            preserve_keywords=request.preserve_keywords,
            mode=request.mode,
            instruction_mode=request.instruction_mode,
            chunking=request.chunking and attempt == 0,  # only inject chunking rule once
        )

        rewritten = await simplify_text(prompt)
        if not rewritten:
            raise HTTPException(status_code=500, detail="Ollama failed to return a response.")

        rewritten_scores = compute_readability_scores(rewritten)
        achieved_grade = get_composite_grade(rewritten_scores)

        final_text = rewritten
        final_grade = achieved_grade

        if abs(achieved_grade - request.target_grade) <= _GRADE_TOLERANCE:
            break  # Within tolerance — done

        # Feed the rewritten text back for another pass
        current_text = rewritten

    # Step 6: post-processing formatting
    if request.chunking:
        final_text = apply_chunking(final_text)
    if request.dyslexia_mode:
        final_text = apply_dyslexia_formatting(final_text)

    # Step 7: semantic preservation scoring (new core module, sklearn-based)
    sem_score = semantic_preservation_score(text, final_text)

    # Step 8: readability detection — bracket original and final text
    _orig_rd = detect_readability(text)
    _final_rd = detect_readability(final_text)

    readability_before = ReadabilityDetectionResult(
        flesch_kincaid=_orig_rd.flesch_kincaid,
        coleman_liau=_orig_rd.coleman_liau,
        smog=_orig_rd.smog,
        ari=_orig_rd.ari,
        average_grade=_orig_rd.average_grade,
    )
    readability_after = ReadabilityDetectionResult(
        flesch_kincaid=_final_rd.flesch_kincaid,
        coleman_liau=_final_rd.coleman_liau,
        smog=_final_rd.smog,
        ari=_final_rd.ari,
        average_grade=_final_rd.average_grade,
    )

    return SimplifyResult(
        original_text=text,
        simplified_text=final_text,
        original_level=original_level,
        target_level=request.target_grade,
        final_level=final_grade,
        readability_before=readability_before,
        readability_after=readability_after,
        semantic_preservation_score=sem_score,
        keywords_preserved=keywords if request.preserve_keywords else [],
        # Backward-compatible aliases for existing UI/clients
        meaning_score=sem_score,
        original_readability=readability_before,
        final_readability=readability_after,
    )


@router.post("/worksheet_versions", response_model=WorksheetResult)
async def worksheet_versions(request: WorksheetRequest):
    """
    Generate three differentiated versions of a worksheet:
    - Advanced (Grade 10-12)
    - Standard (Grade 6-8)
    - Simplified (Grade 3-5)

    Requires Ollama.
    """
    text = request.worksheet_text.strip()
    if len(text.split()) < 5:
        raise HTTPException(
            status_code=422,
            detail="worksheet_text must contain at least 5 words.",
        )

    if not await is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama is not available. Please start Ollama to use /worksheet_versions.",
        )

    versions = await generate_worksheet_versions(text)
    if not versions:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate worksheet versions via Ollama.",
        )

    def _grade(t: str) -> float:
        return get_composite_grade(compute_readability_scores(t))

    return WorksheetResult(
        advanced_version=versions["advanced"],
        standard_version=versions["standard"],
        simplified_version=versions["simplified"],
        advanced_grade=_grade(versions["advanced"]),
        standard_grade=_grade(versions["standard"]),
        simplified_grade=_grade(versions["simplified"]),
    )
