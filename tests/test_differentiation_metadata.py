"""
Unit tests for differentiation_metadata module.

Tests the differentiation metadata generator with various text changes,
edge cases, and validation scenarios.
"""

import pytest

from app.core.differentiation_metadata import generate_differentiation_metadata


class TestDifferentiationMetadata:
    """Test cases for generate_differentiation_metadata function."""

    def test_basic_metadata_generation(self):
        """Test that metadata is generated correctly for a simplification."""
        original = (
            "The photosynthetic process involves the conversion of solar energy "
            "into chemical energy through oxidation-reduction reactions catalyzed "
            "by chlorophyll and associated protein complexes in the thylakoid membrane."
        )
        simplified = (
            "Plants use sunlight to make food. "
            "Green parts of leaves capture light. "
            "This energy turns into food the plant can use."
        )

        result = generate_differentiation_metadata(
            original_text=original,
            simplified_text=simplified,
            readability_before={"average_grade": 14.5},
            readability_after={"average_grade": 4.8},
            semantic_score=0.82,
            keywords_preserved=["photosynthesis", "energy", "chlorophyll"],
        )

        # Check all required keys present
        assert "grade_reduction" in result
        assert "sentence_count_before" in result
        assert "sentence_count_after" in result
        assert "avg_sentence_length_before" in result
        assert "avg_sentence_length_after" in result
        assert "word_count_before" in result
        assert "word_count_after" in result
        assert "avg_word_length_before" in result
        assert "avg_word_length_after" in result
        assert "semantic_preservation_score" in result
        assert "keywords_preserved_count" in result
        assert "accessibility_summary" in result

        # Check types
        assert isinstance(result["grade_reduction"], float)
        assert isinstance(result["sentence_count_before"], int)
        assert isinstance(result["sentence_count_after"], int)
        assert isinstance(result["accessibility_summary"], str)
        assert isinstance(result["keywords_preserved_count"], int)

    def test_grade_reduction_calculation(self):
        """Test that grade reduction is correctly calculated."""
        result = generate_differentiation_metadata(
            original_text="Test text.",
            simplified_text="Test text.",
            readability_before={"average_grade": 10.5},
            readability_after={"average_grade": 5.2},
            semantic_score=0.5,
            keywords_preserved=[],
        )

        # Grade reduction should be 10.5 - 5.2 = 5.3
        assert result["grade_reduction"] == 5.3

    def test_negative_grade_reduction(self):
        """Test when simplified text is actually harder (negative reduction)."""
        result = generate_differentiation_metadata(
            original_text="Test.",
            simplified_text="Test.",
            readability_before={"average_grade": 5.0},
            readability_after={"average_grade": 8.0},
            semantic_score=0.5,
            keywords_preserved=[],
        )

        # Grade reduction should be 5.0 - 8.0 = -3.0
        assert result["grade_reduction"] == -3.0

    def test_sentence_count_increase(self):
        """Test that increased sentence count is detected."""
        result = generate_differentiation_metadata(
            original_text="Long sentence here. Another one.",
            simplified_text="Short. Text. Here. More. Chunks.",
            readability_before={"average_grade": 8.0},
            readability_after={"average_grade": 5.0},
            semantic_score=0.7,
            keywords_preserved=[],
        )

        # Should detect more sentences in simplified
        assert result["sentence_count_after"] > result["sentence_count_before"]

    def test_sentence_length_reduction(self):
        """Test that sentence shortening is detected."""
        result = generate_differentiation_metadata(
            original_text="This is a very long sentence with many words that makes reading difficult.",
            simplified_text="This is short. Text here. Easy to read.",
            readability_before={"average_grade": 8.0},
            readability_after={"average_grade": 4.0},
            semantic_score=0.7,
            keywords_preserved=[],
        )

        # Simplified should have shorter sentences
        assert result["avg_sentence_length_after"] < result["avg_sentence_length_before"]

    def test_word_count_reduction(self):
        """Test that word count reduction is detected."""
        result = generate_differentiation_metadata(
            original_text="This is the original text.",
            simplified_text="This is short.",
            readability_before={"average_grade": 8.0},
            readability_after={"average_grade": 4.0},
            semantic_score=0.7,
            keywords_preserved=[],
        )

        # Simplified should have fewer words
        assert result["word_count_after"] < result["word_count_before"]

    def test_word_length_reduction(self):
        """Test that vocabulary simplification (word length reduction) is detected."""
        result = generate_differentiation_metadata(
            original_text="Comprehensive educational methodology.",
            simplified_text="Easy simple way.",
            readability_before={"average_grade": 10.0},
            readability_after={"average_grade": 4.0},
            semantic_score=0.6,
            keywords_preserved=[],
        )

        # Simplified should have shorter words on average
        assert result["avg_word_length_after"] < result["avg_word_length_before"]

    def test_keywords_preserved_count(self):
        """Test that keywords preserved count is correct."""
        keywords = ["photosynthesis", "mitochondria", "ATP"]
        result = generate_differentiation_metadata(
            original_text="Test text.",
            simplified_text="Test text.",
            readability_before={"average_grade": 8.0},
            readability_after={"average_grade": 5.0},
            semantic_score=0.8,
            keywords_preserved=keywords,
        )

        assert result["keywords_preserved_count"] == 3

    def test_empty_keywords_list(self):
        """Test with no keywords preserved."""
        result = generate_differentiation_metadata(
            original_text="Test text.",
            simplified_text="Simple text.",
            readability_before={"average_grade": 8.0},
            readability_after={"average_grade": 5.0},
            semantic_score=0.8,
            keywords_preserved=[],
        )

        assert result["keywords_preserved_count"] == 0

    def test_accessibility_summary_contains_key_info(self):
        """Test that accessibility summary contains important metrics."""
        result = generate_differentiation_metadata(
            original_text="Original complex text here.",
            simplified_text="Simple text here.",
            readability_before={"average_grade": 10.0},
            readability_after={"average_grade": 5.0},
            semantic_score=0.85,
            keywords_preserved=["keyword"],
        )

        summary = result["accessibility_summary"]

        # Should mention grade reduction
        assert "5.0" in summary or "5" in summary

        # Should mention semantic preservation
        assert "semantic" in summary.lower() or "meaning" in summary.lower()

        # Should mention keywords
        assert "keyword" in summary.lower() or "specialized" in summary.lower()

    def test_high_semantic_preservation_summary(self):
        """Test that summary reflects high semantic preservation."""
        result = generate_differentiation_metadata(
            original_text="Complex original text.",
            simplified_text="Simple version here.",
            readability_before={"average_grade": 10.0},
            readability_after={"average_grade": 5.0},
            semantic_score=0.95,  # Very high preservation
            keywords_preserved=[],
        )

        summary = result["accessibility_summary"]
        # Should mention excellent preservation
        assert "excellent" in summary.lower() or "well" in summary.lower()

    def test_low_semantic_preservation_warning(self):
        """Test that summary warns about lower semantic preservation."""
        result = generate_differentiation_metadata(
            original_text="Complex original text.",
            simplified_text="Different simplified text.",
            readability_before={"average_grade": 10.0},
            readability_after={"average_grade": 2.0},
            semantic_score=0.6,  # Moderate preservation
            keywords_preserved=[],
        )

        summary = result["accessibility_summary"]
        # Should acknowledge the semantic limitation
        assert "simplification" in summary.lower()

    def test_minimal_changes_summary(self):
        """Test summary when text is barely changed."""
        text = "This is a test sentence with moderate length."
        result = generate_differentiation_metadata(
            original_text=text,
            simplified_text=text,  # No change
            readability_before={"average_grade": 7.0},
            readability_after={"average_grade": 7.0},
            semantic_score=1.0,
            keywords_preserved=[],
        )

        summary = result["accessibility_summary"]
        # Should indicate minimal changes
        assert "maintained" in summary.lower() or "stable" in summary.lower()

    def test_invalid_empty_original_text_raises_error(self):
        """Test that empty original text raises ValueError."""
        with pytest.raises(ValueError, match="original_text must be non-empty"):
            generate_differentiation_metadata(
                original_text="",
                simplified_text="Test.",
                readability_before={"average_grade": 5.0},
                readability_after={"average_grade": 5.0},
                semantic_score=0.8,
                keywords_preserved=[],
            )

    def test_invalid_empty_simplified_text_raises_error(self):
        """Test that empty simplified text raises ValueError."""
        with pytest.raises(ValueError, match="simplified_text must be non-empty"):
            generate_differentiation_metadata(
                original_text="Test.",
                simplified_text="",
                readability_before={"average_grade": 5.0},
                readability_after={"average_grade": 5.0},
                semantic_score=0.8,
                keywords_preserved=[],
            )

    def test_missing_average_grade_before_raises_error(self):
        """Test that missing average_grade in readability_before raises error."""
        with pytest.raises(ValueError, match="readability_before must include"):
            generate_differentiation_metadata(
                original_text="Test.",
                simplified_text="Test.",
                readability_before={},  # Missing average_grade
                readability_after={"average_grade": 5.0},
                semantic_score=0.8,
                keywords_preserved=[],
            )

    def test_missing_average_grade_after_raises_error(self):
        """Test that missing average_grade in readability_after raises error."""
        with pytest.raises(ValueError, match="readability_after must include"):
            generate_differentiation_metadata(
                original_text="Test.",
                simplified_text="Test.",
                readability_before={"average_grade": 5.0},
                readability_after={},  # Missing average_grade
                semantic_score=0.8,
                keywords_preserved=[],
            )

    def test_non_numeric_grade_raises_error(self):
        """Test that non-numeric grade raises ValueError."""
        with pytest.raises(ValueError, match="average_grade values must be numeric"):
            generate_differentiation_metadata(
                original_text="Test.",
                simplified_text="Test.",
                readability_before={"average_grade": "ten"},  # String instead of number
                readability_after={"average_grade": 5.0},
                semantic_score=0.8,
                keywords_preserved=[],
            )

    def test_invalid_semantic_score_non_numeric(self):
        """Test that non-numeric semantic score raises ValueError."""
        with pytest.raises(ValueError, match="semantic_score must be numeric"):
            generate_differentiation_metadata(
                original_text="Test.",
                simplified_text="Test.",
                readability_before={"average_grade": 5.0},
                readability_after={"average_grade": 5.0},
                semantic_score="high",  # String instead of number
                keywords_preserved=[],
            )

    def test_semantic_score_out_of_range_low(self):
        """Test that semantic score < 0 raises ValueError."""
        with pytest.raises(ValueError, match="semantic_score must be between"):
            generate_differentiation_metadata(
                original_text="Test.",
                simplified_text="Test.",
                readability_before={"average_grade": 5.0},
                readability_after={"average_grade": 5.0},
                semantic_score=-0.5,  # Below 0
                keywords_preserved=[],
            )

    def test_semantic_score_out_of_range_high(self):
        """Test that semantic score > 1 raises ValueError."""
        with pytest.raises(ValueError, match="semantic_score must be between"):
            generate_differentiation_metadata(
                original_text="Test.",
                simplified_text="Test.",
                readability_before={"average_grade": 5.0},
                readability_after={"average_grade": 5.0},
                semantic_score=1.5,  # Above 1
                keywords_preserved=[],
            )

    def test_invalid_keywords_not_list(self):
        """Test that non-list keywords raises ValueError."""
        with pytest.raises(ValueError, match="keywords_preserved must be a list"):
            generate_differentiation_metadata(
                original_text="Test.",
                simplified_text="Test.",
                readability_before={"average_grade": 5.0},
                readability_after={"average_grade": 5.0},
                semantic_score=0.8,
                keywords_preserved="keyword",  # String instead of list
            )

    def test_values_are_rounded_appropriately(self):
        """Test that all float values are rounded to reasonable precision."""
        result = generate_differentiation_metadata(
            original_text="Original text for testing purposes.",
            simplified_text="Simple text here.",
            readability_before={"average_grade": 8.333333},
            readability_after={"average_grade": 5.666666},
            semantic_score=0.876543,
            keywords_preserved=["test"],
        )

        # Grade reduction should be rounded to 1 decimal
        assert len(str(result["grade_reduction"]).split(".")[-1]) <= 1

        # Avg sentence/word lengths should be rounded to 2 decimals
        assert len(str(result["avg_sentence_length_before"]).split(".")[-1]) <= 2
        assert len(str(result["avg_word_length_before"]).split(".")[-1]) <= 2

        # Semantic score should be rounded to 4 decimals
        assert len(str(result["semantic_preservation_score"]).split(".")[-1]) <= 4

    def test_complex_realistic_scenario(self):
        """Test with realistic academic-to-simple conversion."""
        original = (
            "The mitochondrial genome encodes essential oxidative phosphorylation "
            "components that are requisite for cellular metabolism and energy production "
            "through adenosine triphosphate synthesis. These organelles function through "
            "complex biochemical cascades involving electron transport chains and chemiosmotic "
            "gradients across the inner mitochondrial membrane."
        )

        simplified = (
            "Mitochondria are cell parts that make energy. "
            "They break down food molecules. "
            "This creates ATP, which powers cell activities. "
            "The process is called cellular respiration."
        )

        result = generate_differentiation_metadata(
            original_text=original,
            simplified_text=simplified,
            readability_before={"average_grade": 14.2},
            readability_after={"average_grade": 5.1},
            semantic_score=0.79,
            keywords_preserved=["mitochondria", "ATP", "respiration"],
        )

        # Check values make sense
        assert result["grade_reduction"] > 8.0  # Significant reduction
        assert result["word_count_after"] < result["word_count_before"]
        assert result["avg_sentence_length_after"] < result["avg_sentence_length_before"]
        assert result["keywords_preserved_count"] == 3
        assert len(result["accessibility_summary"]) > 100  # Non-trivial summary

    def test_boundary_semantic_scores(self):
        """Test with boundary semantic score values."""
        # Test with 0.0
        result_low = generate_differentiation_metadata(
            original_text="Test.",
            simplified_text="Test.",
            readability_before={"average_grade": 5.0},
            readability_after={"average_grade": 5.0},
            semantic_score=0.0,
            keywords_preserved=[],
        )
        assert result_low["semantic_preservation_score"] == 0.0

        # Test with 1.0
        result_high = generate_differentiation_metadata(
            original_text="Test.",
            simplified_text="Test.",
            readability_before={"average_grade": 5.0},
            readability_after={"average_grade": 5.0},
            semantic_score=1.0,
            keywords_preserved=[],
        )
        assert result_high["semantic_preservation_score"] == 1.0
