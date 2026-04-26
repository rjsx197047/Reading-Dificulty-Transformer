"""FastAPI route handlers."""

import logging
from typing import Union

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.core.differentiation_metadata import generate_differentiation_metadata
from app.core.document_transformer import compute_document_metrics, segment_paragraphs
from app.core.keyword_extractor import extract_keywords as extract_keywords_util
from app.core.keyword_extractor import count_preserved_keywords
from app.core.pdf_extractor import extract_text_from_pdf, validate_pdf_file
from app.core.readability import detect_readability
from app.core.reliability_assessment import assess_reliability
from app.core.report_generator import generate_document_report, generate_teacher_report
from app.core.semantic_similarity import compute_semantic_similarity
from app.core.semantic_similarity import semantic_preservation_score
from app.models.schemas import (
    AnalysisResult,
    DocumentMetrics,
    DocumentTransformRequest,
    DocumentTransformResult,
    ExportReportRequest,
    HealthResponse,
    ParagraphTransformResult,
    PDFUploadResponse,
    ReadabilityDetectionResult,
    SimplifyRequest,
    SimplifyResult,
    TextInput,
    TransformRequest,
    TransformResult,
    UnifiedTransformResult,
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

logger = logging.getLogger(__name__)

router = APIRouter()

# Tolerance for the readability verification loop (±grade levels)
_GRADE_TOLERANCE = 0.5
# Maximum rewrite attempts in the verification loop
_MAX_RETRIES = 3

# Target level to approximate grade-level mapping (midpoint of range)
# Used by /transform for iterative grade calibration
_TARGET_LEVEL_TO_GRADE = {
    "elementary": 4.0,      # 3rd–5th grade midpoint
    "middle_school": 7.0,   # 6th–8th grade midpoint
    "high_school": 10.5,    # 9th–12th grade midpoint
    "college": 14.0,        # college midpoint
}

# Tolerance for /transform grade correction loop (looser than /simplify)
_TRANSFORM_GRADE_TOLERANCE = 2.0
_TRANSFORM_MAX_PASSES = 3


def _should_use_claude(api_key: str | None) -> bool:
    """Return True if a well-formed Claude API key was supplied."""
    return is_valid_api_key_format(api_key)


async def _run_transform_pipeline(
    text: str,
    target: str,
    api_key: str | None,
) -> dict:
    """
    Run the complete transform pipeline with iterative grade calibration.

    Shared between /transform and /export-report to avoid code duplication.

    Pipeline steps:
      1. Detect original readability & keywords
      2. Iterative rewrite loop (max 3 passes):
         - Transform text via LLM
         - Detect new readability
         - If within tolerance of target grade, stop
         - Otherwise retry with adjusted aggressiveness
      3. Compute semantic similarity
      4. Check keyword preservation
      5. Generate differentiation metadata & teacher report

    Returns:
        dict with all pipeline outputs ready for response construction.
    """
    use_claude = _should_use_claude(api_key)

    # Step 1: Detect readability BEFORE
    original_scores = compute_readability_scores(text)
    original_grade = original_scores.flesch_kincaid_grade
    original_level = classify_difficulty(original_scores).level

    # Step 2: Extract keywords from original
    original_keywords = extract_keywords_util(text)

    # Look up numeric target grade for calibration
    target_grade_numeric = _TARGET_LEVEL_TO_GRADE.get(target, 7.0)

    # Step 3: Iterative transformation loop with grade correction
    transformed = None
    new_grade = None
    grade_alignment_delta = None
    current_aggressiveness = 1  # Start with normal aggressiveness; increment on retry

    for attempt in range(_TRANSFORM_MAX_PASSES):
        logger.info(
            "Transform attempt %d/%d: target=%s (grade %.1f), aggressiveness=%d",
            attempt + 1,
            _TRANSFORM_MAX_PASSES,
            target,
            target_grade_numeric,
            current_aggressiveness,
        )

        # Transform text via LLM with current aggressiveness level
        if use_claude:
            candidate = await transform_text_claude(
                text, target, api_key, aggressiveness=current_aggressiveness
            )
            if not candidate:
                raise HTTPException(status_code=500, detail="Claude API call failed.")
        else:
            candidate = await transform_text(text, target, aggressiveness=current_aggressiveness)
            if not candidate:
                raise HTTPException(
                    status_code=500, detail="Failed to transform text via Ollama."
                )

        # Detect new readability
        candidate_scores = compute_readability_scores(candidate)
        candidate_grade = candidate_scores.flesch_kincaid_grade
        grade_alignment_delta = abs(candidate_grade - target_grade_numeric)

        logger.info(
            "Attempt %d result: achieved grade %.2f (target %.1f, delta %.2f)",
            attempt + 1,
            candidate_grade,
            target_grade_numeric,
            grade_alignment_delta,
        )

        # Accept this result
        transformed = candidate
        new_grade = candidate_grade

        # Check tolerance — stop if close enough (within 1 grade level)
        if grade_alignment_delta <= 1.0:
            logger.info(
                "Attempt %d: grade alignment delta %.2f ≤ 1.0, accepting result",
                attempt + 1,
                grade_alignment_delta,
            )
            break

        # Prepare for next retry (if not final attempt)
        if attempt < _TRANSFORM_MAX_PASSES - 1:
            # Increment aggressiveness for next attempt (up to 3)
            if current_aggressiveness < 3:
                current_aggressiveness += 1
                logger.info(
                    "Grade alignment delta %.2f > 1.0, increasing aggressiveness to %d for next attempt",
                    grade_alignment_delta,
                    current_aggressiveness,
                )

    if transformed is None:
        raise HTTPException(status_code=500, detail="Transform pipeline failed to produce output.")

    # Step 4: Compute semantic similarity (actual embedding-based computation)
    computed_similarity = compute_semantic_similarity(text, transformed)
    # Use actual score if available; only fall back to 0.5 if model is unavailable
    if computed_similarity is not None:
        semantic_score = computed_similarity
        semantic_score_was_computed = True
    else:
        semantic_score = 0.5
        semantic_score_was_computed = False
        logger.warning("Semantic similarity model unavailable — using neutral fallback 0.5")

    # Step 5: Check keyword preservation
    preserved_keywords = count_preserved_keywords(original_keywords, transformed)

    # Step 6: Detect readability for metadata
    readability_before = detect_readability(text)
    readability_after = detect_readability(transformed)

    readability_before_dict = {"average_grade": readability_before.average_grade}
    readability_after_dict = {"average_grade": readability_after.average_grade}

    # Step 7: Generate differentiation metadata
    differentiation_metadata = generate_differentiation_metadata(
        original_text=text,
        simplified_text=transformed,
        readability_before=readability_before_dict,
        readability_after=readability_after_dict,
        semantic_score=semantic_score,
        keywords_preserved=preserved_keywords,
    )

    # Step 8: Determine grade_alignment_status based on delta
    if grade_alignment_delta is not None:
        if grade_alignment_delta <= 1.0:
            grade_alignment_status = "Target level achieved"
        elif grade_alignment_delta <= 3.0:
            grade_alignment_status = "Close to target"
        else:
            grade_alignment_status = "Target level not achieved"
    else:
        grade_alignment_status = "Unknown"

    # Step 9: Generate teacher report (now includes reliability assessment)
    teacher_report, reliability_assessment = generate_teacher_report(
        metadata=differentiation_metadata,
        original_keywords=original_keywords,
        preserved_keywords=preserved_keywords,
        target_grade=target_grade_numeric,
    )

    # Step 10: Build reliability warnings list
    reliability_warnings = reliability_assessment.get("warnings", [])

    # Add warning if grade alignment is poor
    if grade_alignment_delta is not None and grade_alignment_delta > 1.0:
        reliability_warnings.append(
            f"Grade alignment delta {grade_alignment_delta:.1f} exceeds tolerance. "
            f"Target: {target_grade_numeric:.1f}, Achieved: {new_grade:.1f}"
        )

    # Step 11: Compute additional reliability scores if needed
    # (generate_teacher_report computes them, but we also return them separately)
    if semantic_score_was_computed is False:
        reliability_assessment = assess_reliability(
            semantic_score=None,
            keywords_preserved_count=len(preserved_keywords),
            new_grade=new_grade,
            target_grade=target_grade_numeric,
        )
    # Otherwise reliability_assessment from generate_teacher_report is already computed

    return {
        "original_text": text,
        "transformed_text": transformed,
        "original_level": original_level,
        "target_level": target,
        "original_grade": original_grade,
        "new_grade": new_grade,
        "semantic_score": semantic_score if semantic_score_was_computed else None,
        "original_keywords": original_keywords,
        "preserved_keywords": preserved_keywords,
        "differentiation_metadata": differentiation_metadata,
        "teacher_report": teacher_report,
        # Reliability assessment fields
        "semantic_status": reliability_assessment.get("semantic_status"),
        "terminology_status": reliability_assessment.get("terminology_status"),
        "grade_alignment_status": grade_alignment_status,
        "reliability_status": reliability_assessment.get("reliability_status"),
        "reliability_warnings": reliability_warnings,
    }


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


@router.post("/transform", response_model=UnifiedTransformResult)
async def transform(request: TransformRequest):
    """
    Transform text to a target reading level with UNIFIED backward-compatible response.

    ALWAYS returns UnifiedTransformResult with:
    - Backward compatibility fields: original_text, transformed_text, etc.
    - Document/paragraph fields: paragraphs[], document_metrics (if multi-paragraph input)

    Automatically detects whether input contains multiple paragraphs (separated by
    blank lines) and routes to appropriate pipeline:

    **Single Paragraph Mode:**
      - Process via existing transform pipeline
      - Return: transformed_text (string), plus backward-compat fields
      - paragraphs[] field: Array with single paragraph (for frontend consistency)
      - document_metrics: None (not applicable)

    **Multi-Paragraph Mode:**
      - Segment on \\n\\n boundaries
      - For each paragraph: run transform pipeline independently
      - Aggregate document-level metrics
      - Return: transformed_text (all paragraphs joined with \\n\\n), plus
      - paragraphs[] array with per-paragraph metrics
      - document_metrics with averages and reliability

    FRONTEND COMPATIBILITY:
      All responses include transformed_text (string) so old frontend code
      expecting response.transformed_text.replace(...) will not crash.

    Uses Claude if an API key is supplied; otherwise falls back to Ollama.
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

    # STEP 1: Detect paragraph count
    try:
        paragraphs = segment_paragraphs(text)
    except ValueError:
        # If segmentation fails (empty document), fall back to single-paragraph mode
        paragraphs = [text]

    logger.info("Transform endpoint detected %d paragraph(s)", len(paragraphs))

    # STEP 2: Route to appropriate pipeline based on paragraph count
    if len(paragraphs) > 1:
        # Multi-paragraph mode: delegate to document transformation logic
        logger.info("Routing to multi-paragraph document transformation")

        paragraph_results_list: list[dict] = []
        paragraph_transforms_list: list[ParagraphTransformResult] = []
        all_keywords_preserved = set()
        first_original_level = None  # Store from first paragraph for backward compat

        for idx, para in enumerate(paragraphs):
            logger.info("Processing paragraph %d/%d", idx + 1, len(paragraphs))

            try:
                # Run the full transform pipeline on this paragraph
                para_result = await _run_transform_pipeline(para, target, request.api_key)

                # Save original_level from first paragraph (for backward compatibility)
                if idx == 0:
                    first_original_level = para_result["original_level"]

                # Extract metrics for aggregation
                para_metrics = {
                    "original_grade": para_result["original_grade"],
                    "new_grade": para_result["new_grade"],
                    "semantic_score": para_result["semantic_score"],
                    "keywords_preserved_count": len(para_result["preserved_keywords"]),
                }
                paragraph_results_list.append(para_metrics)

                # Collect all preserved keywords
                all_keywords_preserved.update(para_result["preserved_keywords"])

                # Create paragraph-level result
                paragraph_transform = ParagraphTransformResult(
                    original_paragraph=para_result["original_text"],
                    transformed_paragraph=para_result["transformed_text"],
                    original_grade=round(para_result["original_grade"], 2),
                    new_grade=round(para_result["new_grade"], 2),
                    semantic_score=(
                        round(para_result["semantic_score"], 4)
                        if para_result["semantic_score"] is not None
                        else None
                    ),
                    keywords_preserved_count=len(para_result["preserved_keywords"]),
                )
                paragraph_transforms_list.append(paragraph_transform)

            except Exception as e:
                logger.error("Failed to transform paragraph %d: %s", idx + 1, str(e))
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to transform paragraph {idx + 1}: {str(e)}",
                )

        # Compute document-level metrics
        document_metrics_dict = compute_document_metrics(paragraph_results_list)
        document_metrics = DocumentMetrics(
            average_original_grade=document_metrics_dict["average_original_grade"],
            average_new_grade=document_metrics_dict["average_new_grade"],
            average_semantic_score=document_metrics_dict["average_semantic_score"],
            total_keywords_preserved=document_metrics_dict["total_keywords_preserved"],
            document_reliability=document_metrics_dict["document_reliability"],
            paragraphs_processed=document_metrics_dict["paragraphs_processed"],
        )

        # Generate document-level report
        teacher_report = generate_document_report(document_metrics_dict, len(paragraphs))

        logger.info(
            "Document transformation complete: %d paragraphs, avg_grade %.2f → %.2f, reliability=%s",
            len(paragraphs),
            document_metrics.average_original_grade,
            document_metrics.average_new_grade,
            document_metrics.document_reliability,
        )

        # BACKWARD COMPATIBILITY: Join transformed paragraphs with \n\n
        # Validate each paragraph has valid string content
        valid_paragraphs = []
        for p in paragraph_transforms_list:
            if isinstance(p.transformed_paragraph, str) and p.transformed_paragraph.strip():
                valid_paragraphs.append(p.transformed_paragraph)
            else:
                logger.warning("Invalid transformed paragraph detected, using fallback")
                valid_paragraphs.append("Unable to process this paragraph. Please try again.")

        joined_transformed_text = "\n\n".join(valid_paragraphs)

        # Validate final joined text
        if not joined_transformed_text.strip():
            logger.error("Multi-paragraph transform produced empty result")
            joined_transformed_text = "Unable to process transformation. Please try again."

        # DEBUG: Log what we're returning
        logger.info(
            f"Multi-para: first_original_level={first_original_level}, "
            f"paragraphs={len(paragraph_transforms_list)}, "
            f"text_len={len(joined_transformed_text)}"
        )

        # Return UnifiedTransformResult with BOTH formats
        return UnifiedTransformResult(
            # Backward compatibility fields (always present)
            original_text=text,
            transformed_text=joined_transformed_text,
            original_level=first_original_level or "Unknown",
            target_level=target,
            original_grade=document_metrics.average_original_grade,
            new_grade=document_metrics.average_new_grade,
            semantic_score=document_metrics.average_semantic_score,
            original_keywords=[],  # Empty for multi-paragraph
            preserved_keywords=list(all_keywords_preserved),
            teacher_report=teacher_report,
            semantic_status=None,  # Use document reliability instead
            terminology_status=None,
            grade_alignment_status=None,
            reliability_status=document_metrics.document_reliability,
            reliability_warnings=[],
            differentiation_metadata=None,
            # Multi-paragraph fields (new features)
            paragraphs=paragraph_transforms_list,
            document_metrics=document_metrics,
        )

    else:
        # Single-paragraph mode: use existing pipeline (backward compatible)
        logger.info("Routing to single-paragraph transformation (compatibility mode)")

        try:
            result = await _run_transform_pipeline(text, target, request.api_key)
        except Exception as e:
            logger.error(f"Transform pipeline failed: {e}")
            # Return error response with fallback string
            fallback_msg = "Unable to process transformation. Please try again."
            return UnifiedTransformResult(
                original_text=text,
                transformed_text=fallback_msg,
                original_level="Unknown",
                target_level=target,
                original_grade=0.0,
                new_grade=0.0,
                semantic_score=None,
                original_keywords=[],
                preserved_keywords=[],
                teacher_report="Transformation failed. Please check your input and try again.",
                semantic_status="Unavailable",
                terminology_status="Unavailable",
                grade_alignment_status="Unknown",
                reliability_status="Review Recommended",
                reliability_warnings=["Transform pipeline error: " + str(e)],
                differentiation_metadata=None,
                paragraphs=[
                    ParagraphTransformResult(
                        original_paragraph=text,
                        transformed_paragraph=fallback_msg,
                        original_grade=0.0,
                        new_grade=0.0,
                        semantic_score=None,
                        keywords_preserved_count=0,
                    )
                ],
                document_metrics=None,
            )

        # Verify transformed_text is a valid string
        transformed_text = result.get("transformed_text", "")
        if not isinstance(transformed_text, str) or not transformed_text.strip():
            logger.warning("Transform returned invalid transformed_text, using fallback")
            transformed_text = "Unable to process transformation. Please try again."
            result["reliability_warnings"].append("Transformed text validation failed")

        # Return UnifiedTransformResult with BOTH formats for consistency
        return UnifiedTransformResult(
            # Backward compatibility fields (always present)
            original_text=result["original_text"],
            transformed_text=transformed_text,
            original_level=result["original_level"],
            target_level=result["target_level"],
            original_grade=round(result["original_grade"], 2),
            new_grade=round(result["new_grade"], 2),
            semantic_score=(
                round(result["semantic_score"], 4)
                if result["semantic_score"] is not None
                else None
            ),
            original_keywords=result["original_keywords"],
            preserved_keywords=result["preserved_keywords"],
            teacher_report=result["teacher_report"],
            semantic_status=result.get("semantic_status"),
            terminology_status=result.get("terminology_status"),
            grade_alignment_status=result.get("grade_alignment_status"),
            reliability_status=result.get("reliability_status"),
            reliability_warnings=result.get("reliability_warnings", []),
            differentiation_metadata=result["differentiation_metadata"],
            # Single-paragraph fields (also in array format for frontend consistency)
            paragraphs=[
                ParagraphTransformResult(
                    original_paragraph=result["original_text"],
                    transformed_paragraph=transformed_text,
                    original_grade=round(result["original_grade"], 2),
                    new_grade=round(result["new_grade"], 2),
                    semantic_score=(
                        round(result["semantic_score"], 4)
                        if result["semantic_score"] is not None
                        else None
                    ),
                    keywords_preserved_count=len(result["preserved_keywords"]),
                )
            ],
            document_metrics=None,  # Not applicable for single paragraph
        )


@router.post("/export-report", response_class=PlainTextResponse)
async def export_report(request: ExportReportRequest):
    """
    Generate and export a teacher-friendly accessibility report as Markdown.

    Accepts pre-computed transformation pipeline output (from /transform endpoint
    or any transform result) and generates a downloadable Markdown report without
    recomputing the pipeline.

    This is useful for:
    - Exporting reports from previously computed results
    - Batch report generation from stored pipeline outputs
    - Avoiding redundant computation

    Request body should contain:
    - original_text, transformed_text (the texts before/after)
    - original_grade, new_grade (readability scores)
    - semantic_score (optional, float 0-1)
    - preserved_keywords, original_keywords (lists)
    - differentiation_metadata (dict from generate_differentiation_metadata)

    Returns:
        Plain text (Markdown) report with text/markdown MIME type and download headers.

    Example:
        curl -X POST http://localhost:8000/api/export-report \\
          -H "Content-Type: application/json" \\
          -d '{ "original_text": "...", "transformed_text": "...", ... }' \\
          -o report.md
    """
    # Validate required fields
    if not request.original_text or not request.original_text.strip():
        raise HTTPException(
            status_code=422, detail="original_text cannot be empty"
        )
    if not request.transformed_text or not request.transformed_text.strip():
        raise HTTPException(
            status_code=422, detail="transformed_text cannot be empty"
        )
    if not request.differentiation_metadata:
        raise HTTPException(
            status_code=422, detail="differentiation_metadata is required"
        )

    # Generate report from pre-computed metadata (no pipeline computation)
    # Pass target_grade for reliability assessment if available
    teacher_report, reliability_assessment = generate_teacher_report(
        metadata=request.differentiation_metadata,
        original_keywords=request.original_keywords,
        preserved_keywords=request.preserved_keywords,
        target_grade=request.target_grade,
    )

    logger.info(
        "Generated report from pre-computed pipeline output: "
        "grade %.1f→%.1f, semantic=%.3f, keywords=%d, reliability=%s",
        request.original_grade,
        request.new_grade,
        request.semantic_score or 0.0,
        len(request.preserved_keywords),
        reliability_assessment.get("reliability_status", "Unknown"),
    )

    # Return Markdown file with download headers
    return PlainTextResponse(
        content=teacher_report,
        media_type="text/markdown",
        headers={
            "Content-Disposition": 'attachment; filename="accessibility-report.md"'
        },
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


@router.post("/document-transform", response_model=DocumentTransformResult)
async def document_transform(request: DocumentTransformRequest):
    """
    Transform a multi-paragraph document to a target reading level.

    Processes each paragraph independently through the full transform pipeline,
    aggregates results with document-level metrics, and generates a comprehensive
    accessibility report.

    Pipeline:
      1. Segment document into paragraphs (split on \\n\\n)
      2. For each paragraph:
         - Run transform pipeline (same as /transform endpoint)
         - Extract original grade, new grade, semantic score, keywords
      3. Aggregate metrics across all paragraphs
      4. Compute document-level reliability (based on avg semantic score)
      5. Generate document-level accessibility report
      6. Return structured response with per-paragraph + aggregate results

    Returns:
        DocumentTransformResult with paragraphs list, document metrics, and report.
    """
    text = request.text.strip()
    target = request.target_level.lower()

    # Validate target level
    valid_levels = ["elementary", "middle_school", "high_school", "college"]
    if target not in valid_levels:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid target_level. Must be one of: {', '.join(valid_levels)}",
        )

    # Check AI backend availability
    use_claude = _should_use_claude(request.api_key)
    if not use_claude and not await is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="No AI backend available. Start Ollama or provide a Claude API key.",
        )

    # Step 1: Segment document into paragraphs
    try:
        paragraphs = segment_paragraphs(text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    logger.info("Processing %d paragraphs for document transformation", len(paragraphs))

    # Step 2: Process each paragraph through transform pipeline
    paragraph_results_list: list[dict] = []
    paragraph_transforms_list: list[ParagraphTransformResult] = []

    for idx, para in enumerate(paragraphs):
        logger.info("Processing paragraph %d/%d", idx + 1, len(paragraphs))

        try:
            # Run the full transform pipeline on this paragraph
            para_result = await _run_transform_pipeline(para, target, request.api_key)

            # Extract metrics for aggregation
            para_metrics = {
                "original_grade": para_result["original_grade"],
                "new_grade": para_result["new_grade"],
                "semantic_score": para_result["semantic_score"],
                "keywords_preserved_count": len(para_result["preserved_keywords"]),
            }
            paragraph_results_list.append(para_metrics)

            # Create paragraph-level result
            paragraph_transform = ParagraphTransformResult(
                original_paragraph=para_result["original_text"],
                transformed_paragraph=para_result["transformed_text"],
                original_grade=round(para_result["original_grade"], 2),
                new_grade=round(para_result["new_grade"], 2),
                semantic_score=(
                    round(para_result["semantic_score"], 4)
                    if para_result["semantic_score"] is not None
                    else None
                ),
                keywords_preserved_count=len(para_result["preserved_keywords"]),
            )
            paragraph_transforms_list.append(paragraph_transform)

        except Exception as e:
            logger.error("Failed to transform paragraph %d: %s", idx + 1, str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Failed to transform paragraph {idx + 1}: {str(e)}",
            )

    # Step 3: Compute document-level metrics
    document_metrics_dict = compute_document_metrics(paragraph_results_list)
    document_metrics = DocumentMetrics(
        average_original_grade=document_metrics_dict["average_original_grade"],
        average_new_grade=document_metrics_dict["average_new_grade"],
        average_semantic_score=document_metrics_dict["average_semantic_score"],
        total_keywords_preserved=document_metrics_dict["total_keywords_preserved"],
        document_reliability=document_metrics_dict["document_reliability"],
        paragraphs_processed=document_metrics_dict["paragraphs_processed"],
    )

    # Step 4: Generate document-level report
    teacher_report = generate_document_report(document_metrics_dict, len(paragraphs))

    logger.info(
        "Document transformation complete: %d paragraphs, avg_grade %.2f → %.2f, reliability=%s",
        len(paragraphs),
        document_metrics.average_original_grade,
        document_metrics.average_new_grade,
        document_metrics.document_reliability,
    )

    # Step 5: Return structured response
    return DocumentTransformResult(
        paragraphs=paragraph_transforms_list,
        document_metrics=document_metrics,
        teacher_report=teacher_report,
    )


# ═════════════════════════════════════════════════════════════════════════════
# PDF LESSON ADAPTATION ENDPOINT
# ═════════════════════════════════════════════════════════════════════════════


@router.post("/upload-pdf", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    target_level: str = "middle_school",
    api_key: str | None = None,
):
    """
    Upload and adapt a PDF lesson excerpt to a target reading level.

    Pipeline:
      1. Validate PDF file
      2. Extract text from PDF (page-by-page)
      3. Send extracted text into multi-paragraph transform pipeline
      4. Return adapted text + document metrics + teacher report

    Args:
        file: PDF file upload (multipart/form-data)
        target_level: Target reading level (elementary, middle_school, high_school, college)
        api_key: Optional Claude API key

    Returns:
        PDFUploadResponse with extracted text, adapted output, and metrics
    """
    # STEP 1: Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not validate_pdf_file(file.filename):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid file type. Expected PDF, got: {file.filename}",
        )

    # STEP 2: Read PDF bytes
    try:
        pdf_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read PDF file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read PDF file")

    # STEP 3: Extract text from PDF
    logger.info(f"Extracting text from PDF: {file.filename}")
    extraction_result = extract_text_from_pdf(pdf_bytes)

    if not extraction_result.success:
        logger.warning(
            f"PDF extraction failed: {extraction_result.error}"
        )
        return PDFUploadResponse(
            extracted_text="",
            pages_processed=0,
            paragraphs_in_source=0,
            word_count_source=0,
            transformed_text="",
            original_grade=0.0,
            new_grade=0.0,
            error=extraction_result.error or "Unknown PDF extraction error",
        )

    extracted_text = extraction_result.text
    logger.info(
        f"PDF extraction successful: {extraction_result.page_count} pages, "
        f"{extraction_result.paragraph_count} paragraphs, "
        f"{extraction_result.word_count} words"
    )

    # STEP 4: Validate target level
    valid_levels = ["elementary", "middle_school", "high_school", "college"]
    if target_level.lower() not in valid_levels:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid target_level. Must be one of: {', '.join(valid_levels)}",
        )

    # STEP 5: Check backend availability
    use_claude = _should_use_claude(api_key)
    if not use_claude and not await is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="No AI backend available. Start Ollama or provide a Claude API key.",
        )

    # STEP 6: Run transformation pipeline
    try:
        logger.info(
            f"Running transform pipeline on extracted text: "
            f"target={target_level}, use_claude={use_claude}"
        )

        # Reuse existing transform pipeline
        result = await _run_transform_pipeline(
            extracted_text, target_level.lower(), api_key
        )

        logger.info(
            f"Transform pipeline complete: grade {result['original_grade']:.2f} → "
            f"{result['new_grade']:.2f}, semantic={result['semantic_score']}"
        )

    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Transform pipeline failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Text transformation failed: {str(e)}"
        )

    # STEP 7: Validate transformed_text is a valid string
    transformed_text = result.get("transformed_text", "")
    if not isinstance(transformed_text, str) or not transformed_text.strip():
        logger.warning("PDF transform returned invalid transformed_text, using fallback")
        transformed_text = "Unable to process transformation. Please try again."
        if "reliability_warnings" not in result:
            result["reliability_warnings"] = []
        result["reliability_warnings"].append("Transformed text validation failed")

    # STEP 8: Build teacher report with PDF metadata
    teacher_report = result.get("teacher_report", "")

    # Add PDF source section
    pdf_source_section = f"""
## Source Document

**PDF File:** {file.filename}

**Pages Processed:** {extraction_result.page_count}

**Paragraphs Detected:** {extraction_result.paragraph_count}

**Word Count (Original):** {extraction_result.word_count}

---
"""

    teacher_report_with_source = pdf_source_section + teacher_report

    # STEP 9: Return unified response
    return PDFUploadResponse(
        extracted_text=extracted_text,
        pages_processed=extraction_result.page_count,
        paragraphs_in_source=extraction_result.paragraph_count,
        word_count_source=extraction_result.word_count,
        transformed_text=transformed_text,
        original_grade=round(result["original_grade"], 2),
        new_grade=round(result["new_grade"], 2),
        semantic_score=(
            round(result["semantic_score"], 4)
            if result["semantic_score"] is not None
            else None
        ),
        reliability_status=result.get("reliability_status"),
        reliability_warnings=result.get("reliability_warnings", []),
        document_metrics=None,  # Will be set if multi-paragraph
        paragraphs=None,  # Will be set if multi-paragraph
        teacher_report=teacher_report_with_source,
        error=None,
    )
