# Reading Difficulty Transformer

A local-first web application that **analyzes** and **transforms** text reading difficulty using traditional readability formulas and AI-powered analysis via [Ollama](https://ollama.com).

> **100% local & private** — your text never leaves your machine.

---

## Demo

| Analyze | Transform |
|---------|-----------|
| Paste text and get instant readability scores, difficulty classification, AI analysis, and improvement suggestions. | Rewrite any text to a target reading level (elementary through college) using a local LLM. |

---

## Features

### Analyze Mode
- **7 readability formulas** computed simultaneously:
  - Flesch Reading Ease
  - Flesch-Kincaid Grade Level
  - Gunning Fog Index
  - SMOG Index
  - Coleman-Liau Index
  - Automated Readability Index (ARI)
  - Dale-Chall Readability Score
- **Difficulty classification** — Elementary, Middle School, High School, College, or Graduate
- **Text statistics** — word count, sentence count, syllable analysis, complex word percentage
- **AI-powered qualitative analysis** via Ollama (gracefully degrades to formula-only if Ollama is offline)
- **Actionable suggestions** to simplify text

### Transform Mode
- **Rewrite text** to a target reading level using a local LLM
- **Target levels:** Elementary (K-5), Middle School (6-8), High School (9-12), College
- **Before/after comparison** — see grade-level change after transformation
- **Copy to clipboard** — one-click copy of transformed text

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **NLP** | textstat, NLTK |
| **AI** | Ollama (local LLM — llama3.2 default) |
| **Frontend** | Vanilla HTML/CSS/JS (Jinja2 templates) |
| **Config** | Pydantic Settings, `.env` files |

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
python3 -c "import nltk; nltk.download('cmudict'); nltk.download('punkt'); nltk.download('punkt_tab')"
```

### 4. Pull an Ollama Model

```bash
ollama pull llama3.2
```

### 5. Start Ollama (if not already running)

```bash
ollama serve
```

### 6. Run the App

```bash
python3 run.py
```

Open **http://localhost:8000** in your browser.

---

## Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Available settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Model for AI analysis & transforms |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `DEBUG` | `true` | Enable hot-reload |

---

## API Reference

### `GET /api/health`

Health check. Returns server status and Ollama availability.

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "ollama_available": true
}
```

### `POST /api/analyze`

Analyze reading difficulty of text.

**Request:**
```json
{
  "text": "Your text here (minimum 10 words)..."
}
```

**Response:**
```json
{
  "difficulty": {
    "level": "High School",
    "grade_range": "9-12",
    "confidence": 0.85,
    "description": "Standard high school level content."
  },
  "scores": {
    "flesch_reading_ease": 52.3,
    "flesch_kincaid_grade": 10.2,
    "gunning_fog": 12.8,
    "smog_index": 11.5,
    "coleman_liau": 10.1,
    "ari": 11.3,
    "dale_chall": 8.2
  },
  "statistics": {
    "word_count": 150,
    "sentence_count": 8,
    "avg_words_per_sentence": 18.75,
    "complex_word_percentage": 12.5
  },
  "ai_analysis": "The text demonstrates moderate complexity...",
  "suggestions": ["Use simpler vocabulary...", "Shorten sentences..."]
}
```

### `POST /api/transform`

Transform text to a target reading level (requires Ollama).

**Request:**
```json
{
  "text": "Complex academic text...",
  "target_level": "middle_school"
}
```

**Response:**
```json
{
  "original_text": "Complex academic text...",
  "transformed_text": "Simpler version of the text...",
  "original_level": "College",
  "target_level": "middle_school",
  "original_grade": 14.2,
  "new_grade": 7.1
}
```

---

## Project Structure

```
Reading-Dificulty-Transformer/
├── app/
│   ├── api/
│   │   └── routes.py             # API endpoints (analyze, transform, health)
│   ├── core/
│   │   └── config.py             # Pydantic settings (env vars)
│   ├── models/
│   │   └── schemas.py            # Request/response Pydantic models
│   ├── services/
│   │   ├── readability.py        # Core reading-level detector module
│   │   └── ollama_client.py      # Ollama integration (AI analysis & transform)
│   ├── utils/
│   └── main.py                   # FastAPI app entry point
├── static/
│   ├── css/
│   │   └── style.css             # Dark-theme UI styles
│   └── js/
│       └── app.js                # Frontend logic (tabs, API calls, rendering)
├── templates/
│   └── index.html                # Main page (Jinja2 template)
├── tests/
│   └── test_readability.py       # Readability module tests
├── .env.example                  # Environment variable template
├── .gitignore
├── pyproject.toml                # Project metadata & tool config
├── requirements.txt              # Python dependencies
├── run.py                        # Dev server launcher
└── README.md
```

---

## How It Works

### Reading-Level Detection Pipeline

1. **Text Statistics** — Extract raw metrics (word count, sentence count, syllable count, complex word ratio)
2. **Readability Formulas** — Compute 7 standard readability scores using `textstat`
3. **Weighted Classification** — Combine grade-level scores into a composite grade using weighted averaging:
   - Flesch-Kincaid Grade (weight: 2.0)
   - Gunning Fog (weight: 1.5)
   - SMOG Index (weight: 1.5)
   - Coleman-Liau (weight: 1.0)
   - ARI (weight: 1.0)
4. **Difficulty Mapping** — Map composite grade to level (Elementary → Graduate) with confidence score
5. **AI Analysis** *(optional)* — Query Ollama for qualitative assessment of vocabulary, structure, and conceptual density
6. **Suggestions** — Generate actionable improvements based on score thresholds

### Text Transformation

1. **Original Analysis** — Compute baseline grade level
2. **LLM Rewrite** — Prompt Ollama to rewrite text for the target audience while preserving all factual content
3. **Post-Analysis** — Compute the new grade level to verify improvement

---

## Running Tests

```bash
pip install pytest pytest-asyncio
python3 -m pytest tests/ -v
```

---

## Graceful Degradation

The app works **with or without Ollama**:

| Feature | Ollama Online | Ollama Offline |
|---------|:---:|:---:|
| Readability scores | ✅ | ✅ |
| Text statistics | ✅ | ✅ |
| Difficulty classification | ✅ | ✅ |
| Suggestions | ✅ | ✅ |
| AI qualitative analysis | ✅ | ❌ (skipped) |
| Text transformation | ✅ | ❌ (returns error) |

---

## Roadmap

- [ ] PDF/DOCX file upload support
- [ ] Batch analysis (multiple texts)
- [ ] Reading level history & trends
- [ ] Custom vocabulary lists for domain-specific analysis
- [ ] Side-by-side original vs. transformed diff view
- [ ] Export reports (PDF)
- [ ] Multi-language support
- [ ] Browser extension

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests: `python3 -m pytest tests/ -v`
4. Commit changes: `git commit -m "Add my feature"`
5. Push and open a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [textstat](https://github.com/textstat/textstat) — Readability formula implementations
- [Ollama](https://ollama.com) — Local LLM inference
- [FastAPI](https://fastapi.tiangolo.com) — High-performance Python API framework
- [NLTK](https://www.nltk.org) — Natural language processing toolkit
