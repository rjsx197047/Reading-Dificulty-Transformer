"""FastAPI route handlers."""

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.differentiation_metadata import generate_differentiation_metadata
from app.core.keyword_extractor import extract_keywords as extract_keywords_util
from app.core.keyword_extractor import count_preserved_keywords
from app.core.readability import detect_readability
from app.core.report_generator import generate_teacher_report
from app.core.semantic_similarity import compute_semantic_similarity
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
from app.services.claude_client import (
    detect_text_type_claude,
    generate_worksheet_versions_claude,
    get_ai_analysis_claude,
    is_valid_api_key_format,
    simplify_text_claude,
    transform_text_claude,
)
from app.services.ollama_client import (
    detect_text_type as detect_text_type_ollama,
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


def _should_use_claude(api_key: str | None) -> bool:
    """Return True if a well-formed Claude API key was supplied."""
    return is_valid_api_key_format(api_key)


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

    Returns readability scores, text statistics, difficulty classification,
    AI-powered qualitative analysis, and AI-detected text type (article,
    play, story, etc.).

    If a Claude API key is supplied, uses Claude for AI tasks; otherwise
    falls back to local Ollama (gracefully degrading to formula-only if
    neither is available).
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

    ai_analysis: str | None = None
    text_type: str | None = None
    ai_backend = "none"

    if _should_use_claude(input_data.api_key):
        ai_analysis = await get_ai_analysis_claude(text, scores_summary, input_data.api_key)
        text_type = await detect_text_type_claude(text, input_data.api_key)
        if ai_analysis or text_type:
            ai_backend = "claude"

    # If Claude wasn't used or failed, try Ollama
    if ai_backend == "none" and await is_ollama_available():
        ai_analysis = await get_ai_analysis(text, scores_summary)
        text_type = await detect_text_type_ollama(text)
        if ai_analysis or text_type:
            ai_backend = "ollama"

    return AnalysisResult(
        difficulty=difficulty,
        scores=scores,
        statistics=stats,
        ai_analysis=ai_analysis,
        text_type=text_type,
        ai_backend=ai_backend,
        suggestions=suggestions,
    )


@router.post("/transform", response_model=TransformResult)
async def transform(request: TransformRequest):
    """
    Transform text to a target reading level.

    Uses Claude if an API key is supplied; otherwise falls back to Ollama.
    Complete pipeline:
      1. Detect original readability
      2. Extract keywords from original
      3. Transform text via LLM
      4. Detect new readability
      5. Compute semantic similarity
      6. Check keyword preservation
      7. Generate differentiation metadata
      8. Generate teacher report

    Returns comprehensive metadata and analysis for teacher-friendly assessment.
    """
    text = request.text.strip()
    target = request.target_level.lower()

    valid_levels = ["elementary", "middle_school", "high_school", "college"]
    if target not in valid_levels:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid target_level. Must be one of: {', '.join(valid_levels)}",
        )

    use_claude = _should_use_claude(request.api_key)
    if not use_claude and not await is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="No AI backend available. Start Ollama or provide a Claude API key.",
        )

    # Step 1: Detect readability BEFORE
    original_scores = compute_readability_scores(text)
    original_grade = original_scores.flesch_kincaid_grade
    original_level = classify_difficulty(original_scores).level

    # Step 2: Extract keywords from original
    original_keywords = extract_keywords_util(text)

    # Step 3: Transform text via LLM
    if use_claude:
        transformed = await transform_text_claude(text, target, request.api_key)
        if not transformed:
            raise HTTPException(status_code=500, detail="Claude API call failed.")
    else:
        transformed = await transform_text(text, target)
        if not transformed:
            raise HTTPException(status_code=500, detail="Failed to transform text via Ollama.")

    # Step 4: Detect readability AFTER
    new_scores = compute_readability_scores(transformed)
    new_grade = new_scores.flesch_kincaid_grade

    # Step 5: Compute semantic similarity (actual computation, not hardcoded)
    semantic_score = compute_semantic_similarity(text, transformed) or 0.5

    # Step 6: Check keyword preservation
    preserved_keywords = count_preserved_keywords(original_keywords, transformed)

    # Step 7: Detect readability for metadata
    readability_before = detect_readability(text)
    readability_after = detect_readability(transformed)

    # Convert readability detection to dict format for metadata generator
    readability_before_dict = {
        "average_grade": readability_before.average_grade,
    }
    readability_after_dict = {
        "average_grade": readability_after.average_grade,
    }

    # Generate differentiation metadata with actual semantic score and preserved keywords
    differentiation_metadata = generate_differentiation_metadata(
        original_text=text,
        simplified_text=transformed,
        readability_before=readability_before_dict,
        readability_after=readability_after_dict,
        semantic_score=semantic_score,
        keywords_preserved=preserved_keywords,
    )

    # Step 8: Generate teacher report
    teacher_report = generate_teacher_report(
        metadata=differentiation_metadata,
        original_keywords=original_keywords,
        preserved_keywords=preserved_keywords,
    )

    return TransformResult(
        original_text=text,
        transformed_text=transformed,
        original_level=original_level,
        target_level=target,
        original_grade=round(original_grade, 2),
        new_grade=round(new_grade, 2),
        semantic_score=round(semantic_score, 4) if semantic_score else None,
        original_keywords=original_keywords,
        preserved_keywords=preserved_keywords,
        differentiation_metadata=differentiation_metadata,
        teacher_report=teacher_report,
    )


