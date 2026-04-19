"""
Keyword Extraction Module

Extracts important keywords from text using spaCy (preferred) or NLTK fallback.
Includes keyword preservation verification for simplified/transformed text.
"""

from typing import Optional

import nltk

# Ensure NLTK data is available
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")

# Try to import spaCy for advanced extraction
try:
    import spacy

    _SPACY_AVAILABLE = True
except ImportError:
    _SPACY_AVAILABLE = False

# NLTK stopwords for fallback
try:
    from nltk.corpus import stopwords

    _STOPWORDS = set(stopwords.words("english"))
except (LookupError, ImportError):
    _STOPWORDS = set()


def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """
    Extract top keywords from text using spaCy or NLTK fallback.

    Attempts to use spaCy noun chunks (more accurate for multi-word terms)
    if available. Falls back to NLTK POS-tagging for keyword extraction.

    Args:
        text: Input text to analyze
        max_keywords: Maximum number of keywords to return (default 10)

    Returns:
        List of keywords sorted by frequency/importance.
        Returns empty list if extraction fails.

    Examples:
        >>> extract_keywords("Photosynthesis converts solar energy...")
        ['photosynthesis', 'solar energy', 'light', 'glucose', 'oxygen']
    """
    if not text or not text.strip():
        return []

    try:
        # Try spaCy first (better for multi-word terms)
        if _SPACY_AVAILABLE:
            return _extract_with_spacy(text, max_keywords)
        else:
            # Fall back to NLTK
            return _extract_with_nltk(text, max_keywords)
    except Exception:
        # Graceful degradation - return empty list on any error
        return []


def _extract_with_spacy(text: str, max_keywords: int) -> list[str]:
    """
    Extract keywords using spaCy noun chunks.

    Handles multi-word phrases (e.g., "mitochondrial membrane").

    Args:
        text: Input text
        max_keywords: Maximum keywords to return

    Returns:
        List of keywords from noun chunks
    """
    try:
        # Try to load model (will download on first use if needed)
        nlp = spacy.load("en_core_web_sm")
    except (OSError, ImportError):
        # Model not available, fall back to NLTK
        return _extract_with_nltk(text, max_keywords)

    doc = nlp(text)

    # Extract noun chunks
    keywords = set()
    for chunk in doc.noun_chunks:
        text_lower = chunk.text.lower().strip()
        # Filter: min 3 characters, not pure stopwords
        if len(text_lower) >= 3 and not text_lower.isspace():
            keywords.add(text_lower)

    # Also extract single nouns for better coverage
    for token in doc:
        if token.pos_ == "NOUN" and len(token.text) >= 3:
            keywords.add(token.text.lower())

    # Sort by frequency in text (simple heuristic)
    keyword_list = list(keywords)
    keyword_list.sort(key=lambda w: text.lower().count(w), reverse=True)

    return keyword_list[:max_keywords]


def _extract_with_nltk(text: str, max_keywords: int) -> list[str]:
    """
    Extract keywords using NLTK POS-tagging.

    Falls back to when spaCy is unavailable. Extracts nouns
    and filters by stopwords and length.

    Args:
        text: Input text
        max_keywords: Maximum keywords to return

    Returns:
        List of keywords extracted via POS-tagging
    """
    from nltk import pos_tag, word_tokenize

    try:
        tokens = word_tokenize(text.lower())
        pos_tags = pos_tag(tokens)

        # Extract nouns (NN, NNS, NNP, NNPS)
        keywords = set()
        for word, pos in pos_tags:
            if pos in ("NN", "NNS", "NNP", "NNPS"):
                # Filter: min 3 chars, not a stopword
                if len(word) >= 3 and word not in _STOPWORDS:
                    keywords.add(word)

        # Sort by frequency
        keyword_list = list(keywords)
        keyword_list.sort(key=lambda w: text.lower().count(w), reverse=True)

        return keyword_list[:max_keywords]
    except Exception:
        return []


def count_preserved_keywords(
    original_keywords: list[str], simplified_text: str
) -> list[str]:
    """
    Check which original keywords are preserved in simplified text.

    Uses case-insensitive substring matching to verify keyword presence
    in the simplified/transformed text.

    Args:
        original_keywords: Keywords extracted from original text
        simplified_text: The simplified or transformed text

    Returns:
        Subset of original_keywords found in simplified_text.
        Empty list if no keywords preserved or keywords list was empty.

    Examples:
        >>> original = ["photosynthesis", "glucose", "sunlight"]
        >>> simplified = "Plants make glucose using sunlight..."
        >>> count_preserved_keywords(original, simplified)
        ['glucose', 'sunlight']  # 'photosynthesis' not found
    """
    if not original_keywords or not simplified_text:
        return []

    simplified_lower = simplified_text.lower()
    preserved = []

    for keyword in original_keywords:
        keyword_lower = keyword.lower()
        # Case-insensitive substring matching
        # Note: This is a simple match; could be enhanced with word boundaries
        if keyword_lower in simplified_lower:
            preserved.append(keyword)

    return preserved
