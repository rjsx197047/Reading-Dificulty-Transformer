from pydantic import BaseModel, Field


class TextInput(BaseModel):
    """Input schema for text analysis."""

    text: str = Field(..., min_length=1, description="The text to analyze for reading difficulty")
    api_key: str | None = Field(
        None,
        description="Optional Claude API key (sk-ant-...). When provided, uses Claude for AI tasks instead of local Ollama.",
    )


class ReadabilityScores(BaseModel):
    """Traditional readability formula scores."""

    flesch_reading_ease: float = Field(..., description="Flesch Reading Ease (0-100, higher=easier)")
    flesch_kincaid_grade: float = Field(..., description="Flesch-Kincaid Grade Level")
    gunning_fog: float = Field(..., description="Gunning Fog Index")
    smog_index: float = Field(..., description="SMOG Index")
    coleman_liau: float = Field(..., description="Coleman-Liau Index")
    ari: float = Field(..., description="Automated Readability Index")
    dale_chall: float = Field(..., description="Dale-Chall Readability Score")


class TextStatistics(BaseModel):
    """Raw text statistics used for analysis."""

    word_count: int
    sentence_count: int
    syllable_count: int
    avg_words_per_sentence: float
    avg_syllables_per_word: float
    complex_word_count: int
    complex_word_percentage: float
    character_count: int
    paragraph_count: int


class DifficultyLevel(BaseModel):
    """Overall difficulty classification."""

    level: str = Field(
        ..., description="Reading level: Elementary, Middle School, High School, College, Graduate"
    )
    grade_range: str = Field(..., description="Approximate US grade range (e.g., '6-8')")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    description: str = Field(..., description="Human-friendly description of the difficulty")


class AnalysisResult(BaseModel):
    """Complete analysis result combining all modules."""

    difficulty: DifficultyLevel
    scores: ReadabilityScores
    statistics: TextStatistics
    ai_analysis: str | None = Field(
        None, description="AI-powered qualitative analysis (null if unavailable)"
    )
    text_type: str | None = Field(
        None,
        description="AI-detected text type/genre (e.g. 'News Article', 'Play', 'Novel Excerpt')",
    )
    ai_backend: str = Field(
        "none", description="Which AI backend was used: 'claude', 'ollama', or 'none'"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Suggestions to simplify the text"
    )


class TransformRequest(BaseModel):
    """Request to transform text to a target reading level."""

    text: str = Field(..., min_length=1, description="The text to transform")
    target_level: str = Field(
        ..., description="Target level: elementary, middle_school, high_school, college"
    )
    api_key: str | None = Field(
        None, description="Optional Claude API key. When provided, uses Claude instead of Ollama."
    )


class TransformResult(BaseModel):
    """Result of transforming text to a target reading level."""

    original_text: str
    transformed_text: str
    original_level: str
    target_level: str
    original_grade: float
    new_grade: float

    # Enhanced analytics fields
    semantic_score: float | None = Field(
        None, description="Semantic similarity (0-1) between original and transformed text"
    )
    original_keywords: list[str] = Field(
        default_factory=list, description="Keywords extracted from original text"
    )
    preserved_keywords: list[str] = Field(
        default_factory=list, description="Keywords that were preserved in transformed text"
    )
    teacher_report: str | None = Field(
        None, description="Markdown-formatted accessibility report for teachers"
    )

    # Reliability assessment fields
    semantic_status: str | None = Field(
        None, description="Semantic preservation status: 'High preservation', 'Moderate preservation', 'Low preservation', or 'Unavailable'"
    )
    terminology_status: str | None = Field(
        None, description="Keyword retention status: 'Strong terminology retention', 'Moderate terminology retention', or 'Terminology loss risk'"
    )
    grade_alignment_status: str | None = Field(
        None, description="Grade targeting status: 'Target level achieved' or 'Target level not achieved'"
    )
    reliability_status: str | None = Field(
        None, description="Overall reliability for classroom use: 'High', 'Moderate', or 'Review Recommended'"
    )
    reliability_warnings: list[str] = Field(
        default_factory=list, description="List of warnings if reliability metrics fail thresholds"
    )

    # Legacy field
    differentiation_metadata: dict | None = Field(
        None, description="Teacher-friendly metadata explaining changes"
    )


