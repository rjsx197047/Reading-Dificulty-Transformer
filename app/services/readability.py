"""
Reading-level detector module.

Uses traditional readability formulas (Flesch-Kincaid, Gunning Fog, SMOG, etc.)
via the textstat library to compute difficulty scores, then classifies the text
into a human-friendly difficulty level.
"""

import textstat

from app.models.schemas import DifficultyLevel, ReadabilityScores, TextStatistics


# Grade-level boundaries for classification
LEVEL_THRESHOLDS = [
    (0, 5, "Elementary", "K-5", "Suitable for young readers and early learners."),
    (5, 8, "Middle School", "6-8", "Appropriate for pre-teen and young teen readers."),
    (8, 12, "High School", "9-12", "Standard high school level content."),
    (12, 16, "College", "13-16", "College-level academic material."),
    (16, 100, "Graduate", "16+", "Advanced academic or professional writing."),
]


def compute_readability_scores(text: str) -> ReadabilityScores:
    """Compute all standard readability formula scores for the given text."""
    return ReadabilityScores(
        flesch_reading_ease=round(textstat.flesch_reading_ease(text), 2),
        flesch_kincaid_grade=round(textstat.flesch_kincaid_grade(text), 2),
        gunning_fog=round(textstat.gunning_fog(text), 2),
        smog_index=round(textstat.smog_index(text), 2),
        coleman_liau=round(textstat.coleman_liau_index(text), 2),
        ari=round(textstat.automated_readability_index(text), 2),
        dale_chall=round(textstat.dale_chall_readability_score(text), 2),
    )


def compute_text_statistics(text: str) -> TextStatistics:
    """Extract raw statistics from the text."""
    word_count = textstat.lexicon_count(text, removepunct=True)
    sentence_count = max(textstat.sentence_count(text), 1)
    syllable_count = textstat.syllable_count(text)
    char_count = textstat.char_count(text, ignore_spaces=True)

    # Complex words: 3+ syllables
    words = text.split()
    complex_words = [w for w in words if textstat.syllable_count(w) >= 3]
    complex_count = len(complex_words)

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    return TextStatistics(
        word_count=word_count,
        sentence_count=sentence_count,
        syllable_count=syllable_count,
        avg_words_per_sentence=round(word_count / sentence_count, 2),
        avg_syllables_per_word=round(syllable_count / max(word_count, 1), 2),
        complex_word_count=complex_count,
        complex_word_percentage=round(complex_count / max(word_count, 1) * 100, 2),
        character_count=char_count,
        paragraph_count=max(len(paragraphs), 1),
    )


def classify_difficulty(scores: ReadabilityScores) -> DifficultyLevel:
    """
    Classify the text into a difficulty level based on a consensus of
    multiple readability formulas. Uses a weighted average of grade-level
    scores to produce a single composite grade.
    """
    # Weighted average of grade-level metrics
    grade_scores = [
        (scores.flesch_kincaid_grade, 2.0),  # Most widely used
        (scores.gunning_fog, 1.5),
        (scores.smog_index, 1.5),
        (scores.coleman_liau, 1.0),
        (scores.ari, 1.0),
    ]

    total_weight = sum(w for _, w in grade_scores)
    composite_grade = sum(s * w for s, w in grade_scores) / total_weight

    # Clamp negative grades to 0
    composite_grade = max(composite_grade, 0)

    # Map composite grade to a level
    for low, high, level, grade_range, description in LEVEL_THRESHOLDS:
        if low <= composite_grade < high:
            # Confidence: higher when the composite is near the center of the range
            mid = (low + high) / 2
            spread = (high - low) / 2
            distance = abs(composite_grade - mid) / spread
            confidence = round(1.0 - distance * 0.3, 2)  # 0.7–1.0

            return DifficultyLevel(
                level=level,
                grade_range=grade_range,
                confidence=min(max(confidence, 0.5), 1.0),
                description=description,
            )

    # Fallback
    return DifficultyLevel(
        level="Graduate",
        grade_range="16+",
        confidence=0.6,
        description="Advanced academic or professional writing.",
    )


def generate_suggestions(scores: ReadabilityScores, stats: TextStatistics) -> list[str]:
    """Generate actionable suggestions to simplify the text."""
    suggestions = []

    if stats.avg_words_per_sentence > 25:
        suggestions.append(
            f"Shorten sentences. Your average is {stats.avg_words_per_sentence} words/sentence "
            f"— aim for under 20."
        )

    if stats.avg_syllables_per_word > 1.7:
        suggestions.append(
            "Use simpler vocabulary. Many words have 3+ syllables — try shorter synonyms."
        )

    if stats.complex_word_percentage > 15:
        suggestions.append(
            f"{stats.complex_word_percentage}% of words are complex (3+ syllables). "
            f"Replace jargon and technical terms where possible."
        )

    if scores.flesch_reading_ease < 30:
        suggestions.append(
            "The text is very difficult to read. Consider breaking it into "
            "shorter paragraphs with simpler sentence structures."
        )
    elif scores.flesch_reading_ease < 50:
        suggestions.append(
            "The text is fairly difficult. Try using active voice and "
            "common words to improve readability."
        )

    if scores.gunning_fog > 12:
        suggestions.append(
            "Gunning Fog index is high — reduce complex words and keep sentences concise."
        )

    if stats.paragraph_count == 1 and stats.sentence_count > 5:
        suggestions.append("Break the text into multiple paragraphs for better readability.")

    if not suggestions:
        suggestions.append("The text is already at a comfortable reading level. No changes needed.")

    return suggestions


def analyze_text(text: str) -> tuple[DifficultyLevel, ReadabilityScores, TextStatistics, list[str]]:
    """
    Full pipeline: compute scores, classify difficulty, and generate suggestions.
    Returns (difficulty, scores, statistics, suggestions).
    """
    scores = compute_readability_scores(text)
    stats = compute_text_statistics(text)
    difficulty = classify_difficulty(scores)
    suggestions = generate_suggestions(scores, stats)
    return difficulty, scores, stats, suggestions
