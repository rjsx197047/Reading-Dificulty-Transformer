"""
Differentiation Metadata Generator Module

This module generates structured, teacher-friendly metadata explaining how text
changes during simplification. Teachers use this information to assess whether
simplified texts are appropriate for differentiated instruction in their classrooms.

The metadata explains:
- How much the reading difficulty decreased (grade reduction)
- How sentences shortened (improved scanability)
- How vocabulary simplified (reduced cognitive load)
- How meaning was preserved (semantic preservation)
- Which specialized terms were protected (domain knowledge retention)

All metrics are quantitative for precise assessment, with a narrative summary
for quick interpretation.
"""

from typing import TypedDict

import nltk

# Ensure required NLTK data is available
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")


class DifferentiationMetadataResult(TypedDict):
    """Return type for generate_differentiation_metadata function."""

    grade_reduction: float
    sentence_count_before: int
    sentence_count_after: int
    avg_sentence_length_before: float
    avg_sentence_length_after: float
    word_count_before: int
    word_count_after: int
    avg_word_length_before: float
    avg_word_length_after: float
    semantic_preservation_score: float
    keywords_preserved_count: int
    accessibility_summary: str


def generate_differentiation_metadata(
    original_text: str,
    simplified_text: str,
    readability_before: dict,
    readability_after: dict,
    semantic_score: float,
    keywords_preserved: list,
) -> DifferentiationMetadataResult:
    """
    Generate teacher-friendly metadata explaining text changes during simplification.

    This function computes quantitative metrics about how text was simplified and
    generates a narrative summary suitable for teachers deciding whether to use the
    simplified version in their classrooms. The metadata focuses on accessibility
    improvements (grade reduction, sentence shortening, vocabulary simplification)
    while emphasizing preservation of meaning and key terminology.

    Args:
        original_text (str): The original, unmodified text.
        simplified_text (str): The simplified version of the text.
        readability_before (dict): Readability metrics for original text.
            Must include "average_grade" key with numeric value.
        readability_after (dict): Readability metrics for simplified text.
            Must include "average_grade" key with numeric value.
        semantic_score (float): Semantic preservation score from semantic_preservation_score()
            function, range [0.0, 1.0] where 1.0 = perfect preservation.
            Must be a valid float in the range.
        keywords_preserved (list): List of specialized terms locked during rewriting
            (from preserve_keywords=True in /simplify). Can be empty list.

    Returns:
        DifferentiationMetadataResult: Dictionary with 12 keys:
            - grade_reduction (float): Absolute grade level decrease
            - sentence_count_before (int): Number of sentences in original
            - sentence_count_after (int): Number of sentences in simplified
            - avg_sentence_length_before (float): Avg words per sentence (original)
            - avg_sentence_length_after (float): Avg words per sentence (simplified)
            - word_count_before (int): Total words in original
            - word_count_after (int): Total words in simplified
            - avg_word_length_before (float): Avg chars per word (original)
            - avg_word_length_after (float): Avg chars per word (simplified)
            - semantic_preservation_score (float): Meaning retention (0-1)
            - keywords_preserved_count (int): Number of protected terms
            - accessibility_summary (str): Narrative explanation for teachers

    Raises:
        ValueError: If readability dicts lack "average_grade" key,
            if grades are non-numeric, if semantic_score is invalid,
            or if texts are empty.

    Example:
        >>> metadata = generate_differentiation_metadata(
        ...     original_text="Complex academic passage...",
        ...     simplified_text="Simpler version...",
        ...     readability_before={"average_grade": 10.5},
        ...     readability_after={"average_grade": 5.2},
        ...     semantic_score=0.87,
        ...     keywords_preserved=["photosynthesis", "ATP", "respiration"]
        ... )
        >>> print(metadata["grade_reduction"])
        5.3
        >>> print(metadata["accessibility_summary"])
        "This rewrite reduced reading difficulty by 5.3 grade levels while..."
    """
    # ─────────────────────────────────────────────────────────────────────
    # Input Validation
    # ─────────────────────────────────────────────────────────────────────
    if not original_text or not original_text.strip():
        raise ValueError("original_text must be non-empty")
    if not simplified_text or not simplified_text.strip():
        raise ValueError("simplified_text must be non-empty")

    if "average_grade" not in readability_before:
        raise ValueError(
            "readability_before must include 'average_grade' key"
        )
    if "average_grade" not in readability_after:
        raise ValueError(
            "readability_after must include 'average_grade' key"
        )

    grade_before = readability_before["average_grade"]
    grade_after = readability_after["average_grade"]

    if not isinstance(grade_before, (int, float)) or not isinstance(
        grade_after, (int, float)
    ):
        raise ValueError("average_grade values must be numeric")

    if not isinstance(semantic_score, (int, float)):
        raise ValueError("semantic_score must be numeric")
    if not (0.0 <= semantic_score <= 1.0):
        raise ValueError("semantic_score must be between 0.0 and 1.0")

    if not isinstance(keywords_preserved, list):
        raise ValueError("keywords_preserved must be a list")

    # ─────────────────────────────────────────────────────────────────────
    # 1. Grade Reduction
    # ─────────────────────────────────────────────────────────────────────
    grade_reduction = round(grade_before - grade_after, 1)

    # ─────────────────────────────────────────────────────────────────────
    # 2. Sentence Statistics
    # ─────────────────────────────────────────────────────────────────────
    (
        sentence_count_before,
        sentence_count_after,
        avg_sentence_length_before,
        avg_sentence_length_after,
    ) = _compute_sentence_statistics(original_text, simplified_text)

    # ─────────────────────────────────────────────────────────────────────
    # 3. Word Statistics
    # ─────────────────────────────────────────────────────────────────────
    (
        word_count_before,
        word_count_after,
        avg_word_length_before,
        avg_word_length_after,
    ) = _compute_word_statistics(original_text, simplified_text)

    # ─────────────────────────────────────────────────────────────────────
    # 4. Semantic Preservation
    # ─────────────────────────────────────────────────────────────────────
    semantic_preservation = round(semantic_score, 4)

    # ─────────────────────────────────────────────────────────────────────
    # 5. Keywords Preserved Count
    # ─────────────────────────────────────────────────────────────────────
    keywords_preserved_count = len(keywords_preserved)

    # ─────────────────────────────────────────────────────────────────────
    # 6. Accessibility Summary
    # ─────────────────────────────────────────────────────────────────────
    accessibility_summary = _build_accessibility_summary(
        grade_reduction=grade_reduction,
        sentence_count_before=sentence_count_before,
        sentence_count_after=sentence_count_after,
        avg_sentence_length_before=avg_sentence_length_before,
        avg_sentence_length_after=avg_sentence_length_after,
        avg_word_length_before=avg_word_length_before,
        avg_word_length_after=avg_word_length_after,
        semantic_preservation=semantic_preservation,
        keywords_preserved_count=keywords_preserved_count,
    )

    return {
        "grade_reduction": grade_reduction,
        "sentence_count_before": sentence_count_before,
        "sentence_count_after": sentence_count_after,
        "avg_sentence_length_before": round(avg_sentence_length_before, 2),
        "avg_sentence_length_after": round(avg_sentence_length_after, 2),
        "word_count_before": word_count_before,
        "word_count_after": word_count_after,
        "avg_word_length_before": round(avg_word_length_before, 2),
        "avg_word_length_after": round(avg_word_length_after, 2),
        "semantic_preservation_score": semantic_preservation,
        "keywords_preserved_count": keywords_preserved_count,
        "accessibility_summary": accessibility_summary,
    }


