"""
Reliability Assessment Module

Evaluates whether a simplified text is safe for instructional use based on
semantic preservation, keyword retention, and grade targeting accuracy.

Teachers use reliability status to make confidence-informed decisions about
whether to deploy simplified text in their classrooms.
"""

from typing import TypedDict


class ReliabilityAssessment(TypedDict):
    """Return type for assess_reliability function."""

    semantic_status: str
    terminology_status: str
    grade_alignment_status: str
    reliability_status: str
    warnings: list[str]


def assess_reliability(
    semantic_score: float | None,
    keywords_preserved_count: int,
    new_grade: float,
    target_grade: float,
) -> ReliabilityAssessment:
    """
    Assess the reliability and instructional suitability of simplified text.

    Evaluates semantic preservation, keyword retention, and grade alignment
    to determine overall reliability for classroom use. Returns status labels
    and warnings for teacher decision-making.

    Args:
        semantic_score (float | None): Semantic similarity 0.0-1.0 or None if unavailable
        keywords_preserved_count (int): Number of keywords preserved in simplification
        new_grade (float): Achieved grade level of simplified text
        target_grade (float): Requested target grade level

    Returns:
        ReliabilityAssessment dict with:
        - semantic_status (str): "High preservation", "Moderate preservation", or "Low preservation"
        - terminology_status (str): "Strong terminology retention", "Moderate terminology retention", or "Terminology loss risk"
        - grade_alignment_status (str): "Target level achieved" or "Target level not achieved"
        - reliability_status (str): "High", "Moderate", or "Review Recommended"
        - warnings (list[str]): List of warnings for teachers (empty if all good)

    Examples:
        >>> assess_reliability(0.87, 6, 5.2, 5.0)
        {
            "semantic_status": "High preservation",
            "terminology_status": "Strong terminology retention",
            "grade_alignment_status": "Target level achieved",
            "reliability_status": "High",
            "warnings": []
        }

        >>> assess_reliability(0.72, 2, 7.5, 5.0)
        {
            "semantic_status": "Low preservation",
            "terminology_status": "Terminology loss risk",
            "grade_alignment_status": "Target level not achieved",
            "reliability_status": "Review Recommended",
            "warnings": [
                "Semantic preservation is low (0.72) — some concepts may be lost",
                "Only 2 keywords preserved — STEM/domain vocabulary may be missing",
                "Grade level (7.5) is 2.5 levels above target (5.0)"
            ]
        }
    """
    warnings: list[str] = []

    # ─────────────────────────────────────────────────────────────────────
    # 1. Semantic Similarity Reliability
    # ─────────────────────────────────────────────────────────────────────
    if semantic_score is None:
        semantic_status = "Unavailable (model not loaded)"
        semantic_reliability = 0.5  # Neutral for overall calculation
        warnings.append(
            "Semantic similarity not computed — cannot assess meaning preservation"
        )
    elif semantic_score >= 0.85:
        semantic_status = "High preservation"
        semantic_reliability = 1.0
    elif semantic_score >= 0.75:
        semantic_status = "Moderate preservation"
        semantic_reliability = 0.7
    else:
        semantic_status = "Low preservation"
        semantic_reliability = 0.0
        warnings.append(
            f"Semantic preservation is low ({semantic_score:.2f}) — "
            "some concepts may be lost or significantly rewarded"
        )

    # ─────────────────────────────────────────────────────────────────────
    # 2. Keyword Preservation Reliability
    # ─────────────────────────────────────────────────────────────────────
    if keywords_preserved_count >= 5:
        terminology_status = "Strong terminology retention"
        terminology_reliability = 1.0
    elif keywords_preserved_count >= 3:
        terminology_status = "Moderate terminology retention"
        terminology_reliability = 0.7
    else:
        terminology_status = "Terminology loss risk"
        terminology_reliability = 0.0
        warnings.append(
            f"Only {keywords_preserved_count} keyword(s) preserved — "
            "STEM/domain vocabulary may be missing or replaced"
        )

    # ─────────────────────────────────────────────────────────────────────
    # 3. Grade Targeting Accuracy
    # ─────────────────────────────────────────────────────────────────────
    grade_difference = abs(new_grade - target_grade)

    if grade_difference <= 2.0:
        grade_alignment_status = "Target level achieved"
        grade_reliability = 1.0
    else:
        grade_alignment_status = "Target level not achieved"
        grade_reliability = 0.0
        warnings.append(
            f"Grade level ({new_grade:.1f}) is {grade_difference:.1f} levels "
            f"{'above' if new_grade > target_grade else 'below'} target ({target_grade:.1f})"
        )

    # ─────────────────────────────────────────────────────────────────────
    # 4. Overall Reliability Status
    # ─────────────────────────────────────────────────────────────────────
    # High: semantic >= 0.85 AND keywords >= 5
    # Moderate: semantic >= 0.75 (regardless of keywords)
    # Review Recommended: otherwise

    if semantic_score is not None and semantic_score >= 0.85 and keywords_preserved_count >= 5:
        reliability_status = "High"
    elif semantic_score is not None and semantic_score >= 0.75:
        reliability_status = "Moderate"
    else:
        reliability_status = "Review Recommended"

    return {
        "semantic_status": semantic_status,
        "terminology_status": terminology_status,
        "grade_alignment_status": grade_alignment_status,
        "reliability_status": reliability_status,
        "warnings": warnings,
    }


def format_reliability_section(assessment: ReliabilityAssessment) -> str:
    """
    Format reliability assessment as Markdown section for teacher report.

    Args:
        assessment (ReliabilityAssessment): Result from assess_reliability()

    Returns:
        str: Markdown-formatted Reliability Assessment section
    """
    lines = [
        "## Reliability Assessment\n",
        "### Overall Status: **{}**\n".format(assessment["reliability_status"]),
    ]

    # Reliability status explanation
    if assessment["reliability_status"] == "High":
        lines.append(
            "This simplified text meets strong quality criteria and is **recommended for classroom use**. "
            "Semantic meaning is well preserved, key terminology is retained, and the target grade level "
            "is achieved.\n"
        )
    elif assessment["reliability_status"] == "Moderate":
        lines.append(
            "This simplified text is **generally suitable for classroom use**, but review before deploying. "
            "Semantic preservation is good, though some terminology or grade targeting may need attention.\n"
        )
    else:  # Review Recommended
        lines.append(
            "This simplified text **requires teacher review** before classroom use. "
            "One or more reliability metrics are below recommended thresholds. "
            "See warnings below for specific concerns.\n"
        )

    # Detailed metrics
    lines.append("### Detailed Metrics\n")
    lines.append(f"- **Semantic Preservation:** {assessment['semantic_status']}\n")
    lines.append(f"- **Terminology Retention:** {assessment['terminology_status']}\n")
    lines.append(f"- **Grade Alignment:** {assessment['grade_alignment_status']}\n")

    # Warnings section
    if assessment["warnings"]:
        lines.append("\n## Reliability Warnings\n")
        for warning in assessment["warnings"]:
            lines.append(f"⚠️ {warning}\n")
        lines.append("\n")

    return "".join(lines)
