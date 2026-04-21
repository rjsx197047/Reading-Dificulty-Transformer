"""
Report Generator Module

Generates Markdown-formatted accessibility adaptation reports for teachers.
Transforms differentiation metadata into readable reports explaining how text
was simplified and whether it's suitable for classroom use.

Includes reliability assessment to help teachers understand instructional safety.
"""

from app.core.reliability_assessment import (
    assess_reliability,
    format_reliability_section,
)


def generate_teacher_report(metadata: dict, original_keywords: list = None, preserved_keywords: list = None, target_grade: float = None) -> tuple[str, dict]:
    """
    Generate a Markdown-formatted accessibility adaptation report for teachers.

    Converts differentiation metadata into a structured, printer-friendly report
    explaining how text was simplified, providing reliability assessment, and
    offering guidance for classroom use.

    Sections included:
    - Reading Level Metrics
    - Structural Changes
    - Semantic Quality
    - Keywords & Terminology
    - Summary
    - Reliability Assessment (NEW)
    - Teacher Notes & Recommendations

    Args:
        metadata (dict): Differentiation metadata from generate_differentiation_metadata().
            Expected keys:
            - grade_reduction (float)
            - sentence_count_before/after, avg_sentence_length_before/after
            - word_count_before/after, avg_word_length_before/after
            - semantic_preservation_score (float)
            - keywords_preserved_count (int)
            - accessibility_summary (str)
        original_keywords (list, optional): Keywords extracted from original text
        preserved_keywords (list, optional): Keywords preserved in simplified text
        target_grade (float, optional): Target grade for reliability assessment

    Returns:
        tuple[str, dict]: (markdown_report, reliability_assessment)
        - markdown_report: Markdown string with full teacher report
        - reliability_assessment: dict with semantic_status, terminology_status,
                                 grade_alignment_status, reliability_status, warnings

    Example:
        >>> report, assessment = generate_teacher_report(metadata, target_grade=5.0)
        >>> print(report)
        # Accessibility Adaptation Report
        ...
        >>> print(assessment["reliability_status"])
        "High"
    """
    if not metadata:
        default_assessment = {
            "semantic_status": "Unavailable",
            "terminology_status": "Unknown",
            "grade_alignment_status": "Unknown",
            "reliability_status": "Unknown",
            "warnings": ["No metadata available"],
        }
        return ("# Accessibility Adaptation Report\n\nNo metadata available.\n", default_assessment)

    # Extract metadata values with safe defaults
    grade_reduction = metadata.get("grade_reduction", 0.0)
    sentence_count_before = metadata.get("sentence_count_before", 0)
    sentence_count_after = metadata.get("sentence_count_after", 0)
    avg_sentence_length_before = metadata.get("avg_sentence_length_before", 0.0)
    avg_sentence_length_after = metadata.get("avg_sentence_length_after", 0.0)
    word_count_before = metadata.get("word_count_before", 0)
    word_count_after = metadata.get("word_count_after", 0)
    avg_word_length_before = metadata.get("avg_word_length_before", 0.0)
    avg_word_length_after = metadata.get("avg_word_length_after", 0.0)
    semantic_score = metadata.get("semantic_preservation_score", None)
    keywords_preserved_count = metadata.get("keywords_preserved_count", 0)
    accessibility_summary = metadata.get("accessibility_summary", "")

    # Compute reliability assessment
    new_grade = metadata.get("grade_reduction", 0.0) * -1 + (target_grade or 7.0)  # Estimate
    # For more accurate grade, we should pass it directly, but fallback to calculation
    reliability_assessment = assess_reliability(
        semantic_score=semantic_score,
        keywords_preserved_count=keywords_preserved_count,
        new_grade=new_grade if target_grade else 7.0,  # Fallback if target_grade not provided
        target_grade=target_grade or 7.0,
    )

    # Calculate derived metrics for report
    sentence_reduction_pct = (
        100 * (sentence_count_before - sentence_count_after) / sentence_count_before
        if sentence_count_before > 0
        else 0
    )
    word_reduction_pct = (
        100 * (word_count_before - word_count_after) / word_count_before
        if word_count_before > 0
        else 0
    )
    sentence_length_reduction_pct = (
        100 * (avg_sentence_length_before - avg_sentence_length_after) / avg_sentence_length_before
        if avg_sentence_length_before > 0
        else 0
    )
    vocabulary_simplification_pct = (
        100 * (avg_word_length_before - avg_word_length_after) / avg_word_length_before
        if avg_word_length_before > 0
        else 0
    )

    # Build report sections
    report_parts = []

    # Header
    report_parts.append("# Accessibility Adaptation Report\n")

    # Section 1: Reading Level Metrics
    report_parts.append(_build_reading_level_section(grade_reduction))

    # Section 2: Structural Changes
    report_parts.append(
        _build_structural_changes_section(
            sentence_count_before=sentence_count_before,
            sentence_count_after=sentence_count_after,
            sentence_length_reduction_pct=sentence_length_reduction_pct,
            avg_sentence_length_before=avg_sentence_length_before,
            avg_sentence_length_after=avg_sentence_length_after,
            word_count_before=word_count_before,
            word_count_after=word_count_after,
            word_reduction_pct=word_reduction_pct,
            vocabulary_simplification_pct=vocabulary_simplification_pct,
            avg_word_length_before=avg_word_length_before,
            avg_word_length_after=avg_word_length_after,
        )
    )

    # Section 3: Semantic Quality
    report_parts.append(_build_semantic_quality_section(semantic_score))

    # Section 4: Keywords Preserved
    report_parts.append(
        _build_keywords_section(
            keywords_preserved_count=keywords_preserved_count,
            preserved_keywords=preserved_keywords,
        )
    )

    # Section 5: Summary
    report_parts.append(_build_summary_section(accessibility_summary))

    # Section 6 (NEW): Reliability Assessment
    report_parts.append(format_reliability_section(reliability_assessment))

    # Section 7: Teacher Notes and Guidance
    report_parts.append(_build_teacher_notes_section(grade_reduction, semantic_score))

    # Combine all sections
    full_report = "\n".join(report_parts)

    return (full_report, reliability_assessment)


