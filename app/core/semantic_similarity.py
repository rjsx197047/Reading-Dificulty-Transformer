"""
Semantic preservation scoring module.

Measures whether a simplified text preserves the meaning of the original
using sentence embeddings and cosine similarity.

Model: sentence-transformers `all-MiniLM-L6-v2` (small, fast, local).
Similarity: sklearn.metrics.pairwise.cosine_similarity (with sentence-transformers util.cos_sim fallback).

Model is loaded eagerly at startup via preload_model() (called from main.py),
with lazy loading fallback for test/import scenarios.

Import:
    from app.core.semantic_similarity import (
        semantic_preservation_score,
        compute_semantic_similarity,
        preload_model,
    )
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model loading with graceful fallback
# ---------------------------------------------------------------------------
_model = None
_model_init_attempted = False
_available = False
_use_sklearn = True  # Track whether to use sklearn or fall back to built-in cos_sim

try:
    from sentence_transformers import SentenceTransformer, util  # type: ignore
    _st_imports_ok = True
except ImportError as e:
    logger.warning("semantic_similarity: sentence_transformers not installed — %s", e)
    _st_imports_ok = False

try:
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
    _sklearn_ok = True
except ImportError as e:
    logger.info("semantic_similarity: sklearn unavailable, will use built-in cos_sim — %s", e)
    _sklearn_ok = False

_imports_ok = _st_imports_ok  # Minimum requirement is sentence-transformers


def preload_model() -> bool:
    """
    Eagerly load the SentenceTransformer model at application startup.

    Should be called once during FastAPI startup to avoid the first-request
    latency of model loading. Safe to call multiple times — only loads once.

    Returns
    -------
    bool
        True if model loaded successfully, False otherwise.
    """
    global _model, _model_init_attempted, _available

    if _model_init_attempted:
        return _available

    _model_init_attempted = True

    if not _imports_ok:
        logger.warning("semantic_similarity: cannot load model — sentence_transformers missing")
        return False

    try:
        logger.info("semantic_similarity: loading model all-MiniLM-L6-v2 at startup...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _available = True
        logger.info("semantic_similarity: model loaded successfully (all-MiniLM-L6-v2)")
        return True
    except Exception as e:
        logger.warning("semantic_similarity: failed to load model — %s", e)
        _model = None
        _available = False
        return False


def _load_model():
    """
    Lazily load the SentenceTransformer model on first use.

    Fallback if preload_model() wasn't called at startup. Runs exactly
    once per process.
    """
    if not _model_init_attempted:
        preload_model()
    return _model


def semantic_preservation_score(
    original_text: str,
    simplified_text: str,
) -> float | None:
    """
    Compute the semantic preservation score between two texts.

    Uses sentence-transformers `all-MiniLM-L6-v2` to embed both texts and
    cosine similarity (sklearn or built-in) to measure alignment.

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
        Returns None if the embeddings model is unavailable.
    """
    if not original_text or not simplified_text:
        return None

    model = _load_model()
    if model is None:
        logger.warning("semantic_preservation_score: model unavailable")
        return None

    try:
        # Truncate to avoid very large inputs blowing up the encoder
        a = original_text[:4000]
        b = simplified_text[:4000]

        # Encode to numpy arrays
        embeddings = model.encode([a, b], convert_to_numpy=True)

        # Compute cosine similarity — try sklearn first, fall back to util.cos_sim
        if _sklearn_ok:
            try:
                original_embedding = embeddings[0].reshape(1, -1)
                simplified_embedding = embeddings[1].reshape(1, -1)
                similarity_matrix = cosine_similarity(original_embedding, simplified_embedding)
                score = float(similarity_matrix[0][0])
            except Exception as e:
                logger.info("sklearn cosine_similarity failed, falling back to util.cos_sim: %s", e)
                score = float(util.cos_sim(embeddings[0], embeddings[1]).item())
        else:
            # Use sentence-transformers' built-in cos_sim
            score = float(util.cos_sim(embeddings[0], embeddings[1]).item())

        # Clamp to [0, 1]
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
