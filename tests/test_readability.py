"""Tests for the readability analysis module."""

from app.services.readability import (
    analyze_text,
    classify_difficulty,
    compute_readability_scores,
    compute_text_statistics,
    generate_suggestions,
)

SIMPLE_TEXT = (
    "The cat sat on the mat. The dog ran fast. I like the sun. "
    "It is a good day. We can play in the park."
)

COMPLEX_TEXT = (
    "The epistemological ramifications of quantum decoherence theory necessitate "
    "a fundamental reconceptualization of the observer-measurement paradigm. "
    "Consequently, the philosophical underpinnings of deterministic materialism "
    "are rendered increasingly untenable in light of contemporary empirical findings "
    "that corroborate the probabilistic interpretation of subatomic phenomena. "
    "Furthermore, the ontological implications of entanglement demonstrate the "
    "inadequacy of classical reductionist frameworks for comprehending the "
    "interconnected nature of physical reality."
)


def test_compute_scores_returns_all_fields():
    scores = compute_readability_scores(SIMPLE_TEXT)
    assert scores.flesch_reading_ease is not None
    assert scores.flesch_kincaid_grade is not None
    assert scores.gunning_fog is not None
    assert scores.smog_index is not None
    assert scores.coleman_liau is not None
    assert scores.ari is not None
    assert scores.dale_chall is not None


def test_simple_text_is_easier():
    simple_scores = compute_readability_scores(SIMPLE_TEXT)
    complex_scores = compute_readability_scores(COMPLEX_TEXT)
    # Flesch Reading Ease: higher = easier
    assert simple_scores.flesch_reading_ease > complex_scores.flesch_reading_ease


def test_simple_text_lower_grade():
    simple_scores = compute_readability_scores(SIMPLE_TEXT)
    complex_scores = compute_readability_scores(COMPLEX_TEXT)
    assert simple_scores.flesch_kincaid_grade < complex_scores.flesch_kincaid_grade


def test_text_statistics():
    stats = compute_text_statistics(SIMPLE_TEXT)
    assert stats.word_count > 0
    assert stats.sentence_count > 0
    assert stats.avg_words_per_sentence > 0
    assert stats.avg_syllables_per_word > 0


def test_classify_simple_vs_complex():
    simple_scores = compute_readability_scores(SIMPLE_TEXT)
    complex_scores = compute_readability_scores(COMPLEX_TEXT)
    simple_level = classify_difficulty(simple_scores)
    complex_level = classify_difficulty(complex_scores)
    # Simple text should have a lower Flesch-Kincaid grade than complex
    assert simple_scores.flesch_kincaid_grade < complex_scores.flesch_kincaid_grade
    # Complex should be College or Graduate level
    assert complex_level.level in ("College", "Graduate")


def test_analyze_text_full_pipeline():
    difficulty, scores, stats, suggestions = analyze_text(COMPLEX_TEXT)
    assert difficulty.level is not None
    assert difficulty.confidence >= 0.5
    assert scores.flesch_reading_ease is not None
    assert stats.word_count > 0
    assert len(suggestions) > 0


def test_suggestions_for_complex_text():
    scores = compute_readability_scores(COMPLEX_TEXT)
    stats = compute_text_statistics(COMPLEX_TEXT)
    suggestions = generate_suggestions(scores, stats)
    assert len(suggestions) >= 1
    # Should suggest simplification
    assert any("simpl" in s.lower() or "complex" in s.lower() or "shorter" in s.lower()
               for s in suggestions)