# ─────────────────────────────────────────────────────────────────────────
# Report Section Builders
# ─────────────────────────────────────────────────────────────────────────


def _build_reading_level_section(grade_reduction: float) -> str:
    """Build the Reading Level Metrics section."""
    return f"""## Reading Level Metrics

This simplified text reduces reading difficulty by **{grade_reduction} grade levels**, making it more accessible to struggling readers while maintaining content integrity.

"""


def _build_structural_changes_section(
    sentence_count_before: int,
    sentence_count_after: int,
    sentence_length_reduction_pct: float,
    avg_sentence_length_before: float,
    avg_sentence_length_after: float,
    word_count_before: int,
    word_count_after: int,
    word_reduction_pct: float,
    vocabulary_simplification_pct: float,
    avg_word_length_before: float,
    avg_word_length_after: float,
) -> str:
    """Build the Structural Changes section."""
    sections = ["## Structural Changes\n"]

    # Sentence changes
    sections.append("### Sentence Structure")
    if sentence_count_after > sentence_count_before:
        sections.append(
            f"- **Sentence Count:** {sentence_count_before} → {sentence_count_after} "
            f"(+{sentence_count_after - sentence_count_before} additional chunks)"
        )
        sections.append(
            f"  - Long, complex sentences were broken into shorter, more manageable units."
        )
    else:
        sections.append(
            f"- **Sentence Count:** {sentence_count_before} → {sentence_count_after}"
        )

    sections.append(
        f"- **Average Sentence Length:** {avg_sentence_length_before:.1f} → {avg_sentence_length_after:.1f} words"
    )
    sections.append(
        f"  - Sentences reduced by **{sentence_length_reduction_pct:.0f}%**, improving scanability."
    )

    # Word count changes
    sections.append("\n### Word Count")
    sections.append(
        f"- **Total Words:** {word_count_before} → {word_count_after} "
        f"({word_reduction_pct:+.0f}%)"
    )
    sections.append(
        f"  - Text is {word_reduction_pct:.0f}% {'shorter' if word_reduction_pct > 0 else 'longer'}, "
        f"reducing cognitive load."
    )

    # Vocabulary changes
    sections.append("\n### Vocabulary Simplification")
    sections.append(
        f"- **Average Word Length:** {avg_word_length_before:.1f} → {avg_word_length_after:.1f} characters"
    )
    sections.append(
        f"  - Vocabulary simplified by **{vocabulary_simplification_pct:.0f}%** through systematic replacement "
        f"of complex terms with simpler alternatives."
    )

    return "\n".join(sections) + "\n"


def _build_semantic_quality_section(semantic_score: float) -> str:
    """Build the Semantic Quality section."""
    sections = ["## Semantic Quality\n"]

    semantic_pct = semantic_score * 100

    sections.append(f"### Meaning Preservation Score: {semantic_pct:.0f}%")
    sections.append(
        f"*Semantic similarity between original and simplified text (0-100% scale)*\n"
    )

    if semantic_score >= 0.85:
        assessment = (
            "**Excellent preservation** — The simplified text retains nearly all original meaning. "
            "Core concepts, relationships, and nuances are intact. Highly suitable for classroom use."
        )
    elif semantic_score >= 0.70:
        assessment = (
            "**Good preservation** — Most key concepts and meaning are retained. "
            "Some minor simplifications occurred, but the core message is preserved. "
            "Suitable for most classroom applications."
        )
    elif semantic_score >= 0.50:
        assessment = (
            "**Moderate preservation** — Substantial simplification occurred. "
            "Some concepts were condensed or simplified. "
            "Review text to ensure critical information is still present."
        )
    else:
        assessment = (
            "**Limited preservation** — Significant meaning loss may have occurred. "
            "Text was heavily modified for accessibility. "
            "Verify that core content aligns with learning objectives."
        )

    sections.append(f"- {assessment}")

    return "\n".join(sections) + "\n"