class ExportReportRequest(BaseModel):
    """Request to generate and export a teacher report from pre-computed pipeline output."""

    original_text: str = Field(..., description="Original text before transformation")
    transformed_text: str = Field(..., description="Transformed/simplified text")
    original_grade: float = Field(..., description="Original text grade level")
    new_grade: float = Field(..., description="Transformed text grade level")
    semantic_score: float | None = Field(
        None, description="Semantic similarity score (0-1)"
    )
    preserved_keywords: list[str] = Field(
        default_factory=list, description="Keywords preserved in transformation"
    )
    original_keywords: list[str] = Field(
        default_factory=list, description="Keywords extracted from original"
    )
    differentiation_metadata: dict = Field(
        ..., description="Differentiation metadata dict from generate_differentiation_metadata()"
    )
    target_grade: float | None = Field(
        None, description="Target grade for reliability assessment (optional)"
    )


# ---------------------------------------------------------------------------
# Phase 1 / 2 — Enhanced simplification pipeline
# ---------------------------------------------------------------------------


class ReadabilityDetectionResult(BaseModel):
    """
    Focused readability snapshot returned by core/readability.detect_readability().
    Included in SimplifyResult to bracket the pipeline with before/after grades.
    """

    flesch_kincaid: float = Field(..., description="Flesch-Kincaid Grade Level")
    coleman_liau: float = Field(..., description="Coleman-Liau Index")
    smog: float = Field(..., description="SMOG Index")
    ari: float = Field(..., description="Automated Readability Index")
    average_grade: float = Field(
        ..., description="Mean of the four formula scores — primary comparable grade"
    )


class SimplifyRequest(BaseModel):
    """Request for the grade-level simplification pipeline."""

    input_text: str = Field(..., min_length=1, description="The text to simplify")
    target_grade: float = Field(
        ..., ge=1.0, le=16.0, description="Target grade level (1–16, e.g. 5.0 for Grade 5)"
    )
    chunking: bool = Field(
        False, description="Dyslexia Support Mode: split long sentences into short chunks"
    )
    preserve_keywords: bool = Field(
        False, description="Lock key nouns and STEM vocabulary during rewriting"
    )
    mode: str = Field(
        "standard",
        description="Rewrite mode: 'standard' or 'esl' (simpler grammar for non-native speakers)",
    )
    instruction_mode: bool = Field(
        False,
        description="Homework Instruction Mode: convert instructions into numbered steps",
    )
    dyslexia_mode: bool = Field(
        False,
        description="Apply dyslexia-friendly formatting (short paragraphs, extra spacing)",
    )
    api_key: str | None = Field(
        None,
        description="Optional Claude API key. When provided, uses Claude instead of Ollama.",
    )


class SimplifyResult(BaseModel):
    """Structured result from the simplification pipeline."""

    original_text: str = Field(..., description="The original input text")
    simplified_text: str = Field(..., description="The rewritten, simplified text")
    original_level: float = Field(..., description="Estimated grade level of the original text")
    target_level: float = Field(..., description="Requested target grade level")
    final_level: float = Field(..., description="Achieved grade level after rewriting")
    readability_before: ReadabilityDetectionResult | None = Field(
        None,
        description="Readability scores for the original text (FK, Coleman-Liau, SMOG, ARI, avg)",
    )
    readability_after: ReadabilityDetectionResult | None = Field(
        None,
        description="Readability scores for the simplified text (FK, Coleman-Liau, SMOG, ARI, avg)",
    )
    semantic_preservation_score: float | None = Field(
        None,
        description="Cosine similarity (0–1) between original and simplified embeddings",
    )
    keywords_preserved: list[str] = Field(
        default_factory=list, description="Keywords that were locked during rewriting"
    )
    # --- Backward-compatible aliases (existing UI/clients) ---
    meaning_score: float | None = Field(
        None, description="Alias for semantic_preservation_score (backward compat)"
    )
    original_readability: ReadabilityDetectionResult | None = Field(
        None, description="Alias for readability_before (backward compat)"
    )
    final_readability: ReadabilityDetectionResult | None = Field(
        None, description="Alias for readability_after (backward compat)"
    )


