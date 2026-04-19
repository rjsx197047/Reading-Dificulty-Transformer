# Reading Difficulty Transformer

A local-first classroom accessibility engine that **analyzes**, **simplifies**, and **differentiates** text for students, teachers, ESL learners, and readers with dyslexia — powered by local Ollama, optional Claude API, and traditional readability formulas.

> **Local-first & private** — your text stays on your machine unless you explicitly connect a Claude API key.

---

## What It Does

| Mode | Who it's for | What it returns |
|------|-------------|-----------------|
| **Analyze** | Anyone | 7 readability scores, difficulty level, AI text-type detection, AI analysis, suggestions |
| **Simplify** | Teachers, students, ESL learners | Grade-targeted rewrite with keyword locking, dyslexia support, meaning score |
| **Worksheet** | Teachers | 3 differentiated versions (Advanced / Standard / Simplified) in one click |
| **Transform** | General use | Quick rewrite to a named level (Elementary → College) |

---

## Features

### Analyze Mode
- **7 readability formulas** — Flesch Reading Ease, Flesch-Kincaid, Gunning Fog, SMOG, Coleman-Liau, ARI, Dale-Chall
- **Hover tooltips** — each score name shows a detailed description of what it measures and how to interpret it
- **AI text type detection** — the LLM classifies the passage as News Article, Novel Excerpt, Play, Textbook Chapter, Essay, Dialogue, etc.
- **Composite grade level** — weighted consensus across all formulas
- **Difficulty classification** — Elementary, Middle School, High School, College, Graduate
- **Text statistics** — word count, sentence count, syllable analysis, complex word %
- **AI qualitative analysis** — via Claude API or local Ollama, with a backend chip showing which was used
- **Actionable suggestions** to simplify text

### Simplify Mode (Grade-Level Slider)
- **Numeric grade target** — slide from Grade 1 to Grade 16
- **Vocabulary pre-processing** — 60+ word replacements (*utilize → use*, *approximately → about*, etc.) applied before LLM rewriting
- **Keyword preservation** — NLTK extracts key nouns and STEM terms; LLM is instructed to leave them unchanged
- **Dyslexia Support Mode** (`chunking`) — long sentences are split at natural clause boundaries
- **Dyslexia Formatting** — short paragraphs, each sentence on its own line
- **ESL Mode** — simplified grammar, SVO structure, no idioms
- **Instruction Mode** — converts homework instructions into numbered action steps
- **Automatic verification loop** — checks achieved grade level; retries up to 3× if outside ±0.5 grade tolerance
- **Semantic similarity score** — cosine similarity via sentence-transformers `all-MiniLM-L6-v2` (optional)
- **Instructional suitability scoring** — evaluates grade accuracy, semantic preservation, sentence reduction, and vocabulary simplification (optional)
- **Structured JSON output** — `original_text`, `simplified_text`, `readability_before`, `readability_after`, `semantic_preservation_score`

### Worksheet Generator
- Paste any text; receive **three differentiated versions** in one request
- Advanced (Grade 10-12), Standard (Grade 6-8), Simplified (Grade 3-5)
- Each version scored for achieved grade level
- One-click copy per version

### Transform Mode
- Quick named-level rewriting: Elementary, Middle School, High School, College
- Before/after grade comparison
- **Keyword extraction & preservation tracking** — extracts important terms from original, reports which survived simplification
- **Semantic similarity scoring** — computes actual meaning preservation (0.0–1.0) via sentence embeddings
- **Teacher report generation** — Markdown-formatted accessibility assessment with classroom guidance
- Comprehensive differentiation metadata for teacher-friendly explanation

