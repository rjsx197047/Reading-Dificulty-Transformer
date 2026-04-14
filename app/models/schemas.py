from pydantic import BaseModel, Field


class TextInput(BaseModel):
    """Input schema for text analysis."""

    text: str = Field(..., min_length=1, description="The text to analyze for reading difficulty")


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
        None, description="AI-powered qualitative analysis from Ollama (null if unavailable)"
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


class TransformResult(BaseModel):
    """Result of transforming text to a target reading level."""

    original_text: str
    transformed_text: str
    original_level: str
    target_level: str
    original_grade: float
    new_grade: float


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


class SimplifyResult(BaseModel):
    """Structured result from the simplification pipeline."""

    original_level: float = Field(..., description="Estimated grade level of the original text")
    target_level: float = Field(..., description="Requested target grade level")
    final_level: float = Field(..., description="Achieved grade level after rewriting")
    meaning_score: float | None = Field(
        None, description="Cosine similarity score (0–1) measuring meaning preservation"
    )
    simplified_text: str = Field(..., description="The rewritten, simplified text")
    keywords_preserved: list[str] = Field(
        default_factory=list, description="Keywords that were locked during rewriting"
    )
    original_readability: ReadabilityDetectionResult | None = Field(
        None,
        description="Readability scores for the original text (FK, Coleman-Liau, SMOG, ARI, avg)",
    )
    final_readability: ReadabilityDetectionResult | None = Field(
        None,
        description="Readability scores for the simplified text (FK, Coleman-Liau, SMOG, ARI, avg)",
    )


class WorksheetRequest(BaseModel):
    """Request to generate three differentiated versions of a worksheet."""

    worksheet_text: str = Field(
        ..., min_length=1, description="The teacher-provided worksheet text to differentiate"
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
