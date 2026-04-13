# Reading Difficulty Transformer

A local-first classroom accessibility engine that **analyzes**, **simplifies**, and **differentiates** text for students, teachers, ESL learners, and readers with dyslexia — powered by [Ollama](https://ollama.com) and traditional readability formulas.

> **100% local & private** — your text never leaves your machine.

---

## What It Does

| Mode | Who it's for | What it returns |
|------|-------------|-----------------|
| **Analyze** | Anyone | 7 readability scores, difficulty level, AI analysis, suggestions |
| **Simplify** | Teachers, students, ESL learners | Grade-targeted rewrite with keyword locking, dyslexia support, meaning score |
| **Worksheet** | Teachers | 3 differentiated versions (Advanced / Standard / Simplified) in one click |
| **Transform** | General use | Quick rewrite to a named level (Elementary → College) |

---

## Features

### Analyze Mode
- **7 readability formulas** — Flesch Reading Ease, Flesch-Kincaid, Gunning Fog, SMOG, Coleman-Liau, ARI, Dale-Chall
- **Composite grade level** — weighted consensus across all formulas
- **Difficulty classification** — Elementary, Middle School, High School, College, Graduate
- **Text statistics** — word count, sentence count, syllable analysis, complex word %
- **AI qualitative analysis** via Ollama (graceful fallback to formula-only if offline)
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
- **Semantic similarity score** — cosine similarity between original and simplified text (requires `sentence-transformers`)
- **Structured JSON output** — `original_level`, `target_level`, `final_level`, `meaning_score`, `simplified_text`

### Worksheet Generator
- Paste any text; receive **three differentiated versions** in one request
- Advanced (Grade 10-12), Standard (Grade 6-8), Simplified (Grade 3-5)
- Each version scored for achieved grade level
- One-click copy per version

### Transform Mode
- Quick named-level rewriting: Elementary, Middle School, High School, College
- Before/after grade comparison

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **NLP** | textstat, NLTK |
| **AI** | Ollama (local LLM — llama3.2 default) |
| **Semantic Scoring** | sentence-transformers `all-MiniLM-L6-v2` (optional) |
| **Frontend** | Vanilla HTML/CSS/JS (Jinja2 templates) |
| **Config** | Pydantic Settings, `.env` files |
| **Agent Interface** | `ReadingDifficultyAgent` — Forge AI / multi-agent compatible |

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Ollama** — [Install Ollama](https://ollama.com/download)

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

### 4. Pull an Ollama Model

```bash
ollama pull llama3.2
```

### 5. Start Ollama

```bash
ollama serve
```

### 6. Run the App

```bash
python3 run.py
```

Open **http://localhost:8000** in your browser.

---

## Optional: Semantic Similarity Scoring

Install `sentence-transformers` to enable the meaning preservation score in Simplify mode:

```bash
pip install sentence-transformers
```

The model (`all-MiniLM-L6-v2`, ~80MB) downloads automatically on first use and runs fully locally.

---

## Configuration

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Model for all AI tasks |
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
{ "text": "Your text here (minimum 10 words)..." }
```

**Response:**
```json
{
  "difficulty": { "level": "High School", "grade_range": "9-12", "confidence": 0.85, "description": "..." },
  "scores": { "flesch_reading_ease": 52.3, "flesch_kincaid_grade": 10.2, ... },
  "statistics": { "word_count": 150, "sentence_count": 8, ... },
  "ai_analysis": "The text demonstrates moderate complexity...",
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
  "dyslexia_mode": false
}
```

**Response:**
```json
{
  "original_level": 9.2,
  "target_level": 5.0,
  "final_level": 5.4,
  "meaning_score": 0.91,
  "simplified_text": "The mitochondria helps the cell make energy.\n\nThis process is called cellular respiration.",
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

---

### `POST /api/worksheet_versions`

**Request:**
```json
{ "worksheet_text": "Read the passage and answer the following questions..." }
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
{ "text": "Complex academic text...", "target_level": "middle_school" }
```

**Response:**
```json
{
  "original_text": "...",
  "transformed_text": "...",
  "original_level": "College",
  "target_level": "middle_school",
  "original_grade": 14.2,
  "new_grade": 7.1
}
```

---

## Forge AI / Multi-Agent Integration

The `ReadingDifficultyAgent` class wraps the API for use in orchestration pipelines:

```python
from app.services.forge_agent import ReadingDifficultyAgent

agent = ReadingDifficultyAgent(api_base="http://localhost:8000/api")

# Detect reading level
result = await agent.detect_level("Your text here...")

# Simplify to Grade 5
result = await agent.simplify_text(
    input_text="...",
    target_grade=5.0,
    preserve_keywords=True,
    mode="esl",
)

# Generate worksheet versions
result = await agent.generate_versions("Worksheet text here...")
```

All methods are async and return structured dicts matching the API response schemas.

---

## Project Structure

```
Reading-Dificulty-Transformer/
├── app/
│   ├── api/
│   │   └── routes.py             # All endpoints: analyze, simplify, worksheet_versions, transform, health
│   ├── core/
│   │   └── config.py             # Pydantic settings (env vars)
│   ├── models/
│   │   └── schemas.py            # Request/response Pydantic models
│   ├── services/
│   │   ├── readability.py        # Readability formulas + composite grade scoring
│   │   ├── ollama_client.py      # Ollama integration (analysis, simplify, worksheet)
│   │   ├── simplifier.py         # Vocab replacement, keyword extraction, chunking, prompt builder
│   │   ├── semantic.py           # Cosine similarity scoring (sentence-transformers, optional)
│   │   └── forge_agent.py        # ReadingDifficultyAgent — Forge AI / multi-agent wrapper
│   └── main.py                   # FastAPI app entry point
├── static/
│   ├── css/style.css             # Dark-theme UI styles
│   └── js/app.js                 # Frontend logic (4 tabs, API calls, rendering)
├── templates/
│   └── index.html                # Main page (4 tabs: Analyze, Simplify, Worksheet, Transform)
├── tests/
│   └── test_readability.py       # Readability module tests
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
⑤ Send to Ollama → rewritten text
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
⑧ Compute semantic similarity score (if sentence-transformers installed)
    │
    ▼
⑨ Return structured JSON
```

---

## Graceful Degradation

| Feature | Ollama Online | Ollama Offline | sentence-transformers missing |
|---------|:---:|:---:|:---:|
| Readability scores | ✅ | ✅ | ✅ |
| Text statistics | ✅ | ✅ | ✅ |
| Difficulty classification | ✅ | ✅ | ✅ |
| Suggestions | ✅ | ✅ | ✅ |
| AI qualitative analysis | ✅ | ❌ skipped | ✅ |
| Text transformation | ✅ | ❌ error | ✅ |
| Simplify pipeline | ✅ | ❌ error | ✅ |
| Semantic similarity score | ✅ | ✅ | ❌ null |
| Worksheet generator | ✅ | ❌ error | ✅ |

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

- [ ] PDF / DOCX file upload support
- [ ] Batch analysis (multiple texts)
- [ ] Side-by-side diff view (original vs. simplified)
- [ ] Reading level history & trends
- [ ] Export reports (PDF)
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
- [FastAPI](https://fastapi.tiangolo.com) — High-performance Python API framework
- [NLTK](https://www.nltk.org) — Natural language processing toolkit
- [sentence-transformers](https://www.sbert.net) — Semantic similarity scoring