# ─────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────


def _compute_sentence_statistics(
    original_text: str, simplified_text: str
) -> tuple[int, int, float, float]:
    """
    Compute sentence count and average sentence length before and after.

    Uses NLTK sentence tokenization to split text at sentence boundaries,
    then calculates average words per sentence for both versions.

    Args:
        original_text (str): Original text before simplification
        simplified_text (str): Simplified text after simplification

    Returns:
        tuple: (count_before, count_after, avg_len_before, avg_len_after)
            - count_before (int): Number of sentences in original
            - count_after (int): Number of sentences in simplified
            - avg_len_before (float): Average words per sentence (original)
            - avg_len_after (float): Average words per sentence (simplified)
    """
    # Tokenize into sentences
    sentences_before = nltk.sent_tokenize(original_text)
    sentences_after = nltk.sent_tokenize(simplified_text)

    sentence_count_before = len(sentences_before)
    sentence_count_after = len(sentences_after)

    # Count total words
    words_before = original_text.split()
    words_after = simplified_text.split()

    total_words_before = len(words_before)
    total_words_after = len(words_after)

    # Calculate averages (with edge case handling)
    avg_sentence_length_before = (
        total_words_before / sentence_count_before if sentence_count_before > 0 else 0.0
    )
    avg_sentence_length_after = (
        total_words_after / sentence_count_after if sentence_count_after > 0 else 0.0
    )

    return (
        sentence_count_before,
        sentence_count_after,
        avg_sentence_length_before,
        avg_sentence_length_after,
    )