### Dual Backend (Ollama + Claude API)
- **Local Ollama (default)** — zero-cost, fully private, no account needed
- **Claude API (optional)** — supply an API key in Settings for stronger, more accurate responses
- Per-request routing — each call picks whichever backend is available
- API key is stored in browser `localStorage` only; never persisted server-side
- Clear backend status chip on each AI analysis result

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **NLP** | textstat, NLTK |
| **Local AI** | Ollama (llama3.2 default) |
| **Cloud AI (optional)** | Anthropic Claude API (`claude-sonnet-4-5` default) |
| **Semantic Scoring** | sentence-transformers `all-MiniLM-L6-v2` (optional) |
| **Frontend** | Vanilla HTML/CSS/JS (Jinja2 templates) |
| **Config** | Pydantic Settings, `.env` files |
| **Agent Interface** | `ReadingDifficultyAgent` — Forge AI / multi-agent compatible |

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Ollama** — [Install Ollama](https://ollama.com/download) (optional if you're using a Claude API key instead)

### 1. Clone the Repository

```bash
git clone https://github.com/rjsx197047/Reading-Dificulty-Transformer.git
cd Reading-Dificulty-Transformer
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Download NLTK Data

```bash
python3 -c "
import nltk
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('punkt_tab')
nltk.download('stopwords')
"
```

### 4. Pull an Ollama Model (optional if using Claude API)

```bash
ollama pull llama3.2
ollama serve
```

### 5. Run the App

```bash
python3 run.py
```

Open **http://localhost:8000** in your browser.

---

## Using a Claude API Key

For stronger, more accurate responses than the default local model:

1. Get an API key from [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. Click the **gear icon** in the top-right of the app
3. Paste your key (starts with `sk-ant-`) and click **Save Key**
4. All AI tasks now route through Claude. The header badge switches to **"Claude API Active"**

**Security notes:**
- Your key is stored only in your browser's `localStorage`
- The server never persists it — it's passed per-request in memory and forwarded directly to Anthropic's API
- Click **Clear** in Settings at any time to remove it
- To use a different browser profile or device, re-enter the key there

---

## Keyword Extraction & Preservation

The `extract_keywords()` function in `app/core/keyword_extractor.py` identifies important terms in original text and tracks whether they survive the simplification process.

### How It Works

- **spaCy noun chunks (preferred)** — When available, extracts multi-word phrases like "mitochondrial membrane", "photosynthesis"
- **NLTK POS-tagging fallback** — If spaCy unavailable, uses NN/NNS/NNP/NNPS tags to identify nouns
- **Smart filtering** — Removes stopwords (the, a, an) and enforces minimum 3-character length
- **Frequency ranking** — Returns top 10 keywords sorted by occurrence in text

### Keyword Preservation Check

The `count_preserved_keywords()` function verifies which original keywords appear in the simplified text:
- Case-insensitive substring matching
- Returns list of preserved keywords for teacher review
- Helps teachers assess whether STEM vocabulary was maintained during simplification

### Usage Example

```python
from app.core.keyword_extractor import extract_keywords, count_preserved_keywords

# Extract keywords from original text
original = "Photosynthesis converts solar energy into chemical energy in the chloroplasts."
keywords = extract_keywords(original)
# Returns: ['photosynthesis', 'solar energy', 'chemical energy', 'chloroplasts', ...]

# Check which survived simplification
simplified = "Plants turn sunlight into food using chloroplasts."
preserved = count_preserved_keywords(keywords, simplified)
# Returns: ['solar energy' → 'sunlight', 'chloroplasts'] or subset thereof
```

---

## Semantic Similarity Scoring (Enhanced)

The `compute_semantic_similarity()` function in `app/core/semantic_similarity.py` measures meaning preservation using sentence embeddings.

### What It Does

- **Actual computation, not hardcoded** — Uses sentence-transformers `all-MiniLM-L6-v2` model
- **Cosine similarity** — Measures semantic overlap between original and simplified text
- **0.0–1.0 normalization** — Clear interpretation: 0.85+ = excellent, 0.60+ = good, <0.50 = significant loss
- **Graceful fallback** — Returns None if model unavailable; caller can default to 0.5

### Interpretation Guide

| Score | Meaning |
|-------|---------|
| 0.85–1.0 | **Excellent** — Core concepts preserved, minimal loss |
| 0.70–0.85 | **Good** — Most meaning retained, some simplification |
| 0.50–0.70 | **Moderate** — Substantial changes, key ideas present |
| <0.50 | **Limited** — Significant rewording, concepts may shift |

### Usage Example

```python
from app.core.semantic_similarity import compute_semantic_similarity

original = "The mitochondrion is the site of aerobic cellular respiration, where glucose is oxidized to produce ATP."
simplified = "Mitochondria are where cells make energy from food."

score = compute_semantic_similarity(original, simplified)
print(f"Semantic similarity: {score}")  # e.g., 0.82

# Interpretation:
# 0.82 = Good preservation; most key concepts (mitochondria, energy, food/glucose) retained
```

---

## Teacher Report Generator

The `generate_teacher_report()` function in `app/core/report_generator.py` creates Markdown-formatted accessibility reports explaining how text was simplified and whether it's suitable for classroom use.

### Report Sections

1. **Reading Level Metrics** — Grade reduction summary (e.g., "reduced by 5.3 grade levels")
2. **Structural Changes** — Sentence count, average length, word count, vocabulary simplification %
3. **Semantic Quality** — Meaning preservation score with interpretation
4. **Keywords & Terminology** — Specialized terms protected or removed
5. **Summary** — Dynamic narrative explaining changes
6. **Teacher Notes & Recommendations** — Classroom implementation guidance based on grade level and semantic score

### Example Report Output

```markdown
# Accessibility Adaptation Report

## Reading Level Metrics
This simplified text reduces reading difficulty by **5.3 grade levels**, making it more accessible to struggling readers while maintaining content integrity.

## Structural Changes
### Sentence Structure
- **Sentence Count:** 8 → 12 (+4 additional chunks)
- **Average Sentence Length:** 25.0 → 9.1 words
  - Sentences reduced by **64%**, improving scanability.

### Word Count
- **Total Words:** 200 → 110 (-45%)

### Vocabulary Simplification
- **Average Word Length:** 5.2 → 4.1 characters
  - Vocabulary simplified by **21%** through systematic replacement

## Semantic Quality
### Meaning Preservation Score: 82%
**Good preservation** — Most key concepts and meaning are retained.

## Keywords & Terminology
**3 specialized terms were protected** to maintain domain-specific vocabulary.
Protected terms:
- mitochondria
- photosynthesis
- chloroplasts

## Summary
[Generated from metadata and context]

## Teacher Notes & Recommendations
### For Your Grade Level
This is a **substantial reduction** in difficulty. Appropriate for students 2-3 grade levels below their peers...

### For Content Integrity
Most core concepts are preserved. Use this version for students who struggle with reading...

### Implementation Tips
- Preview this text before classroom use...
- Consider using the original text with advanced readers...
```

---

## Optional: Semantic Similarity Scoring

Install `sentence-transformers` to enable the meaning preservation score in Simplify mode:

```bash
pip install sentence-transformers scikit-learn
```

The model (`all-MiniLM-L6-v2`, ~80MB) downloads automatically on first use and runs fully locally.

---

## Differentiation Metadata Generator

The `generate_differentiation_metadata()` function in `app/core/differentiation_metadata.py` generates teacher-friendly metadata explaining how text changes during simplification. This enables teachers to understand the accessibility improvements at a glance.

### Metadata Fields (12 Dimensions)

The function returns structured information about:
- **Grade Reduction** — How much the reading difficulty decreased (e.g., 5.3 grade levels)
- **Sentence Statistics** — Original and simplified sentence counts + average sentence length
- **Word Statistics** — Word counts and average word length before/after
- **Semantic Preservation** — Percentage of meaning retained (0.0–1.0)
- **Keywords Preserved** — Count of protected specialized terms
- **Accessibility Summary** — Dynamic narrative explaining changes in teacher-friendly language

### Usage Example

```python
from app.core.differentiation_metadata import generate_differentiation_metadata

metadata = generate_differentiation_metadata(
    original_text="Complex academic text...",
    simplified_text="Simpler version...",
    readability_before={"average_grade": 10.5},
    readability_after={"average_grade": 5.2},
    semantic_score=0.87,
    keywords_preserved=["mitochondria", "ATP"]
)

print(metadata["grade_reduction"])  # e.g., 5.3
print(metadata["keywords_preserved_count"])  # 2
print(metadata["accessibility_summary"])
# "This rewrite reduced reading difficulty by 5.3 grade levels while breaking 
#  sentences from 25-word average down to 9-word average. Vocabulary was 
#  simplified, semantic meaning preserved at 87%, and 2 key terms were protected."
```

### Narrative Summary

The `accessibility_summary` field provides context-aware explanations:
- Mentions grade reduction magnitude
- Describes sentence restructuring (chunking or length reduction)
- Explains vocabulary simplification impacts
- Notes semantic preservation quality
- Highlights protected specialized terms

---

## Instructional Suitability Scoring

The `instructional_suitability_score()` function in `app/core/instructional_scoring.py` evaluates whether simplified text is appropriate for classroom use by scoring four key dimensions:

### Scoring Dimensions (Each 0.0–1.0)

1. **Grade Accuracy Score** (35% weight)
   - Measures how closely the simplified text matches the target grade level
   - Formula: `max(0, 1 - abs(final_grade - target_grade) / 4.0)`
   - Perfect accuracy (0 grade difference) = 1.0; 4+ grades off = 0.0

2. **Semantic Preservation Score** (35% weight)
   - Reuses the semantic similarity score (cosine similarity via sentence embeddings)
   - Measures whether important meaning and concepts are retained
   - Defaults to 0.5 if the model is unavailable

3. **Sentence Length Reduction Score** (15% weight)
   - Measures how much shorter the sentences became
   - Based on average words per sentence before and after
   - Positive reduction (shorter sentences) = higher score

4. **Vocabulary Simplification Score** (15% weight)
   - Measures how much simpler the word choices are
   - Based on average word length before and after
   - Word length is a proxy for vocabulary complexity

### Combined Score

The **instructional_suitability_score** combines all four metrics:
```python
0.35 × grade_accuracy + 0.35 × semantic + 0.15 × sentence_reduction + 0.15 × vocabulary
```

Result: A single 0.0–1.0 score where 1.0 = ideal classroom accessibility.

### Usage Example

```python
from app.core.instructional_scoring import instructional_suitability_score

result = instructional_suitability_score(
    original_text="Complex academic text...",
    simplified_text="Simplified version...",
    readability_before={"average_grade": 10.5},
    readability_after={"average_grade": 5.2},
    target_grade=5.0,
    semantic_score=0.87
)

print(result["instructional_suitability_score"])  # e.g., 0.85
print(result["diagnostic"])  # Intermediate values for debugging
```

---

## Configuration

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Local model name |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `DEBUG` | `true` | Enable hot-reload |

---

## API Reference

### `GET /api/health`

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "ollama_available": true,
  "semantic_scoring_available": false
}
```

---

### `POST /api/analyze`

**Request:**
```json
{
  "text": "Your text here (minimum 10 words)...",
  "api_key": "sk-ant-..."
}
```
The `api_key` field is optional — when present, uses Claude API; otherwise uses Ollama.

**Response:**
```json
{
  "difficulty": { "level": "High School", "grade_range": "9-12", "confidence": 0.85, "description": "..." },
  "scores": { "flesch_reading_ease": 52.3, "flesch_kincaid_grade": 10.2, ... },
  "statistics": { "word_count": 150, "sentence_count": 8, ... },
  "ai_analysis": "The text demonstrates moderate complexity...",
  "text_type": "News Article",
  "ai_backend": "claude",
  "suggestions": ["Shorten sentences...", "Use simpler vocabulary..."]
}
```

---

### `POST /api/simplify`

**Request:**
```json
{
  "input_text": "The mitochondria produces ATP through cellular respiration...",
  "target_grade": 5.0,
  "chunking": true,
  "preserve_keywords": true,
  "mode": "standard",
  "instruction_mode": false,
  "dyslexia_mode": false,
  "api_key": "sk-ant-..."
}
```

**Response:**
```json
{
  "original_text": "The mitochondria produces...",
  "simplified_text": "The mitochondria helps the cell make energy.\n\nThis process is called cellular respiration.",
  "original_level": 9.2,
  "target_level": 5.0,
  "final_level": 5.4,
  "readability_before": {
    "flesch_kincaid": 9.5,
    "coleman_liau": 10.1,
    "smog": 8.8,
    "ari": 8.3,
    "average_grade": 9.2
  },
  "readability_after": {
    "flesch_kincaid": 5.1,
    "coleman_liau": 5.6,
    "smog": 5.3,
    "ari": 5.6,
    "average_grade": 5.4
  },
  "semantic_preservation_score": 0.91,
  "keywords_preserved": ["mitochondria", "respiration", "atp"]
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_text` | string | required | Text to simplify |
| `target_grade` | float 1–16 | required | Target grade level |
| `chunking` | bool | false | Dyslexia Support: split sentences into short chunks |
| `preserve_keywords` | bool | false | Lock key nouns and STEM terms |
| `mode` | string | `"standard"` | `"standard"` or `"esl"` |
| `instruction_mode` | bool | false | Convert instructions to numbered steps |
| `dyslexia_mode` | bool | false | Short paragraphs, each sentence on its own line |
| `api_key` | string | null | Optional Claude API key |

---

### `POST /api/worksheet_versions`

**Request:**
```json
{ "worksheet_text": "Read the passage and answer the following questions...", "api_key": "sk-ant-..." }
```

**Response:**
```json
{
  "advanced_version": "...",
  "standard_version": "...",
  "simplified_version": "...",
  "advanced_grade": 11.2,
  "standard_grade": 7.1,
  "simplified_grade": 4.3
}
```

---

### `POST /api/transform`

**Request:**
```json
{ 
  "text": "Complex academic text...", 
  "target_level": "middle_school", 
  "api_key": "sk-ant-..." 
}
```

**Response:**
```json
{
  "original_text": "...",
  "transformed_text": "...",
  "original_level": "College",
  "target_level": "middle_school",
  "original_grade": 14.2,
  "new_grade": 7.1,
  "semantic_score": 0.82,
  "original_keywords": ["photosynthesis", "cellular respiration", "ATP", "glucose"],
  "preserved_keywords": ["photosynthesis", "ATP"],
  "differentiation_metadata": {
    "grade_reduction": 7.1,
    "sentence_count_before": 8,
    "sentence_count_after": 12,
    "avg_sentence_length_before": 25.1,
    "avg_sentence_length_after": 9.1,
    "word_count_before": 200,
    "word_count_after": 110,
    "avg_word_length_before": 5.2,
    "avg_word_length_after": 4.1,
    "semantic_preservation_score": 0.82,
    "keywords_preserved_count": 2,
    "accessibility_summary": "This rewrite reduced reading difficulty by 7.1 grade levels..."
  },
  "teacher_report": "# Accessibility Adaptation Report\n\n## Reading Level Metrics\n..."
}
```

**New Response Fields:**
- `semantic_score` — Computed semantic similarity (0.0–1.0), not hardcoded
- `original_keywords` — Keywords extracted from original text
- `preserved_keywords` — Keywords verified to appear in transformed text
- `teacher_report` — Markdown-formatted classroom guidance report

---

### `POST /api/export-report`

**Purpose:** Generate a downloadable/printable Markdown report for the transformation.

**Request:** Same as `/api/transform`
```json
{ 
  "text": "Complex academic text...", 
  "target_level": "middle_school", 
  "api_key": "sk-ant-..." 
}
```

**Response:** Plain text (Markdown format) with MIME type `text/markdown`
```markdown
# Accessibility Adaptation Report

## Reading Level Metrics
This simplified text reduces reading difficulty by **7.1 grade levels**...

## Structural Changes
### Sentence Structure
- **Sentence Count:** 8 → 12 (+4 additional chunks)
- **Average Sentence Length:** 25.1 → 9.1 words
  - Sentences reduced by **64%**, improving scanability.
...

## Teacher Notes & Recommendations
This is a **substantial reduction** in difficulty. Appropriate for students 2-3 grade levels below their peers...
```

**Usage:**
```bash
# Get and save report
curl -X POST http://localhost:8000/api/export-report \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your text here...",
    "target_level": "elementary"
  }' > report.md

# View in terminal
cat report.md

# View in browser/editor
open report.md
```

---

## Forge AI / Multi-Agent Integration

The `ReadingDifficultyAgent` class wraps the API for use in orchestration pipelines:

```python
from app.services.forge_agent import ReadingDifficultyAgent

agent = ReadingDifficultyAgent(api_base="http://localhost:8000/api")

result = await agent.detect_level("Your text here...")

result = await agent.simplify_text(
    input_text="...",
    target_grade=5.0,
    preserve_keywords=True,
    mode="esl",
)

result = await agent.generate_versions("Worksheet text here...")
```

All methods are async and return structured dicts matching the API response schemas.

---

## Project Structure

```
Reading-Dificulty-Transformer/
├── app/
│   ├── api/
│   │   └── routes.py             # All endpoints; routes to Claude or Ollama based on api_key
│   ├── core/
│   │   ├── config.py             # Pydantic settings
│   │   ├── readability.py        # detect_readability() — focused 4-formula grade snapshot
│   │   ├── keyword_extractor.py  # extract_keywords(), count_preserved_keywords() — spaCy + NLTK
│   │   ├── semantic_similarity.py  # semantic_preservation_score(), compute_semantic_similarity() — sentence embeddings
│   │   ├── report_generator.py   # generate_teacher_report() — Markdown accessibility reports
│   │   ├── instructional_scoring.py # instructional_suitability_score() — classroom accessibility evaluation
│   │   └── differentiation_metadata.py # generate_differentiation_metadata() — teacher-friendly change summary
│   ├── models/
│   │   └── schemas.py            # Pydantic request/response models
│   ├── services/
│   │   ├── readability.py        # All 7 readability formulas + composite grade scoring
│   │   ├── ollama_client.py      # Local Ollama integration (analyze, detect_text_type, simplify, worksheet)
│   │   ├── claude_client.py      # Anthropic Claude API integration (stronger alternative to Ollama)
│   │   ├── simplifier.py         # Vocab replacement, keyword extraction, chunking, prompt builder
│   │   ├── semantic.py           # Legacy numpy-based semantic service (still used by /health)
│   │   └── forge_agent.py        # ReadingDifficultyAgent — Forge AI / multi-agent wrapper
│   └── main.py                   # FastAPI app entry point
├── static/
│   ├── css/style.css             # Dark-theme UI styles (with tooltips, settings panel, backend chips)
│   └── js/app.js                 # Frontend logic (4 tabs, API calls, settings panel, tooltip data)
├── templates/
│   └── index.html                # Main page (4 tabs + settings panel + text type display)
├── tests/
│   ├── test_readability.py
│   ├── test_instructional_scoring.py # Unit tests for instructional suitability scoring
│   └── test_differentiation_metadata.py # Unit tests for differentiation metadata generator
├── .env.example
├── pyproject.toml
├── requirements.txt
├── run.py
└── README.md
```

---

## How the Simplify Pipeline Works

```
INPUT TEXT
    │
    ▼
① Detect original grade level (composite weighted average of 5 formulas)
    │
    ▼
② Apply vocabulary pre-processing (60+ word replacements, STEM terms protected)
    │
    ▼
③ Extract keywords via NLTK POS tagging (if preserve_keywords=True)
    │
    ▼
④ Build LLM prompt with grade target + active flags (chunking, ESL, instruction mode...)
    │
    ▼
⑤ Send to Claude API (if api_key provided) or Ollama → rewritten text
    │
    ▼
⑥ Verify achieved grade level
    ├─ Within ±0.5 of target → done
    └─ Outside tolerance → retry (max 3 attempts)
    │
    ▼
⑦ Apply post-processing (chunking splits, dyslexia formatting)
    │
    ▼
⑧ Compute semantic similarity score (sklearn cosine_similarity over sentence embeddings)
    │
    ▼
⑨ Bracket with detect_readability() before + after
    │
    ▼
⑩ Return structured JSON
```

---

## Graceful Degradation

| Feature | Ollama + Claude | Ollama only | Claude only | Neither |
|---------|:---:|:---:|:---:|:---:|
| Readability scores | ✅ | ✅ | ✅ | ✅ |
| Text statistics | ✅ | ✅ | ✅ | ✅ |
| Difficulty classification | ✅ | ✅ | ✅ | ✅ |
| Suggestions | ✅ | ✅ | ✅ | ✅ |
| AI qualitative analysis | ✅ Claude | ✅ Ollama | ✅ Claude | ❌ skipped |
| Text type detection | ✅ Claude | ✅ Ollama | ✅ Claude | ❌ skipped |
| Text transformation | ✅ Claude | ✅ Ollama | ✅ Claude | ❌ error |
| Simplify pipeline | ✅ Claude | ✅ Ollama | ✅ Claude | ❌ error |
| Worksheet generator | ✅ Claude | ✅ Ollama | ✅ Claude | ❌ error |
| Semantic similarity | Optional | Optional | Optional | Optional |
| Instructional suitability scoring | ✅ | ✅ | ✅ | ✅ |
| Differentiation metadata | ✅ | ✅ | ✅ | ✅ |

---

## Running Tests

```bash
pip install pytest pytest-asyncio
python3 -m pytest tests/ -v
```

---

## Target Users

- **Middle school students** — grade-level text simplification
- **ESL learners** — simplified grammar, reduced clause nesting
- **Students with dyslexia** — chunked sentences, short paragraphs, extra spacing
- **Teachers** — differentiated worksheets in one click, keyword preservation for STEM vocab
- **Public library homework help desks** — lightweight single-input interface

---

## Roadmap

- [x] **Keyword extraction & preservation tracking** ✅ (Part 1-2, v0.2.0)
- [x] **Semantic similarity scoring** ✅ (Actual computation, Part 3, v0.2.0)
- [x] **Teacher report generation** ✅ (Markdown format, Part 5, v0.2.0)
- [x] **Export report endpoint** ✅ (Part 6, v0.2.0)
- [ ] Export reports (PDF/HTML) — currently Markdown
- [ ] PDF / DOCX file upload support
- [ ] Batch analysis (multiple texts)
- [ ] Side-by-side diff view (original vs. simplified)
- [ ] Reading level history & trends
- [ ] Analytics dashboard (documents simplified, avg grade reduction)
- [ ] Multi-language support
- [ ] Browser extension

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests: `python3 -m pytest tests/ -v`
4. Commit and open a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [textstat](https://github.com/textstat/textstat) — Readability formula implementations
- [Ollama](https://ollama.com) — Local LLM inference
- [Anthropic Claude API](https://docs.anthropic.com) — Cloud LLM backend
- [FastAPI](https://fastapi.tiangolo.com) — High-performance Python API framework
- [NLTK](https://www.nltk.org) — Natural language processing toolkit
- [sentence-transformers](https://www.sbert.net) — Semantic similarity scoring
