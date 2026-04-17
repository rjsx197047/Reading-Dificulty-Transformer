"""
Instructional Suitability Scoring Module

This module evaluates whether simplified text output is appropriate for
classroom accessibility use. It combines multiple metrics into a unified
instructional suitability score (0.0–1.0) that teachers can use to assess
whether simplified text meets their classroom needs.

The scoring framework evaluates:
- Grade accuracy: How closely the simplified text matches the target grade level
- Semantic preservation: Whether important meaning and concepts are retained
- Sentence reduction: How much shorter the sentences became
- Vocabulary simplification: How much simpler the word choices are

All scores are normalized to [0, 1] where 1.0 represents ideal classroom
accessibility and 0.0 represents poor suitability.
"""

from typing import TypedDict

import nltk

# Ensure required NLTK data is available
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")


class InstructionalSuitabilityResult(TypedDict):
    """Return type for instructional_suitability_score function."""

    grade_accuracy_score: float
    semantic_preservation_score: float
    sentence_length_reduction_score: float
    vocabulary_simplification_score: float
    instructional_suitability_score: float
    diagnostic: dict


def instructional_suitability_score(
    original_text: str,
    simplified_text: str,
    readability_before: dict,
    readability_after: dict,
    target_grade: float,
    semantic_score: float | None,
) -> InstructionalSuitabilityResult:
    """
    Compute instructional suitability metrics for simplified text.

    This function evaluates whether simplified text is appropriate for
    classroom use by scoring four key dimensions: grade accuracy, semantic
    preservation, sentence reduction, and vocabulary simplification. Each
    metric is normalized to [0, 1], then combined into a weighted composite
    score.

    Args:
        original_text (str): The original, unmodified text.
        simplified_text (str): The simplified version of the text.
        readability_before (dict): Readability metrics for original text.
            Must include "average_grade" key with numeric value.
        readability_after (dict): Readability metrics for simplified text.
            Must include "average_grade" key with numeric value.
        target_grade (float): Target grade level (e.g., 5.0 for grade 5).
        semantic_score (float | None): Semantic preservation score from
            `semantic_preservation_score()` (0.0–1.0), or None if unavailable.
            If None, defaults to 0.5 (neutral score).

    Returns:
        InstructionalSuitabilityResult: Dictionary with keys:
            - grade_accuracy_score (float): How close final grade matches target (0–1)
            - semantic_preservation_score (float): Meaning retention (0–1)
            - sentence_length_reduction_score (float): Sentence shortening (0–1)
            - vocabulary_simplification_score (float): Word simplification (0–1)
            - instructional_suitability_score (float): Weighted composite (0–1)
            - diagnostic (dict): Intermediate values for debugging/analysis

    Raises:
        ValueError: If readability dicts lack "average_grade" key,
            or if target_grade is non-numeric or negative.

    Example:
        >>> result = instructional_suitability_score(
        ...     original_text="Complex academic text...",
        ...     simplified_text="Simple version...",
        ...     readability_before={"average_grade": 10.5},
        ...     readability_after={"average_grade": 5.2},
        ...     target_grade=5.0,
        ...     semantic_score=0.87
        ... )
        >>> result["instructional_suitability_score"]  # Primary output
        0.85
    """
    # ─────────────────────────────────────────────────────────────────────
    # Input Validation
    # ─────────────────────────────────────────────────────────────────────
    if not isinstance(target_grade, (int, float)) or target_grade < 0:
        raise ValueError(f"target_grade must be non-negative number, got {target_grade}")

    if "average_grade" not in readability_before:
        raise ValueError(
            "readability_before must include 'average_grade' key"
        )
    if "average_grade" not in readability_after:
        raise ValueError(
            "readability_after must include 'average_grade' key"
        )

    original_grade = readability_before["average_grade"]
    final_grade = readability_after["average_grade"]

    if not isinstance(original_grade, (int, float)) or not isinstance(
        final_grade, (int, float)
    ):
        raise ValueError("average_grade values must be numeric")

    # ─────────────────────────────────────────────────────────────────────
    # Metric 1: Grade Accuracy Score (35% weight)
    # ─────────────────────────────────────────────────────────────────────
    grade_accuracy_score = _compute_grade_accuracy_score(final_grade, target_grade)

    # ─────────────────────────────────────────────────────────────────────
    # Metric 2: Semantic Preservation Score (35% weight)
    # ─────────────────────────────────────────────────────────────────────
    semantic_preservation_result = (
        semantic_score if semantic_score is not None else 0.5
    )
    semantic_preservation_result = max(0.0, min(1.0, semantic_preservation_result))

    # ─────────────────────────────────────────────────────────────────────
    # Metric 3: Sentence Length Reduction Score (15% weight)
    # ─────────────────────────────────────────────────────────────────────
    (
        sentence_length_reduction_score,
        avg_sentence_before,
        avg_sentence_after,
    ) = _compute_sentence_length_reduction_score(original_text, simplified_text)

    # ─────────────────────────────────────────────────────────────────────
    # Metric 4: Vocabulary Simplification Score (15% weight)
    # ─────────────────────────────────────────────────────────────────────
    (
        vocabulary_simplification_score,
        avg_word_len_before,
        avg_word_len_after,
    ) = _compute_vocabulary_simplification_score(original_text, simplified_text)

    # ─────────────────────────────────────────────────────────────────────
    # Weighted Composite Score
    # ─────────────────────────────────────────────────────────────────────
    instructional_suitability = (
        0.35 * grade_accuracy_score
        + 0.35 * semantic_preservation_result
        + 0.15 * sentence_length_reduction_score
        + 0.15 * vocabulary_simplification_score
    )
    # Clamp to [0, 1] as safety measure (should already be bounded)
    instructional_suitability = max(0.0, min(1.0, instructional_suitability))

    # ─────────────────────────────────────────────────────────────────────
    # Diagnostic Metadata
    # ─────────────────────────────────────────────────────────────────────
    diagnostic = {
        "target_grade": target_grade,
        "final_grade": final_grade,
        "original_grade": original_grade,
        "avg_sentence_length_before": avg_sentence_before,
        "avg_sentence_length_after": avg_sentence_after,
        "avg_word_length_before": avg_word_len_before,
        "avg_word_length_after": avg_word_len_after,
    }

    return {
        "grade_accuracy_score": round(grade_accuracy_score, 4),
        "semantic_preservation_score": round(semantic_preservation_result, 4),
        "sentence_length_reduction_score": round(sentence_length_reduction_score, 4),
        "vocabulary_simplification_score": round(
            vocabulary_simplification_score, 4
        ),
        "instructional_suitability_score": round(instructional_suitability, 4),
        "diagnostic": diagnostic,
    }