def _compute_word_statistics(
    original_text: str, simplified_text: str
) -> tuple[int, int, float, float]:
    """
    Compute word count and average word length before and after.

    Splits text into words using whitespace, measures character count per word
    as a proxy for vocabulary complexity.

    Args:
        original_text (str): Original text before simplification
        simplified_text (str): Simplified text after simplification

    Returns:
        tuple: (count_before, count_after, avg_len_before, avg_len_after)
            - count_before (int): Number of words in original
            - count_after (int): Number of words in simplified
            - avg_len_before (float): Average character length per word (original)
            - avg_len_after (float): Average character length per word (simplified)
    """
    # Split into words
    words_before = original_text.lower().split()
    words_after = simplified_text.lower().split()

    word_count_before = len(words_before)
    word_count_after = len(words_after)

    # Calculate average word lengths (with edge case handling)
    if word_count_before > 0:
        avg_word_length_before = sum(len(w) for w in words_before) / word_count_before
    else:
        avg_word_length_before = 0.0

    if word_count_after > 0:
        avg_word_length_after = sum(len(w) for w in words_after) / word_count_after
    else:
        avg_word_length_after = 0.0

    return (
        word_count_before,
        word_count_after,
        avg_word_length_before,
        avg_word_length_after,
    )


def _build_accessibility_summary(
    grade_reduction: float,
    sentence_count_before: int,
    sentence_count_after: int,
    avg_sentence_length_before: float,
    avg_sentence_length_after: float,
    avg_word_length_before: float,
    avg_word_length_after: float,
    semantic_preservation: float,
    keywords_preserved_count: int,
) -> str:
    """
    Generate a narrative accessibility summary for teachers.

    Creates a dynamic, context-aware explanation of how the text was simplified
    by analyzing the magnitude of changes in grade level, sentence structure,
    vocabulary, and semantic preservation.

    Args:
        grade_reduction (float): Grade levels reduced (e.g., 5.3)
        sentence_count_before (int): Original sentence count
        sentence_count_after (int): Simplified sentence count
        avg_sentence_length_before (float): Original avg words per sentence
        avg_sentence_length_after (float): Simplified avg words per sentence
        avg_word_length_before (float): Original avg chars per word
        avg_word_length_after (float): Simplified avg chars per word
        semantic_preservation (float): Meaning preservation (0-1)
        keywords_preserved_count (int): Number of protected terms

    Returns:
        str: Multi-sentence narrative summary suitable for teacher review
    """
    summary_parts = []

    # ─────────────────────────────────────────────────────────────────────
    # Part 1: Grade reduction statement
    # ─────────────────────────────────────────────────────────────────────
    if grade_reduction > 0.1:
        summary_parts.append(
            f"This rewrite reduced reading difficulty by {grade_reduction} grade levels."
        )
    elif grade_reduction > -0.1:
        summary_parts.append("This rewrite maintained approximately the same reading level.")
    else:
        summary_parts.append(
            f"Note: Reading difficulty increased by {abs(grade_reduction)} grade levels."
        )

    # ─────────────────────────────────────────────────────────────────────
    # Part 2: Sentence impact statement
    # ─────────────────────────────────────────────────────────────────────
    sentence_reduction_pct = (
        100 * (avg_sentence_length_before - avg_sentence_length_after) / avg_sentence_length_before
        if avg_sentence_length_before > 0
        else 0
    )

    if sentence_count_after > sentence_count_before:
        summary_parts.append(
            f"Sentences were broken into {sentence_count_after - sentence_count_before} additional "
            f"chunks (from {sentence_count_before} to {sentence_count_after}), improving scanability."
        )
    elif sentence_reduction_pct > 30:
        summary_parts.append(
            f"Sentences were substantially shortened by {sentence_reduction_pct:.0f}% "
            f"(avg {avg_sentence_length_before:.1f} → {avg_sentence_length_after:.1f} words), "
            f"making text easier to process."
        )
    elif sentence_reduction_pct > 10:
        summary_parts.append(
            f"Sentences were moderately shortened by {sentence_reduction_pct:.0f}% "
            f"(avg {avg_sentence_length_before:.1f} → {avg_sentence_length_after:.1f} words)."
        )
    else:
        summary_parts.append(
            f"Sentence structure remained relatively stable at approximately "
            f"{avg_sentence_length_before:.1f}-word average length."
        )

    # ─────────────────────────────────────────────────────────────────────
    # Part 3: Vocabulary simplification statement
    # ─────────────────────────────────────────────────────────────────────
    vocab_reduction_pct = (
        100 * (avg_word_length_before - avg_word_length_after) / avg_word_length_before
        if avg_word_length_before > 0
        else 0
    )

    if vocab_reduction_pct > 20:
        summary_parts.append(
            f"Vocabulary was significantly simplified by {vocab_reduction_pct:.0f}% "
            f"(avg {avg_word_length_before:.1f} → {avg_word_length_after:.1f} chars/word), "
            f"reducing cognitive load."
        )
    elif vocab_reduction_pct > 5:
        summary_parts.append(
            f"Vocabulary was moderately simplified by {vocab_reduction_pct:.0f}% "
            f"(avg {avg_word_length_before:.1f} → {avg_word_length_after:.1f} chars/word)."
        )
    else:
        summary_parts.append(
            f"Vocabulary complexity remained relatively unchanged at approximately "
            f"{avg_word_length_before:.1f} characters per word average."
        )

    # ─────────────────────────────────────────────────────────────────────
    # Part 4: Semantic preservation statement
    # ─────────────────────────────────────────────────────────────────────
    semantic_pct = semantic_preservation * 100
    if semantic_preservation >= 0.85:
        summary_parts.append(
            f"Semantic meaning was excellently preserved at {semantic_pct:.0f}%, "
            f"ensuring core concepts remain intact."
        )
    elif semantic_preservation >= 0.70:
        summary_parts.append(
            f"Semantic meaning was well preserved at {semantic_pct:.0f}%, "
            f"with most key concepts retained."
        )
    else:
        summary_parts.append(
            f"Note: Semantic preservation was {semantic_pct:.0f}%; "
            f"some simplification of concepts occurred."
        )

    # ─────────────────────────────────────────────────────────────────────
    # Part 5: Keyword preservation statement
    # ─────────────────────────────────────────────────────────────────────
    if keywords_preserved_count > 0:
        summary_parts.append(
            f"{keywords_preserved_count} specialized term{'s' if keywords_preserved_count != 1 else ''} "
            f"{'were' if keywords_preserved_count != 1 else 'was'} protected "
            f"to maintain domain-specific vocabulary."
        )

    # ─────────────────────────────────────────────────────────────────────
    # Combine parts into single summary
    # ─────────────────────────────────────────────────────────────────────
    full_summary = " ".join(summary_parts)

    return full_summary