def _build_keywords_section(keywords_preserved_count: int, preserved_keywords: list = None) -> str:
    """Build the Keywords Preserved section."""
    sections = ["## Keywords & Terminology\n"]

    if keywords_preserved_count > 0:
        sections.append(
            f"**{keywords_preserved_count} specialized term{'s' if keywords_preserved_count != 1 else ''} "
            f"{'were' if keywords_preserved_count != 1 else 'was'} protected** to maintain domain-specific vocabulary.\n"
        )

        if preserved_keywords and len(preserved_keywords) > 0:
            sections.append("Protected terms:")
            # Format keywords in a bulleted list, limiting to 20 items displayed
            displayed_keywords = preserved_keywords[:20]
            for keyword in displayed_keywords:
                sections.append(f"- {keyword}")

            if len(preserved_keywords) > 20:
                sections.append(f"- ... and {len(preserved_keywords) - 20} more")
    else:
        sections.append(
            "No specialized terms were locked during simplification. "
            "All vocabulary was subject to replacement for accessibility."
        )

    return "\n".join(sections) + "\n"


def _build_summary_section(accessibility_summary: str) -> str:
    """Build the Summary section."""
    sections = ["## Summary\n"]

    if accessibility_summary:
        sections.append(accessibility_summary)
    else:
        sections.append("No summary available.")

    return "\n".join(sections) + "\n"


def _build_teacher_notes_section(grade_reduction: float, semantic_score: float) -> str:
    """Build the Teacher Notes and Recommendations section."""
    sections = ["## Teacher Notes & Recommendations\n"]

    # Grade-based guidance
    if grade_reduction >= 5.0:
        grade_guidance = (
            "This is a **major reduction** in difficulty. "
            "Suitable for students with severe reading difficulties or those significantly below grade level. "
            "Monitor comprehension closely during initial reading."
        )
    elif grade_reduction >= 3.0:
        grade_guidance = (
            "This is a **substantial reduction** in difficulty. "
            "Appropriate for students 2-3 grade levels below their peers. "
            "Can serve as a bridge for building content knowledge before tackling original text."
        )
    elif grade_reduction >= 1.0:
        grade_guidance = (
            "This is a **moderate reduction** in difficulty. "
            "Suitable for students 1-2 grade levels below grade level, or as support material. "
            "Consider pairing with original text for advanced readers."
        )
    else:
        grade_guidance = (
            "This text has a **minimal reduction** in reading difficulty. "
            "May not significantly improve accessibility for struggling readers. "
            "Review whether additional simplification is needed."
        )

    sections.append("### For Your Grade Level")
    sections.append(f"- {grade_guidance}\n")

    # Semantic-based guidance
    if semantic_score >= 0.80:
        semantic_guidance = (
            "The simplified text maintains excellent fidelity to the original. "
            "You can confidently use it as a primary text for differentiated instruction."
        )
    elif semantic_score >= 0.60:
        semantic_guidance = (
            "Most core concepts are preserved. "
            "Use this version for students who struggle with reading but not with content comprehension. "
            "Supplement with discussion to reinforce any simplified concepts."
        )
    else:
        semantic_guidance = (
            "Some content has been significantly simplified. "
            "Review the text carefully and consider supplementing with visual aids, videos, or discussion "
            "to ensure students grasp the intended learning objectives."
        )

    sections.append("### For Content Integrity")
    sections.append(f"- {semantic_guidance}\n")

    # General recommendations
    sections.append("### Implementation Tips")
    sections.append(
        "- Preview this text before classroom use to verify it meets your learning objectives."
    )
    sections.append(
        "- Consider using the original text with advanced readers while providing this simplified version to struggling readers."
    )
    sections.append(
        "- Pair reading with comprehension questions and discussion to build deep understanding."
    )
    sections.append(
        "- Monitor student engagement and adjust support based on feedback.\n"
    )

    sections.append("---\n")
    sections.append(
        "*Report generated by Reading Difficulty Transformer. "
        "For accessibility best practices and classroom implementation guidance, see the full documentation.*"
    )

    return "\n".join(sections)


# ─────────────────────────────────────────────────────────────────────────
# Document-level Report Generation
# ─────────────────────────────────────────────────────────────────────────


