// ===== DOM Elements =====
const analyzeInput = document.getElementById("analyze-input");
const analyzeBtn = document.getElementById("analyze-btn");
const wordCount = document.getElementById("word-count");
const resultsDiv = document.getElementById("results");

const transformInput = document.getElementById("transform-input");
const transformBtn = document.getElementById("transform-btn");
const targetLevel = document.getElementById("target-level");
const transformResults = document.getElementById("transform-results");
const copyBtn = document.getElementById("copy-btn");

const loading = document.getElementById("loading");
const loadingText = document.getElementById("loading-text");
const ollamaStatus = document.getElementById("ollama-status");

// ===== Tab Switching =====
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`${btn.dataset.tab}-tab`).classList.add("active");
  });
});

// ===== Word Count & Button State =====
analyzeInput.addEventListener("input", () => {
  const words = analyzeInput.value.trim().split(/\s+/).filter(Boolean).length;
  wordCount.textContent = `${words} word${words !== 1 ? "s" : ""}`;
  analyzeBtn.disabled = words < 10;
});

// ===== Health Check =====
async function checkOllama() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.ollama_available) {
      ollamaStatus.textContent = "Ollama Online";
      ollamaStatus.className = "status-badge status-online";
    } else {
      ollamaStatus.textContent = "Ollama Offline (formula-only mode)";
      ollamaStatus.className = "status-badge status-offline";
    }
  } catch {
    ollamaStatus.textContent = "Server Unreachable";
    ollamaStatus.className = "status-badge status-offline";
  }
}
checkOllama();

// ===== Analyze =====
analyzeBtn.addEventListener("click", async () => {
  const text = analyzeInput.value.trim();
  if (!text) return;

  showLoading("Analyzing reading difficulty...");

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Analysis failed");
    }

    const data = await res.json();
    renderResults(data);
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    hideLoading();
  }
});

function renderResults(data) {
  // Difficulty
  document.getElementById("difficulty-level").textContent = data.difficulty.level;
  document.getElementById("difficulty-grade").textContent = `Grades ${data.difficulty.grade_range}`;
  document.getElementById("confidence-value").textContent = `${Math.round(data.difficulty.confidence * 100)}%`;
  document.getElementById("difficulty-desc").textContent = data.difficulty.description;

  // Scores
  const scoresGrid = document.getElementById("scores-grid");
  const scoreEntries = [
    ["Flesch Ease", data.scores.flesch_reading_ease],
    ["Flesch-Kincaid", data.scores.flesch_kincaid_grade],
    ["Gunning Fog", data.scores.gunning_fog],
    ["SMOG", data.scores.smog_index],
    ["Coleman-Liau", data.scores.coleman_liau],
    ["ARI", data.scores.ari],
    ["Dale-Chall", data.scores.dale_chall],
  ];
  scoresGrid.innerHTML = scoreEntries
    .map(
      ([label, value]) =>
        `<div class="score-item"><span class="label">${label}</span><span class="value">${value}</span></div>`
    )
    .join("");

  // Statistics
  const statsGrid = document.getElementById("stats-grid");
  const statEntries = [
    ["Words", data.statistics.word_count],
    ["Sentences", data.statistics.sentence_count],
    ["Avg Words/Sentence", data.statistics.avg_words_per_sentence],
    ["Avg Syllables/Word", data.statistics.avg_syllables_per_word],
    ["Complex Words", `${data.statistics.complex_word_percentage}%`],
    ["Paragraphs", data.statistics.paragraph_count],
  ];
  statsGrid.innerHTML = statEntries
    .map(
      ([label, value]) =>
        `<div class="stat-item"><span class="label">${label}</span><span class="value">${value}</span></div>`
    )
    .join("");

  // AI Analysis
  const aiCard = document.getElementById("ai-card");
  if (data.ai_analysis) {
    document.getElementById("ai-analysis").textContent = data.ai_analysis;
    aiCard.classList.remove("hidden");
  } else {
    aiCard.classList.add("hidden");
  }

  // Suggestions
  const sugList = document.getElementById("suggestions-list");
  sugList.innerHTML = data.suggestions.map((s) => `<li>${s}</li>`).join("");

  resultsDiv.classList.remove("hidden");
}

// ===== Transform =====
transformBtn.addEventListener("click", async () => {
  const text = transformInput.value.trim();
  if (!text) return;

  showLoading("Transforming text with AI...");

  try {
    const res = await fetch("/api/transform", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, target_level: targetLevel.value }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Transform failed");
    }

    const data = await res.json();
    renderTransformResults(data);
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    hideLoading();
  }
});

function renderTransformResults(data) {
  document.getElementById("original-level").textContent = data.original_level;
  document.getElementById("original-grade").textContent = `Grade ${data.original_grade}`;
  document.getElementById("new-level").textContent = data.target_level.replace("_", " ");
  document.getElementById("new-grade").textContent = `Grade ${data.new_grade}`;
  document.getElementById("transformed-text").textContent = data.transformed_text;
  transformResults.classList.remove("hidden");
}

// ===== Copy Button =====
copyBtn.addEventListener("click", () => {
  const text = document.getElementById("transformed-text").textContent;
  navigator.clipboard.writeText(text).then(() => {
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = "Copy to Clipboard"), 2000);
  });
});

// ===== Loading Helpers =====
function showLoading(text) {
  loadingText.textContent = text;
  loading.classList.remove("hidden");
}

function hideLoading() {
  loading.classList.add("hidden");
}
