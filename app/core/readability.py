"""
Core readability detection module.

Provides detect_readability(text) as the single entry point for computing
a focused set of grade-level formulas and an average grade estimate.

This module is intentionally thin — it delegates to textstat and returns
a plain ReadabilityDetection dataclass. The existing services/readability.py
remains unchanged and continues to own the broader scoring/classification
pipeline used by /analyze.
"""

from dataclasses import dataclass

import textstat


@dataclass
class ReadabilityDetection:
    """
    Focused readability snapshot used to bracket the simplification pipeline.

    Fields
    ------
    flesch_kincaid : float
        Flesch-Kincaid Grade Level — most widely used US grade estimate.
    coleman_liau : float
        Coleman-Liau Index — character-based formula, good complement to FK.
    smog : float
        SMOG Index — designed for health/medical materials; reliable on
        shorter passages.
    ari : float
        Automated Readability Index — character + word count based.
    average_grade : float
        Simple mean of the four formula scores above, rounded to 2 dp.
        Used as a single comparable number across pipeline stages.
    """

    flesch_kincaid: float
    coleman_liau: float
    smog: float
    ari: float
    average_grade: float


def detect_readability(text: str) -> ReadabilityDetection:
    """
    Compute a focused set of grade-level readability scores for *text*.

    Returns a ReadabilityDetection with four formula scores and their mean.
    All values are rounded to 2 decimal places. Grade scores are clamped to
    a minimum of 0 so negative outputs from short texts don't propagate.

    Parameters
    ----------
    text : str
        The input text. Works best with at least 3 sentences; shorter
        passages may produce unreliable SMOG scores.
    """
    fk = round(max(textstat.flesch_kincaid_grade(text), 0.0), 2)
    cl = round(max(textstat.coleman_liau_index(text), 0.0), 2)
    sm = round(max(textstat.smog_index(text), 0.0), 2)
    ar = round(max(textstat.automated_readability_index(text), 0.0), 2)

    avg = round((fk + cl + sm + ar) / 4, 2)

    return ReadabilityDetection(
        flesch_kincaid=fk,
        coleman_liau=cl,
        smog=sm,
        ari=ar,
        average_grade=avg,
    )
