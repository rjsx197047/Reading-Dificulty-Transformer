"""
Text simplification utilities.

Handles vocabulary replacement, keyword extraction/preservation,
sentence chunking (dyslexia mode), and dyslexia-friendly formatting.
These pre/post-processing steps run around the LLM rewrite step.
"""

import re

import nltk

# Download required NLTK data silently if missing
for _pkg in ("averaged_perceptron_tagger_eng", "punkt_tab", "stopwords"):
    try:
        nltk.data.find(f"taggers/{_pkg}" if "tagger" in _pkg else f"tokenizers/{_pkg}" if "punkt" in _pkg else f"corpora/{_pkg}")
    except LookupError:
        nltk.download(_pkg, quiet=True)

from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

# ---------------------------------------------------------------------------
# Vocabulary replacement dictionary
# ---------------------------------------------------------------------------
VOCAB_REPLACEMENTS: dict[str, str] = {
    "approximately": "about",
    "utilize": "use",
    "utilise": "use",
    "utilization": "use",
    "utilisation": "use",
    "commence": "start",
    "commencement": "start",
    "demonstrate": "show",
    "demonstrated": "showed",
    "demonstrates": "shows",
    "demonstrating": "showing",
    "subsequently": "then",
    "consequently": "so",
    "nevertheless": "still",
    "notwithstanding": "despite",
    "furthermore": "also",
    "moreover": "also",
    "however": "but",
    "therefore": "so",
    "thus": "so",
    "hence": "so",
    "henceforth": "from now on",
    "albeit": "though",
    "endeavor": "try",
    "endeavour": "try",
    "facilitate": "help",
    "implementation": "use",
    "implement": "use",
    "methodology": "method",
    "methodologies": "methods",
    "objective": "goal",
    "objectives": "goals",
    "numerous": "many",
    "sufficient": "enough",
    "insufficient": "not enough",
    "optimal": "best",
    "optimum": "best",
    "terminate": "end",
    "termination": "end",
    "initiate": "start",
    "initiation": "start",
    "magnitude": "size",
    "obtain": "get",
    "obtained": "got",
    "require": "need",
    "requires": "needs",
    "required": "needed",
    "requirement": "need",
    "requirements": "needs",
    "indicate": "show",
    "indicates": "shows",
    "indicated": "showed",
    "indicating": "showing",
    "comprise": "include",
    "comprises": "includes",
    "comprised": "included",
    "consisting": "made up of",
    "consists": "is made up of",
    "possess": "have",
    "possesses": "has",
    "assistance": "help",
    "assist": "help",
    "assists": "helps",
    "assisted": "helped",
    "acquire": "get",
    "acquires": "gets",
    "acquired": "got",
    "prior to": "before",
    "subsequent to": "after",
    "in order to": "to",
    "due to the fact that": "because",
    "in the event that": "if",
    "at this point in time": "now",
    "in spite of": "despite",
}

# STEM vocabulary that should never be replaced
PROTECTED_STEM_TERMS: set[str] = {
    "photosynthesis", "mitochondria", "chromosome", "molecule", "atom",
    "neutron", "proton", "electron", "osmosis", "diffusion", "respiration",
    "metabolism", "ecosystem", "hypothesis", "theorem", "algorithm",
    "polynomial", "derivative", "integral", "equation", "coefficient",
    "denominator", "numerator", "perpendicular", "circumference", "diameter",
    "radius", "perimeter", "parallelogram", "trapezoid", "quadrilateral",
    "photon", "wavelength", "frequency", "amplitude", "velocity",
    "acceleration", "momentum", "kinetic", "potential", "gravitational",
    "electromagnetic", "microorganism", "bacteria", "virus", "fungi",
    "nucleus", "cytoplasm", "membrane", "chloroplast", "ribosome",
    "deoxyribonucleic", "ribonucleic", "adenine", "thymine", "guanine",
    "cytosine", "allele", "genotype", "phenotype", "mutation", "evolution",
    "democracy", "constitution", "legislature", "judiciary", "sovereignty",
    "metaphor", "simile", "alliteration", "onomatopoeia", "protagonist",
    "antagonist", "narrative", "exposition", "resolution",
}


def apply_vocab_replacements(text: str) -> str:
    """
    Replace complex words with simpler synonyms using the replacement dictionary.
    Skips words that are STEM protected terms.
    Replacements are case-preserving for the first letter.
    """
    # Sort by length descending so multi-word phrases match before single words
    sorted_phrases = sorted(VOCAB_REPLACEMENTS.keys(), key=len, reverse=True)

    for phrase in sorted_phrases:
        replacement = VOCAB_REPLACEMENTS[phrase]
        # Skip if any word in the phrase is a protected STEM term
        if any(w.lower() in PROTECTED_STEM_TERMS for w in phrase.split()):
            continue

        # Case-insensitive whole-word replacement
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)

        def _replace(m: re.Match) -> str:
            matched = m.group(0)
            if matched[0].isupper():
                return replacement.capitalize()
            return replacement

        text = pattern.sub(_replace, text)

    return text