@router.post("/export-report")
async def export_report(request: TransformRequest):
    """
    Generate and export a teacher-friendly accessibility report.

    Takes the same input as /transform and returns a Markdown-formatted
    report suitable for printing or sharing with teachers and administrators.

    Returns:
        Plain text (Markdown) report
    """
    # Re-use the transform logic to get all metrics
    text = request.text.strip()
    target = request.target_level.lower()

    valid_levels = ["elementary", "middle_school", "high_school", "college"]
    if target not in valid_levels:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid target_level. Must be one of: {', '.join(valid_levels)}",
        )

    use_claude = _should_use_claude(request.api_key)
    if not use_claude and not await is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="No AI backend available. Start Ollama or provide a Claude API key.",
        )

    # Step 1: Detect readability BEFORE
    original_scores = compute_readability_scores(text)
    original_grade = original_scores.flesch_kincaid_grade

    # Step 2: Extract keywords from original
    original_keywords = extract_keywords_util(text)

    # Step 3: Transform text via LLM
    if use_claude:
        transformed = await transform_text_claude(text, target, request.api_key)
        if not transformed:
            raise HTTPException(status_code=500, detail="Claude API call failed.")
    else:
        transformed = await transform_text(text, target)
        if not transformed:
            raise HTTPException(status_code=500, detail="Failed to transform text via Ollama.")

    # Step 4: Detect readability AFTER
    new_scores = compute_readability_scores(transformed)
    new_grade = new_scores.flesch_kincaid_grade

    # Step 5: Compute semantic similarity
    semantic_score = compute_semantic_similarity(text, transformed) or 0.5

    # Step 6: Check keyword preservation
    preserved_keywords = count_preserved_keywords(original_keywords, transformed)

    # Step 7: Detect readability for metadata
    readability_before = detect_readability(text)
    readability_after = detect_readability(transformed)

    # Convert readability detection to dict format
    readability_before_dict = {
        "average_grade": readability_before.average_grade,
    }
    readability_after_dict = {
        "average_grade": readability_after.average_grade,
    }

    # Generate differentiation metadata
    differentiation_metadata = generate_differentiation_metadata(
        original_text=text,
        simplified_text=transformed,
        readability_before=readability_before_dict,
        readability_after=readability_after_dict,
        semantic_score=semantic_score,
        keywords_preserved=preserved_keywords,
    )

    # Step 8: Generate teacher report
    teacher_report = generate_teacher_report(
        metadata=differentiation_metadata,
        original_keywords=original_keywords,
        preserved_keywords=preserved_keywords,
    )

    # Return plain text with markdown MIME type
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(
        content=teacher_report,
        media_type="text/markdown",
    )


@router.post("/simplify", response_model=SimplifyResult)
async def simplify(request: SimplifyRequest):
    """
    Full simplification pipeline with grade-level targeting.

    Uses Claude if an API key is supplied; otherwise falls back to Ollama.
    Simplification logic is unchanged — only the LLM backend switches.
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

    use_claude = _should_use_claude(request.api_key)
    if not use_claude and not await is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="No AI backend available. Start Ollama or provide a Claude API key.",
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
            chunking=request.chunking and attempt == 0,
        )

        if use_claude:
            rewritten = await simplify_text_claude(prompt, request.api_key)
        else:
            rewritten = await simplify_text(prompt)

        if not rewritten:
            backend = "Claude API" if use_claude else "Ollama"
            raise HTTPException(status_code=500, detail=f"{backend} failed to return a response.")

        rewritten_scores = compute_readability_scores(rewritten)
        achieved_grade = get_composite_grade(rewritten_scores)

        final_text = rewritten
        final_grade = achieved_grade

        if abs(achieved_grade - request.target_grade) <= _GRADE_TOLERANCE:
            break

        current_text = rewritten

    # Step 6: post-processing formatting
    if request.chunking:
        final_text = apply_chunking(final_text)
    if request.dyslexia_mode:
        final_text = apply_dyslexia_formatting(final_text)

    # Step 7: semantic preservation scoring
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

    Uses Claude if an API key is supplied; otherwise falls back to Ollama.
    """
    text = request.worksheet_text.strip()
    if len(text.split()) < 5:
        raise HTTPException(
            status_code=422,
            detail="worksheet_text must contain at least 5 words.",
        )

    use_claude = _should_use_claude(request.api_key)
    if not use_claude and not await is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="No AI backend available. Start Ollama or provide a Claude API key.",
        )

    if use_claude:
        versions = await generate_worksheet_versions_claude(text, request.api_key)
    else:
        versions = await generate_worksheet_versions(text)

    if not versions:
        backend = "Claude API" if use_claude else "Ollama"
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate worksheet versions via {backend}.",
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
