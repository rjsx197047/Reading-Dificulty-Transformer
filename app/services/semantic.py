"""
Semantic similarity scoring using sentence-transformers.

Computes cosine similarity between original and simplified text
to verify meaning is preserved during rewriting.

sentence-transformers is an optional dependency. If not installed,
all functions return None and the field is omitted from responses.
"""

from __future__ import annotations

_model = None
_model_loaded = False
_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    _AVAILABLE = True
except ImportError:
    pass


def _get_model():
    global _model, _model_loaded
    if not _model_loaded:
        _model_loaded = True
        if _AVAILABLE:
            try:
                # Small, fast model — good for local-first deployment
                _model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                _model = None
    return _model


def compute_similarity(text_a: str, text_b: str) -> float | None:
    """
    Compute cosine similarity between two texts using sentence embeddings.

    Returns a float in [0, 1] where 1.0 = identical meaning,
    or None if sentence-transformers is not available.
    """
    if not _AVAILABLE:
        return None

    model = _get_model()
    if model is None:
        return None

    try:
        import numpy as np

        embeddings = model.encode([text_a[:2000], text_b[:2000]], convert_to_numpy=True)
        a, b = embeddings[0], embeddings[1]

        # Cosine similarity
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return None

        similarity = float(np.dot(a, b) / (norm_a * norm_b))
        return round(max(0.0, min(1.0, similarity)), 4)

    except Exception:
        return None


def is_available() -> bool:
    """Return True if sentence-transformers is installed and the model loaded."""
    return _AVAILABLE