class WorksheetRequest(BaseModel):
    """Request to generate three differentiated versions of a worksheet."""

    worksheet_text: str = Field(
        ..., min_length=1, description="The teacher-provided worksheet text to differentiate"
    )
    api_key: str | None = Field(
        None, description="Optional Claude API key. When provided, uses Claude instead of Ollama."
    )


class WorksheetResult(BaseModel):
    """Three differentiated versions of the worksheet."""

    advanced_version: str = Field(..., description="High School / College level version")
    standard_version: str = Field(..., description="Middle School level version")
    simplified_version: str = Field(..., description="Elementary level version")
    advanced_grade: float
    standard_grade: float
    simplified_grade: float


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    ollama_available: bool
    semantic_scoring_available: bool = False


# ---------------------------------------------------------------------------
# Document-level transformation — multi-paragraph support
# ---------------------------------------------------------------------------


class ParagraphTransformResult(BaseModel):
    """Result for a single paragraph transformation."""

    original_paragraph: str = Field(..., description="Original paragraph text")
    transformed_paragraph: str = Field(..., description="Transformed/simplified paragraph text")
    original_grade: float = Field(..., description="Original paragraph grade level")
    new_grade: float = Field(..., description="Transformed paragraph grade level")
    semantic_score: float | None = Field(
        None, description="Semantic similarity (0-1) for this paragraph"
    )
    keywords_preserved_count: int = Field(
        ..., description="Number of keywords preserved in this paragraph"
    )


class DocumentMetrics(BaseModel):
    """Aggregate metrics across all paragraphs in a document."""

    average_original_grade: float = Field(
        ..., description="Average grade level across original paragraphs"
    )
    average_new_grade: float = Field(
        ..., description="Average grade level across transformed paragraphs"
    )
    average_semantic_score: float | None = Field(
        None, description="Average semantic preservation score across paragraphs"
    )
    total_keywords_preserved: int = Field(
        ..., description="Total keywords preserved across all paragraphs"
    )
    document_reliability: str = Field(
        ...,
        description="Document-level reliability status: 'High', 'Moderate', or 'Review Recommended'",
    )
    paragraphs_processed: int = Field(..., description="Number of paragraphs processed")


class DocumentTransformRequest(BaseModel):
    """Request to transform multi-paragraph document to a target reading level."""

    text: str = Field(..., min_length=1, description="The multi-paragraph document to transform")
    target_level: str = Field(
        ...,
        description="Target level: elementary, middle_school, high_school, college",
    )
    api_key: str | None = Field(
        None,
        description="Optional Claude API key. When provided, uses Claude instead of Ollama.",
    )


class DocumentTransformResult(BaseModel):
    """Complete result of transforming a multi-paragraph document."""

    paragraphs: list[ParagraphTransformResult] = Field(
        ..., description="Per-paragraph transformation results"
    )
    document_metrics: DocumentMetrics = Field(
        ..., description="Aggregate metrics across all paragraphs"
    )
    teacher_report: str | None = Field(
        None,
        description="Markdown-formatted document-level accessibility report for teachers",
    )


# ---------------------------------------------------------------------------
# Unified Transform Response (Backend/Frontend Contract)
# ---------------------------------------------------------------------------


