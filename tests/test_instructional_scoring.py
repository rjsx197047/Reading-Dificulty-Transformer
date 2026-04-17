"""
Unit tests for instructional_scoring module.

Tests the instructional suitability scoring function with various inputs,
edge cases, and validation scenarios.
"""

import pytest

from app.core.instructional_scoring import instructional_suitability_score


class TestInstructionalSuitabilityScore:
    """Test cases for instructional_suitability_score function."""

    def test_basic_simplification_scores_correctly(self):
        """Test that a simplified text receives a higher suitability score."""
        original = (
            "The mitochondrial genome encodes essential oxidative phosphorylation "
            "components that are requisite for cellular metabolism and energy production."
        )
        simplified = (
            "Mitochondria are cell parts that make energy. "
            "They use oxygen to create fuel for the cell."
        )

        result = instructional_suitability_score(
            original_text=original,
            simplified_text=simplified,
            readability_before={"average_grade": 11.2},
            readability_after={"average_grade": 5.1},
            target_grade=5.0,
            semantic_score=0.88,
        )

        # All scores should be between 0 and 1
        assert 0.0 <= result["grade_accuracy_score"] <= 1.0
        assert 0.0 <= result["semantic_preservation_score"] <= 1.0
        assert 0.0 <= result["sentence_length_reduction_score"] <= 1.0
        assert 0.0 <= result["vocabulary_simplification_score"] <= 1.0
        assert 0.0 <= result["instructional_suitability_score"] <= 1.0

        # Final score should be composite of all metrics
        expected_composite = (
            0.35 * result["grade_accuracy_score"]
            + 0.35 * result["semantic_preservation_score"]
            + 0.15 * result["sentence_length_reduction_score"]
            + 0.15 * result["vocabulary_simplification_score"]
        )
        assert abs(result["instructional_suitability_score"] - expected_composite) < 0.001

    def test_perfect_grade_accuracy(self):
        """Test when final grade matches target grade exactly."""
        result = instructional_suitability_score(
            original_text="This is a test sentence.",
            simplified_text="This is a test sentence.",
            readability_before={"average_grade": 5.0},
            readability_after={"average_grade": 5.0},  # Perfect match
            target_grade=5.0,
            semantic_score=1.0,
        )

        # Grade accuracy should be 1.0 (perfect)
        assert result["grade_accuracy_score"] == 1.0

    def test_grade_four_points_off(self):
        """Test when final grade is 4 grades off (should score 0.0)."""
        result = instructional_suitability_score(
            original_text="This is a test sentence.",
            simplified_text="This is a test sentence.",
            readability_before={"average_grade": 5.0},
            readability_after={"average_grade": 9.0},  # 4 grades off
            target_grade=5.0,
            semantic_score=0.5,
        )

        # Grade accuracy should be 0.0 (4 grades = full penalty)
        assert result["grade_accuracy_score"] == 0.0

    def test_grade_two_points_off(self):
        """Test intermediate grade accuracy."""
        result = instructional_suitability_score(
            original_text="This is a test sentence.",
            simplified_text="This is a test sentence.",
            readability_before={"average_grade": 5.0},
            readability_after={"average_grade": 7.0},  # 2 grades off
            target_grade=5.0,
            semantic_score=0.5,
        )

        # Grade accuracy should be 0.5 (halfway to penalty)
        assert result["grade_accuracy_score"] == 0.5

    def test_semantic_score_none_defaults_to_neutral(self):
        """Test that None semantic_score defaults to 0.5."""
        result = instructional_suitability_score(
            original_text="This is a test sentence.",
            simplified_text="This is a test sentence.",
            readability_before={"average_grade": 5.0},
            readability_after={"average_grade": 5.0},
            target_grade=5.0,
            semantic_score=None,  # Not available
        )

        # Semantic score should default to 0.5 (neutral)
        assert result["semantic_preservation_score"] == 0.5

    def test_sentence_shortening_improves_score(self):
        """Test that sentence reduction increases the score."""
        original = "This is a long sentence that contains many words and ideas."
        simplified = "This is short. It is simple."

        result = instructional_suitability_score(
            original_text=original,
            simplified_text=simplified,
            readability_before={"average_grade": 8.0},
            readability_after={"average_grade": 4.0},
            target_grade=4.0,
            semantic_score=0.7,
        )

        # Sentence reduction should be positive (sentences got shorter)
        assert result["sentence_length_reduction_score"] > 0.0

    def test_vocabulary_simplification_improves_score(self):
        """Test that word length reduction increases the score."""
        original = "Sophisticated words in complicated sentences."
        simplified = "Simple easy words in plain text."

        result = instructional_suitability_score(
            original_text=original,
            simplified_text=simplified,
            readability_before={"average_grade": 8.0},
            readability_after={"average_grade": 4.0},
            target_grade=4.0,
            semantic_score=0.7,
        )

        # Vocabulary simplification should be positive (words got shorter)
        assert result["vocabulary_simplification_score"] > 0.0

    def test_no_change_gives_zero_reduction_scores(self):
        """Test that identical texts give zero reduction scores."""
        text = "This is a test sentence."

        result = instructional_suitability_score(
            original_text=text,
            simplified_text=text,
            readability_before={"average_grade": 5.0},
            readability_after={"average_grade": 5.0},
            target_grade=5.0,
            semantic_score=1.0,
        )

        # No sentence shortening
        assert result["sentence_length_reduction_score"] == 0.0
        # No vocabulary simplification
        assert result["vocabulary_simplification_score"] == 0.0

    def test_diagnostic_metadata_included(self):
        """Test that diagnostic metadata is returned."""
        result = instructional_suitability_score(
            original_text="Original text here.",
            simplified_text="Simple text.",
            readability_before={"average_grade": 8.0},
            readability_after={"average_grade": 4.0},
            target_grade=4.0,
            semantic_score=0.75,
        )

        # Check diagnostic dict exists and has expected keys
        assert "diagnostic" in result
        diagnostic = result["diagnostic"]
        assert "target_grade" in diagnostic
        assert "final_grade" in diagnostic
        assert "original_grade" in diagnostic
        assert "avg_sentence_length_before" in diagnostic
        assert "avg_sentence_length_after" in diagnostic
        assert "avg_word_length_before" in diagnostic
        assert "avg_word_length_after" in diagnostic

    def test_invalid_target_grade_raises_error(self):
        """Test that invalid target_grade raises ValueError."""
        with pytest.raises(ValueError, match="target_grade must be non-negative"):
            instructional_suitability_score(
                original_text="Test text.",
                simplified_text="Test text.",
                readability_before={"average_grade": 5.0},
                readability_after={"average_grade": 5.0},
                target_grade=-1,  # Invalid: negative
                semantic_score=0.5,
            )

    def test_missing_average_grade_in_readability_before_raises_error(self):
        """Test that missing 'average_grade' key raises ValueError."""
        with pytest.raises(ValueError, match="readability_before must include"):
            instructional_suitability_score(
                original_text="Test text.",
                simplified_text="Test text.",
                readability_before={},  # Missing 'average_grade'
                readability_after={"average_grade": 5.0},
                target_grade=5.0,
                semantic_score=0.5,
            )

    def test_missing_average_grade_in_readability_after_raises_error(self):
        """Test that missing 'average_grade' key raises ValueError."""
        with pytest.raises(ValueError, match="readability_after must include"):
            instructional_suitability_score(
                original_text="Test text.",
                simplified_text="Test text.",
                readability_before={"average_grade": 5.0},
                readability_after={},  # Missing 'average_grade'
                target_grade=5.0,
                semantic_score=0.5,
            )

    def test_non_numeric_average_grade_raises_error(self):
        """Test that non-numeric average_grade raises ValueError."""
        with pytest.raises(ValueError, match="average_grade values must be numeric"):
            instructional_suitability_score(
                original_text="Test text.",
                simplified_text="Test text.",
                readability_before={"average_grade": "five"},  # Invalid: string
                readability_after={"average_grade": 5.0},
                target_grade=5.0,
                semantic_score=0.5,
            )

    def test_composite_score_weighted_correctly(self):
        """Test that composite score is weighted sum of components."""
        # Create a specific scenario where we know all components
        result = instructional_suitability_score(
            original_text="The important concept is here.",
            simplified_text="The idea is here.",
            readability_before={"average_grade": 6.0},
            readability_after={"average_grade": 5.5},
            target_grade=5.5,
            semantic_score=1.0,
        )

        # Extract components
        grade_acc = result["grade_accuracy_score"]
        semantic = result["semantic_preservation_score"]
        sentence_red = result["sentence_length_reduction_score"]
        vocab_simp = result["vocabulary_simplification_score"]

        # Compute expected composite
        expected = (
            0.35 * grade_acc
            + 0.35 * semantic
            + 0.15 * sentence_red
            + 0.15 * vocab_simp
        )

        # Compare with actual
        actual = result["instructional_suitability_score"]
        assert abs(actual - expected) < 0.001

    def test_scores_are_rounded_to_four_decimals(self):
        """Test that scores are rounded to 4 decimal places."""
        result = instructional_suitability_score(
            original_text="Original text.",
            simplified_text="Simple text.",
            readability_before={"average_grade": 5.5},
            readability_after={"average_grade": 5.0},
            target_grade=5.0,
            semantic_score=0.875,
        )

        # Check all scores have max 4 decimal places
        for key in [
            "grade_accuracy_score",
            "semantic_preservation_score",
            "sentence_length_reduction_score",
            "vocabulary_simplification_score",
            "instructional_suitability_score",
        ]:
            value = result[key]
            # Check it's a float with reasonable precision
            assert isinstance(value, float)
            # Verify no more than 4 decimal places
            decimal_places = len(str(value).split(".")[-1])
            assert decimal_places <= 4

    def test_clamps_semantic_score_to_valid_range(self):
        """Test that out-of-range semantic scores are clamped to [0, 1]."""
        # Test with score > 1.0
        result = instructional_suitability_score(
            original_text="Test.",
            simplified_text="Test.",
            readability_before={"average_grade": 5.0},
            readability_after={"average_grade": 5.0},
            target_grade=5.0,
            semantic_score=1.5,  # Out of range
        )
        assert result["semantic_preservation_score"] <= 1.0

        # Test with score < 0.0
        result = instructional_suitability_score(
            original_text="Test.",
            simplified_text="Test.",
            readability_before={"average_grade": 5.0},
            readability_after={"average_grade": 5.0},
            target_grade=5.0,
            semantic_score=-0.5,  # Out of range
        )
        assert result["semantic_preservation_score"] >= 0.0

    def test_complex_simplification_scenario(self):
        """Test with a realistic complex-to-simple simplification."""
        original = (
            "The photosynthetic process involves the conversion of solar energy "
            "into chemical energy through the oxidation-reduction reactions catalyzed "
            "by chlorophyll and associated protein complexes in the thylakoid membrane."
        )
        simplified = (
            "Plants use sunlight to make food. "
            "Green parts of leaves capture light. "
            "This energy turns into food the plant can use."
        )

        result = instructional_suitability_score(
            original_text=original,
            simplified_text=simplified,
            readability_before={"average_grade": 14.5},
            readability_after={"average_grade": 4.8},
            target_grade=5.0,
            semantic_score=0.82,
        )

        # Should be a high suitability score
        assert result["instructional_suitability_score"] > 0.6
        # Should have good semantic preservation
        assert result["semantic_preservation_score"] > 0.7
        # Should have substantial sentence reduction
        assert result["sentence_length_reduction_score"] > 0.3
        # Should have vocabulary simplification
        assert result["vocabulary_simplification_score"] > 0.3
