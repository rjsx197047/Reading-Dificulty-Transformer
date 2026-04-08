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


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    ollama_available: bool