# ─────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────


def _compute_grade_accuracy_score(final_grade: float, target_grade: float) -> float:
    """
    Compute how closely the final grade matches the target grade.

    Formula: max(0, 1 - abs(final_grade - target_grade) / 4.0)

    Rationale:
    - A 4-grade spread represents the full practical range (K–College)
    - Perfect accuracy (0 grade difference) = 1.0
    - 4+ grades off = 0.0
    - Values between are linearly interpolated

    Args:
        final_grade (float): Achieved readability grade after simplification
        target_grade (float): Target grade requested by user

    Returns:
        float: Score in [0, 1] where 1.0 = perfect accuracy
    """
    score = 1 - abs(final_grade - target_grade) / 4.0
    return max(0.0, score)


def _compute_sentence_length_reduction_score(
    original_text: str, simplified_text: str
) -> tuple[float, float, float]:
    """
    Compute how much shorter the sentences became in the simplified text.

    Method:
    1. Tokenize both texts into sentences
    2. Count words in each text
    3. Calculate average words per sentence before and after
    4. Compute reduction ratio: (before - after) / before
    5. Clamp to [0, 1]

    Rationale:
    - Shorter sentences improve readability and accessibility
    - A 50% reduction = 0.5 score
    - No reduction = 0.0 score
    - Excessive truncation (>100% reduction, theoretically impossible) clamped at 1.0

    Args:
        original_text (str): Original text before simplification
        simplified_text (str): Simplified text after simplification

    Returns:
        tuple: (reduction_score, avg_words_before, avg_words_after)
            - reduction_score (float): Score in [0, 1]
            - avg_words_before (float): Average words per sentence in original
            - avg_words_after (float): Average words per sentence in simplified
    """
    # Tokenize sentences
    sentences_before = nltk.sent_tokenize(original_text)
    sentences_after = nltk.sent_tokenize(simplified_text)

    # Handle edge case: no sentences found
    if not sentences_before or not sentences_after:
        return 0.0, 0.0, 0.0

    # Count total words in each text
    words_before = original_text.split()
    words_after = simplified_text.split()

    total_words_before = len(words_before)
    total_words_after = len(words_after)
    sentence_count_before = len(sentences_before)
    sentence_count_after = len(sentences_after)

    # Calculate averages
    avg_words_before = (
        total_words_before / sentence_count_before if sentence_count_before > 0 else 0
    )
    avg_words_after = (
        total_words_after / sentence_count_after if sentence_count_after > 0 else 0
    )

    # Compute reduction ratio: positive reduction = higher score
    if avg_words_before > 0:
        reduction_ratio = (avg_words_before - avg_words_after) / avg_words_before
    else:
        reduction_ratio = 0.0

    # Clamp to [0, 1]
    score = max(0.0, min(1.0, reduction_ratio))

    return score, avg_words_before, avg_words_after


def _compute_vocabulary_simplification_score(
    original_text: str, simplified_text: str
) -> tuple[float, float, float]:
    """
    Compute how much simpler the vocabulary became in the simplified text.

    Method:
    1. Split both texts into words (lowercased)
    2. Calculate average word length before and after
    3. Compute simplification ratio: (before - after) / before
    4. Clamp to [0, 1]

    Rationale:
    - Average word length is a strong proxy for vocabulary complexity
    - Shorter words = simpler, more accessible vocabulary
    - A 20% reduction in average word length = 0.2 score
    - No reduction = 0.0 score

    Args:
        original_text (str): Original text before simplification
        simplified_text (str): Simplified text after simplification

    Returns:
        tuple: (simplification_score, avg_len_before, avg_len_after)
            - simplification_score (float): Score in [0, 1]
            - avg_len_before (float): Average word length in original
            - avg_len_after (float): Average word length in simplified
    """
    # Split into words and lowercase for consistent measurement
    words_before = original_text.lower().split()
    words_after = simplified_text.lower().split()

    # Handle edge case: no words found
    if not words_before or not words_after:
        return 0.0, 0.0, 0.0

    # Calculate average word lengths
    avg_word_len_before = sum(len(w) for w in words_before) / len(words_before)
    avg_word_len_after = sum(len(w) for w in words_after) / len(words_after)

    # Compute simplification ratio: positive reduction = higher score
    if avg_word_len_before > 0:
        simplification_ratio = (avg_word_len_before - avg_word_len_after) / avg_word_len_before
    else:
        simplification_ratio = 0.0

    # Clamp to [0, 1]
    score = max(0.0, min(1.0, simplification_ratio))

    return score, avg_word_len_before, avg_word_len_after