def generate_document_report(
    document_metrics: dict,
    paragraph_count: int,
) -> str:
    """
    Generate a Markdown-formatted document-level accessibility report.

    Provides summary of multi-paragraph document transformation with
    aggregate metrics and document-level reliability assessment.

    Args:
        document_metrics (dict): Aggregate metrics from compute_document_metrics().
            Expected keys:
            - average_original_grade (float)
            - average_new_grade (float)
            - average_semantic_score (float | None)
            - total_keywords_preserved (int)
            - document_reliability (str)
            - paragraphs_processed (int)
        paragraph_count (int): Total number of paragraphs in document

    Returns:
        str: Markdown-formatted document report
    """
    if not document_metrics:
        return "# Document-Level Accessibility Report\n\nNo metrics available.\n"

    average_original_grade = document_metrics.get("average_original_grade", 0.0)
    average_new_grade = document_metrics.get("average_new_grade", 0.0)
    average_semantic_score = document_metrics.get("average_semantic_score")
    total_keywords_preserved = document_metrics.get("total_keywords_preserved", 0)
    document_reliability = document_metrics.get("document_reliability", "Unknown")
    paragraphs_processed = document_metrics.get("paragraphs_processed", 0)

    grade_reduction = average_original_grade - average_new_grade

    # Build report sections
    sections = []

    # Header
    sections.append("# Document-Level Accessibility Report\n")

    # Overview
    sections.append("## Overview\n")
    sections.append(
        f"This document was processed as **{paragraphs_processed} paragraph(s)**. "
        f"The following metrics represent aggregate values across the entire document.\n"
    )

    # Reading Level Summary
    sections.append("## Reading Level Summary\n")
    sections.append(
        f"- **Original Average Grade Level:** {average_original_grade:.2f}\n"
    )
    sections.append(
        f"- **Transformed Average Grade Level:** {average_new_grade:.2f}\n"
    )
    sections.append(
        f"- **Average Reduction:** {grade_reduction:.2f} grade levels\n"
    )

    # Semantic Quality
    sections.append("\n## Semantic Quality\n")
    if average_semantic_score is not None:
        semantic_pct = average_semantic_score * 100
        sections.append(
            f"**Average Meaning Preservation Score:** {semantic_pct:.0f}%\n"
        )

        if average_semantic_score >= 0.85:
            assessment = (
                "**Excellent preservation** — Simplified text retains nearly all original meaning "
                "across paragraphs. Highly suitable for classroom use."
            )
        elif average_semantic_score >= 0.75:
            assessment = (
                "**Good preservation** — Most key concepts are retained across paragraphs. "
                "Suitable for most classroom applications."
            )
        elif average_semantic_score >= 0.50:
            assessment = (
                "**Moderate preservation** — Some concepts were simplified. "
                "Review text to ensure critical information is present."
            )
        else:
            assessment = (
                "**Limited preservation** — Significant meaning loss may have occurred. "
                "Verify that core content aligns with learning objectives."
            )

        sections.append(f"- {assessment}\n")
    else:
        sections.append("Semantic similarity scoring unavailable.\n")

    # Terminology
    sections.append("## Terminology Preservation\n")
    sections.append(
        f"**{total_keywords_preserved} specialized term(s) preserved** across all paragraphs "
        "to maintain domain-specific vocabulary.\n"
    )

    # Document Reliability
    sections.append("## Document Reliability Assessment\n")
    sections.append(f"**Overall Status:** {document_reliability}\n")

    if document_reliability == "High":
        reliability_text = (
            "This document is **recommended for classroom use**. "
            "Semantic meaning is well preserved, and target grade level is achieved across paragraphs."
        )
    elif document_reliability == "Moderate":
        reliability_text = (
            "This document is **generally suitable for classroom use**, but review before deploying. "
            "Some paragraphs may need closer inspection for content integrity."
        )
    else:  # Review Recommended
        reliability_text = (
            "This document **requires teacher review** before classroom use. "
            "One or more paragraphs have reliability metrics below recommended thresholds."
        )

    sections.append(f"\n{reliability_text}\n")

    # Recommendations
    sections.append("## Teacher Recommendations\n")
    sections.append(
        "- Review the paragraph-level transformation results to identify any paragraphs "
        "requiring additional editing.\n"
    )
    sections.append(
        "- Check that domain-specific terminology is correctly preserved.\n"
    )
    sections.append(
        "- Consider supplementing with visual aids or discussion for paragraphs with lower semantic scores.\n"
    )
    sections.append(
        "- Verify that the overall document maintains coherence and logical flow after transformation.\n"
    )

    sections.append("\n---\n")
    sections.append(
        "*Document report generated by Reading Difficulty Transformer. "
        "For accessibility best practices, see the full documentation.*"
    )

    return "\n".join(sections)