class UnifiedTransformResult(BaseModel):
    """
    Unified response from /api/transform endpoint.

    Always includes backward compatibility fields (original_text, transformed_text, etc.)
    PLUS document/paragraph-level fields when applicable.

    This ensures:
    - Old frontend code expecting string fields doesn't break
    - New frontend code can access paragraph and document metrics
    - Single-paragraph and multi-paragraph modes use same response structure
    """

    # ─────────────────────────────────────────────────────────────────────
    # BACKWARD COMPATIBILITY FIELDS (Always present, never null)
    # ─────────────────────────────────────────────────────────────────────

    original_text: str = Field(
        ..., description="Original input text (single or joined from paragraphs)"
    )
    transformed_text: str = Field(
        ...,
        description="Transformed output text (single paragraph or joined from all paragraphs with \\n\\n)",
    )
    original_level: str = Field(
        ...,
        description="Difficulty level of original text: Elementary, Middle School, High School, College, Graduate",
    )
    target_level: str = Field(
        ..., description="Target level requested: elementary, middle_school, high_school, college"
    )
    original_grade: float = Field(
        ..., description="Original text grade level (single paragraph or average)"
    )
    new_grade: float = Field(
        ..., description="Transformed text grade level (single paragraph or average)"
    )
    semantic_score: float | None = Field(
        None, description="Semantic preservation score 0-1 (single paragraph or average)"
    )
    original_keywords: list[str] = Field(
        default_factory=list, description="Keywords extracted from original text"
    )
    preserved_keywords: list[str] = Field(
        default_factory=list, description="Keywords preserved in transformed text"
    )
    teacher_report: str | None = Field(
        None,
        description="Markdown-formatted accessibility report (single or document-level)",
    )

    # Reliability assessment fields (single paragraph or document-level)
    semantic_status: str | None = Field(
        None, description="Semantic preservation status"
    )
    terminology_status: str | None = Field(
        None, description="Keyword retention status"
    )
    grade_alignment_status: str | None = Field(
        None, description="Grade targeting status"
    )
    reliability_status: str | None = Field(
        None, description="Overall reliability for classroom use"
    )
    reliability_warnings: list[str] = Field(
        default_factory=list, description="Warnings if metrics below thresholds"
    )

    differentiation_metadata: dict | None = Field(
        None, description="Teacher-friendly metadata explaining changes"
    )

    # ─────────────────────────────────────────────────────────────────────
    # MULTI-PARAGRAPH FIELDS (Optional, present only if input had paragraphs)
    # ─────────────────────────────────────────────────────────────────────

    paragraphs: list[ParagraphTransformResult] | None = Field(
        None,
        description="Per-paragraph results (only present if input had multiple paragraphs)",
    )
    document_metrics: DocumentMetrics | None = Field(
        None,
        description="Document-level aggregate metrics (only present if input had multiple paragraphs)",
    )


# ---------------------------------------------------------------------------
# PDF Upload Response Schemas
# ---------------------------------------------------------------------------


class PDFUploadResponse(BaseModel):
    """
    Response from PDF upload and adaptation endpoint.

    Contains extracted text from PDF, readability metrics, and adapted output
    suitable for classroom use.
    """

    # PDF extraction metadata
    extracted_text: str = Field(
        ...,
        description="Full text extracted from PDF",
    )
    pages_processed: int = Field(
        ..., description="Number of pages in the PDF"
    )
    paragraphs_in_source: int = Field(
        ..., description="Number of paragraphs detected in extracted text"
    )
    word_count_source: int = Field(
        ..., description="Word count of extracted PDF text"
    )

    # Transformation results
    transformed_text: str = Field(
        ...,
        description="Text adapted to target reading level",
    )
    original_grade: float = Field(
        ..., description="Original text grade level"
    )
    new_grade: float = Field(
        ..., description="Adapted text grade level"
    )
    semantic_score: float | None = Field(
        None, description="Semantic preservation score (0-1)"
    )

    # Reliability & metrics
    reliability_status: str | None = Field(
        None,
        description="Overall reliability: 'High', 'Moderate', or 'Review Recommended'",
    )
    reliability_warnings: list[str] = Field(
        default_factory=list, description="Warnings if any metrics below thresholds"
    )

    # Document-level metrics
    document_metrics: dict | None = Field(
        None,
        description="Aggregate metrics if PDF had multiple paragraphs",
    )
    paragraphs: list[dict] | None = Field(
        None,
        description="Per-paragraph transformation results",
    )

    # Teacher report
    teacher_report: str | None = Field(
        None,
        description="Markdown-formatted accessibility report for teachers",
    )

    # Error handling
    error: str | None = Field(
        None,
        description="Error message if extraction or processing failed",
    )


class PDFLessonAdaptationRequest(BaseModel):
    """
    Request to adapt a PDF lesson.

    Note: file is handled by FastAPI's UploadFile, not included in this schema.
    """

    target_level: str = Field(
        "middle_school",
        description="Target reading level: elementary, middle_school, high_school, college",
    )
    api_key: str | None = Field(
        None,
        description="Optional Claude API key for AI-powered analysis",
    )
