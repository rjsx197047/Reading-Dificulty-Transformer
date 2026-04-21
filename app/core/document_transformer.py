"""
Document-level text transformation module.

Handles multi-paragraph document processing with per-paragraph transformation
and aggregate document-level metrics and reliability assessment.
"""

import logging
from statistics import mean

logger = logging.getLogger(__name__)


def segment_paragraphs(text: str) -> list[str]:
    """
    Segment document into paragraphs using double-newline detection.

    Splits on \n\n boundaries and filters empty paragraphs.

    Args:
        text (str): Raw document text

    Returns:
        list[str]: List of non-empty paragraphs
    """
    # Split on double newlines (paragraph boundaries)
    raw_paragraphs = text.split("\n\n")

    # Filter and clean: strip whitespace and remove empty strings
    paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

    if not paragraphs:
        raise ValueError("Document contains no valid paragraphs after segmentation")

    logger.info("Segmented document into %d paragraphs", len(paragraphs))
    return paragraphs


def compute_document_metrics(
    paragraph_results: list[dict],
) -> dict:
    """
    Compute aggregate metrics across all paragraphs.

    Args:
        paragraph_results (list[dict]): List of per-paragraph transformation results.
            Each dict should have keys: original_grade, new_grade, semantic_score,
            keywords_preserved_count

    Returns:
        dict: Aggregate metrics with average grades, semantic score, and document reliability
    """
    if not paragraph_results:
        raise ValueError("No paragraph results provided")

    # Extract metrics
    original_grades = [p["original_grade"] for p in paragraph_results]
    new_grades = [p["new_grade"] for p in paragraph_results]
    semantic_scores = [
        p["semantic_score"]
        for p in paragraph_results
        if p["semantic_score"] is not None
    ]
    keywords_counts = [
        p["keywords_preserved_count"] for p in paragraph_results
    ]

    # Compute averages
    average_original_grade = mean(original_grades)
    average_new_grade = mean(new_grades)
    average_semantic_score = (
        mean(semantic_scores) if semantic_scores else None
    )
    total_keywords_preserved = sum(keywords_counts)

    # Determine document reliability based on average semantic score
    if average_semantic_score is None:
        document_reliability = "Review Recommended"
    elif average_semantic_score >= 0.85:
        document_reliability = "High"
    elif average_semantic_score >= 0.75:
        document_reliability = "Moderate"
    else:
        document_reliability = "Review Recommended"

    logger.info(
        "Document metrics: avg_original=%.2f, avg_new=%.2f, "
        "avg_semantic=%.3f, reliability=%s",
        average_original_grade,
        average_new_grade,
        average_semantic_score or 0.0,
        document_reliability,
    )

    return {
        "average_original_grade": round(average_original_grade, 2),
        "average_new_grade": round(average_new_grade, 2),
        "average_semantic_score": (
            round(average_semantic_score, 4)
            if average_semantic_score is not None
            else None
        ),
        "total_keywords_preserved": total_keywords_preserved,
        "document_reliability": document_reliability,
        "paragraphs_processed": len(paragraph_results),
    }
