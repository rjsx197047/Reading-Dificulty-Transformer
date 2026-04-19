"""
Semantic preservation scoring module.

Measures whether a simplified text preserves the meaning of the original
using sentence embeddings and cosine similarity.

Model: sentence-transformers `all-MiniLM-L6-v2` (small, fast, local).
Similarity: sklearn.metrics.pairwise.cosine_similarity.

Graceful fallback: if sentence-transformers or the model cannot be loaded,
`semantic_preservation_score()` returns None so callers can omit the field
from structured output instead of crashing.

Import:
    from app.core.semantic_similarity import semantic_preservation_score
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy model loading with graceful fallback
# ---------------------------------------------------------------------------
_model = None
_model_init_attempted = False
_available = False

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
    _imports_ok = True
except ImportError as e:
    logger.info("semantic_similarity disabled — missing dependency: %s", e)
    _imports_ok = False


def _load_model():
    """
    Lazily load the SentenceTransformer model on first use.

    Runs exactly once per process. If loading fails (network error, corrupted
    cache, incompatible numpy build, etc.), _available stays False and all
    subsequent calls return None without retrying.
    """
    global _model, _model_init_attempted, _available

    if _model_init_attempted:
        return _model

    _model_init_attempted = True

    if not _imports_ok:
        return None

    try:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _available = True
        logger.info("semantic_similarity: model loaded (all-MiniLM-L6-v2)")
    except Exception as e:
        logger.warning("semantic_similarity: failed to load model — %s", e)
        _model = None
        _available = False

    return _model


def semantic_preservation_score(
    original_text: str,
    simplified_text: str,
) -> float | None:
    """
    Compute the semantic preservation score between two texts.

    Uses sentence-transformers `all-MiniLM-L6-v2` to embed both texts and
    sklearn's cosine_similarity to measure how closely their meanings align.

    Parameters
    ----------
    original_text : str
        The source text before simplification.
    simplified_text : str
        The text produced by the simplification pipeline.

    Returns
    -------
    float | None
        A score in [0.0, 1.0] where:
          * 1.0 means identical meaning
          * 0.0 means unrelated meaning
        Returns None if the embeddings model is unavailable (e.g.
        sentence-transformers not installed) so callers can fall back
        gracefully instead of crashing.

    Examples
    --------
    >>> semantic_preservation_score(
    ...     "This assignment requires students to analyze the causes of "
    ...     "the American Revolution.",
    ...     "Students must study why the American Revolution happened.",
    ... )
    0.87  # approximate — exact value depends on model version
    """
    if not original_text or not simplified_text:
        return None

    model = _load_model()
    if model is None:
        return None

    try:
        # Truncate to avoid very large inputs blowing up the encoder
        a = original_text[:4000]
        b = simplified_text[:4000]

        embeddings = model.encode([a, b], convert_to_numpy=True)
        original_embedding = embeddings[0].reshape(1, -1)
        simplified_embedding = embeddings[1].reshape(1, -1)

        similarity_matrix = cosine_similarity(original_embedding, simplified_embedding)
        score = float(similarity_matrix[0][0])

        # Clamp to [0, 1] — cosine can drift slightly out of range on
        # near-identical texts due to floating-point error.
        return round(max(0.0, min(1.0, score)), 4)

    except Exception as e:
        logger.warning("semantic_preservation_score: computation failed — %s", e)
        return None


def compute_semantic_similarity(
    original_text: str,
    transformed_text: str,
) -> float | None:
    """
    Compute semantic similarity between original and transformed text.

    Public wrapper around semantic_preservation_score() for use in transform
    and other endpoints. Measures meaning preservation using sentence embeddings
    and cosine similarity.

    Parameters
    ----------
    original_text : str
        The source text before transformation.
    transformed_text : str
        The text after transformation or simplification.

    Returns
    -------
    float | None
        A similarity score in [0.0, 1.0] where:
          * 1.0 = identical or nearly identical meaning
          * 0.5 = moderate semantic overlap
          * 0.0 = unrelated meaning
        Returns None if the embeddings model is unavailable.

    Examples
    --------
    >>> score = compute_semantic_similarity(
    ...     "Photosynthesis converts solar energy into chemical energy.",
    ...     "Plants turn sunlight into food."
    ... )
    >>> print(f"Semantic similarity: {score}")  # e.g., 0.82
    """
    return semantic_preservation_score(original_text, transformed_text)


def is_available() -> bool:
    """Return True if the semantic scoring model is loaded and usable."""
    _load_model()
    return _available