def extract_keywords(text: str) -> list[str]:
    """
    Extract key nouns and technical terms from the text that should be
    preserved during rewriting. Returns a deduplicated list of keywords.
    """
    try:
        tokens = word_tokenize(text)
        tagged = nltk.pos_tag(tokens)
        stop = set(stopwords.words("english"))

        keywords: list[str] = []
        for word, tag in tagged:
            word_lower = word.lower()
            # Keep nouns (NN, NNS, NNP, NNPS) that aren't stopwords
            if tag.startswith("NN") and word_lower not in stop and len(word) > 3:
                keywords.append(word_lower)
            # Always keep protected STEM terms
            if word_lower in PROTECTED_STEM_TERMS:
                if word_lower not in keywords:
                    keywords.append(word_lower)

        # Deduplicate preserving order
        seen: set[str] = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)

        return unique[:30]  # Cap at 30 to keep prompts manageable

    except Exception:
        return []


def apply_chunking(text: str, max_words: int = 15) -> str:
    """
    Dyslexia Support Mode: split long sentences into shorter readable segments.
    Sentences longer than max_words are broken at natural conjunction/clause points.
    Returns text with double newlines between chunks for clear visual separation.
    """
    try:
        sentences = sent_tokenize(text)
    except Exception:
        sentences = text.split(". ")

    chunks: list[str] = []

    for sentence in sentences:
        words = sentence.split()
        if len(words) <= max_words:
            chunks.append(sentence.strip())
            continue

        # Try to split at conjunctions / relative pronouns
        split_pattern = re.compile(
            r"\b(because|although|however|therefore|which|that|who|when|where"
            r"|while|but|and|or|so|since|unless|until|though|if)\b",
            re.IGNORECASE,
        )

        parts = split_pattern.split(sentence)
        current = ""
        sub_chunks: list[str] = []

        i = 0
        while i < len(parts):
            part = parts[i]
            connector = parts[i + 1] if i + 1 < len(parts) else ""
            i += 2 if connector else 1

            candidate = (current + " " + part).strip()
            candidate_with_connector = (candidate + " " + connector).strip()

            if len(candidate_with_connector.split()) > max_words and current:
                sub_chunks.append(current.strip().rstrip(","))
                current = connector + " " + part if connector else part
            else:
                current = candidate_with_connector

        if current.strip():
            sub_chunks.append(current.strip().rstrip(","))

        # Fallback: just hard-split on max_words if no connectors found
        if not sub_chunks or (len(sub_chunks) == 1 and len(sub_chunks[0].split()) > max_words):
            sub_chunks = []
            for j in range(0, len(words), max_words):
                sub_chunks.append(" ".join(words[j : j + max_words]))

        chunks.extend(sub_chunks)

    return "\n\n".join(c for c in chunks if c)


def apply_dyslexia_formatting(text: str) -> str:
    """
    Format text for dyslexia-friendly reading:
    - Short paragraphs (max 3 sentences each)
    - Extra line breaks between clauses
    - Each sentence on its own line
    """
    try:
        sentences = sent_tokenize(text)
    except Exception:
        sentences = text.split(". ")

    formatted_paragraphs: list[str] = []
    chunk_size = 3  # sentences per paragraph

    for i in range(0, len(sentences), chunk_size):
        group = sentences[i : i + chunk_size]
        para = "\n".join(s.strip() for s in group if s.strip())
        formatted_paragraphs.append(para)

    return "\n\n".join(formatted_paragraphs)


def build_simplify_prompt(
    text: str,
    target_grade: float,
    keywords: list[str],
    preserve_keywords: bool,
    mode: str,
    instruction_mode: bool,
    chunking: bool,
) -> str:
    """Build the LLM prompt for text simplification based on active options."""
    grade_descriptions = {
        range(1, 4): "a 1st-3rd grader (ages 6-9). Use very simple words and very short sentences.",
        range(4, 6): "a 4th-5th grader (ages 9-11). Use simple words and short sentences.",
        range(6, 9): "a 6th-8th grader (ages 11-14). Use clear language and moderate sentence length.",
        range(9, 13): "a 9th-12th grader (ages 14-18). Use standard vocabulary.",
        range(13, 17): "a college student. Use precise academic language while remaining clear.",
    }

    audience = f"a Grade {target_grade:.0f} student"
    for grade_range, description in grade_descriptions.items():
        if int(target_grade) in grade_range:
            audience = description
            break

    rules: list[str] = [
        "1. Preserve ALL factual information and key ideas — do not omit anything.",
        f"2. Rewrite for {audience}.",
        "3. Output ONLY the rewritten text — no explanations, headers, or notes.",
        "4. Shorten sentences to under 20 words each.",
        "5. Replace complex vocabulary with simpler synonyms.",
        "6. Convert passive voice to active voice wherever possible.",
        "7. Remove nested clauses — break them into separate sentences.",
    ]

    if preserve_keywords and keywords:
        kw_list = ", ".join(keywords[:20])
        rules.append(
            f"8. PRESERVE these keywords exactly as written (do not replace them): {kw_list}"
        )

    if mode == "esl":
        rules.append(
            "9. ESL MODE: Use the simplest possible grammar. Avoid idioms and phrasal verbs. "
            "Prefer SVO (Subject-Verb-Object) sentence structure. No nested clauses."
        )

    if instruction_mode:
        rules.append(
            "10. INSTRUCTION MODE: This text contains homework instructions. "
            "Convert them into numbered steps. Each step should start with an action verb. "
            "Keep each step to one sentence."
        )

    if chunking:
        rules.append(
            "11. CHUNKING MODE: Write every sentence as its own short paragraph. "
            "Put a blank line between each sentence."
        )

    rules_text = "\n".join(rules)

    return f"""You are an expert reading-level adapter for educators and students.

Rules:
{rules_text}

Original text:
---
{text[:4000]}
---

Rewritten text:"""
