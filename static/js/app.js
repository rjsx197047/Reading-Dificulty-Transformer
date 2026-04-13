// ===== DOM Elements =====
const analyzeInput = document.getElementById("analyze-input");
const analyzeBtn = document.getElementById("analyze-btn");
const wordCount = document.getElementById("word-count");
const resultsDiv = document.getElementById("results");

const simplifyInput = document.getElementById("simplify-input");
const simplifyBtn = document.getElementById("simplify-btn");
const simplifyWordCount = document.getElementById("simplify-word-count");
const gradeSlider = document.getElementById("grade-slider");
const gradeDisplay = document.getElementById("grade-display");
const simplifyResults = document.getElementById("simplify-results");

const worksheetInput = document.getElementById("worksheet-input");
const worksheetBtn = document.getElementById("worksheet-btn");
const worksheetWordCount = document.getElementById("worksheet-word-count");
const worksheetResults = document.getElementById("worksheet-results");

const transformInput = document.getElementById("transform-input");
const transformBtn = document.getElementById("transform-btn");
const targetLevel = document.getElementById("target-level");
const transformResults = document.getElementById("transform-results");
const copyBtn = document.getElementById("copy-btn");

const loading = document.getElementById("loading");
const loadingText = document.getElementById("loading-text");
const ollamaStatus = document.getElementById("ollama-status");
const semanticStatus = document.getElementById("semantic-status");

// ===== Tab Switching =====
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`${btn.dataset.tab}-tab`).classList.add("active");
  });
});

// ===== Word Count Helpers =====
function countWords(text) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

analyzeInput.addEventListener("input", () => {
  const words = countWords(analyzeInput.value);
  wordCount.textContent = `${words} word${words !== 1 ? "s" : ""}`;
  analyzeBtn.disabled = words < 10;
});

simplifyInput.addEventListener("input", () => {
  const words = countWords(simplifyInput.value);
  simplifyWordCount.textContent = `${words} word${words !== 1 ? "s" : ""}`;
});

worksheetInput.addEventListener("input", () => {
  const words = countWords(worksheetInput.value);
  worksheetWordCount.textContent = `${words} word${words !== 1 ? "s" : ""}`;
});

// ===== Grade Slider =====
gradeSlider.addEventListener("input", () => {
  const val = parseFloat(gradeSlider.value);
  gradeDisplay.textContent = `Grade ${val % 1 === 0 ? val : val.toFixed(1)}`;
  gradeDisplay.className = "grade-pill " + gradeColorClass(val);
});

function gradeColorClass(grade) {
  if (grade <= 5) return "grade-pill-elem";
  if (grade <= 8) return "grade-pill-middle";
  if (grade <= 12) return "grade-pill-high";
  return "grade-pill-college";
}

// ===== Health Check =====
async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();

    if (data.ollama_available) {
      ollamaStatus.textContent = "Ollama Online";
      ollamaStatus.className = "status-badge status-online";
    } else {
      ollamaStatus.textContent = "Ollama Offline";
      ollamaStatus.className = "status-badge status-offline";
    }

    if (data.semantic_scoring_available) {
      semanticStatus.textContent = "Semantic Scoring On";
      semanticStatus.className = "status-badge status-online";
    } else {
      semanticStatus.textContent = "Semantic Scoring Off";
      semanticStatus.className = "status-badge status-dim";
    }
  } catch {
    ollamaStatus.textContent = "Server Unreachable";
    ollamaStatus.className = "status-badge status-offline";
    semanticStatus.textContent = "Server Unreachable";
    semanticStatus.className = "status-badge status-offline";
  }
}
checkHealth();

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
    if (!res.ok) throw new Error((await res.json()).detail || "Analysis failed");
    renderAnalyzeResults(await res.json());
  } catch (err) {
    showError(err.message);
  } finally {
    hideLoading();
  }
});

function renderAnalyzeResults(data) {
  document.getElementById("difficulty-level").textContent = data.difficulty.level;
  document.getElementById("difficulty-grade").textContent = `Grades ${data.difficulty.grade_range}`;
  document.getElementById("confidence-value").textContent = `${Math.round(data.difficulty.confidence * 100)}%`;
  document.getElementById("difficulty-desc").textContent = data.difficulty.description;

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
    .map(([label, value]) => `<div class="score-item"><span class="label">${label}</span><span class="value">${value}</span></div>`)
    .join("");

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
    .map(([label, value]) => `<div class="stat-item"><span class="label">${label}</span><span class="value">${value}</span></div>`)
    .join("");

  const aiCard = document.getElementById("ai-card");
  if (data.ai_analysis) {
    document.getElementById("ai-analysis").textContent = data.ai_analysis;
    aiCard.classList.remove("hidden");
  } else {
    aiCard.classList.add("hidden");
  }

  const sugList = document.getElementById("suggestions-list");
  sugList.innerHTML = data.suggestions.map((s) => `<li>${s}</li>`).join("");

  resultsDiv.classList.remove("hidden");
}

// ===== Simplify =====
simplifyBtn.addEventListener("click", async () => {
  const text = simplifyInput.value.trim();
  if (!text) return;

  showLoading("Simplifying text — this may take a moment...");
  try {
    const payload = {
      input_text: text,
      target_grade: parseFloat(gradeSlider.value),
      chunking: document.getElementById("opt-chunking").checked,
      preserve_keywords: document.getElementById("opt-keywords").checked,
      mode: document.getElementById("simplify-mode").value,
      instruction_mode: document.getElementById("opt-instructions").checked,
      dyslexia_mode: document.getElementById("opt-dyslexia").checked,
    };

    const res = await fetch("/api/simplify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Simplification failed");
    renderSimplifyResults(await res.json());
  } catch (err) {
    showError(err.message);
  } finally {
    hideLoading();
  }
});

function renderSimplifyResults(data) {
  document.getElementById("orig-grade-val").textContent = `${data.original_level}`;
  document.getElementById("target-grade-val").textContent = `${data.target_level}`;
  document.getElementById("final-grade-val").textContent = `${data.final_level}`;

  // Color final grade based on proximity to target
  const diff = Math.abs(data.final_level - data.target_level);
  const finalEl = document.getElementById("final-grade-val");
  finalEl.className = "journey-grade " + (diff <= 0.5 ? "grade-success" : diff <= 1.5 ? "grade-warn" : "grade-high");

  // Meaning score
  const meaningRow = document.getElementById("meaning-score-row");
  if (data.meaning_score !== null && data.meaning_score !== undefined) {
    const pct = Math.round(data.meaning_score * 100);
    document.getElementById("meaning-value").textContent = `${pct}%`;
    const bar = document.getElementById("meaning-bar");
    bar.style.width = `${pct}%`;
    bar.className = "meaning-bar " + (pct >= 80 ? "meaning-high" : pct >= 60 ? "meaning-mid" : "meaning-low");
    meaningRow.classList.remove("hidden");
  } else {
    meaningRow.classList.add("hidden");
  }

  // Keywords
  const kwCard = document.getElementById("keywords-card");
  if (data.keywords_preserved && data.keywords_preserved.length > 0) {
    document.getElementById("keywords-list").innerHTML = data.keywords_preserved
      .map((kw) => `<span class="keyword-tag">${kw}</span>`)
      .join("");
    kwCard.classList.remove("hidden");
  } else {
    kwCard.classList.add("hidden");
  }

  document.getElementById("simplified-text").textContent = data.simplified_text;
  simplifyResults.classList.remove("hidden");
}

document.getElementById("copy-simplified-btn").addEventListener("click", () => {
  const text = document.getElementById("simplified-text").textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById("copy-simplified-btn");
    btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = "Copy to Clipboard"), 2000);
  });
});

// ===== Worksheet =====
worksheetBtn.addEventListener("click", async () => {
  const text = worksheetInput.value.trim();
  if (!text) return;

  showLoading("Generating differentiated versions...");
  try {
    const res = await fetch("/api/worksheet_versions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ worksheet_text: text }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Worksheet generation failed");
    renderWorksheetResults(await res.json());
  } catch (err) {
    showError(err.message);
  } finally {
    hideLoading();
  }
});

function renderWorksheetResults(data) {
  document.getElementById("adv-grade").textContent = `Grade ${data.advanced_grade}`;
  document.getElementById("std-grade").textContent = `Grade ${data.standard_grade}`;
  document.getElementById("sim-grade").textContent = `Grade ${data.simplified_grade}`;

  document.getElementById("adv-text").textContent = data.advanced_version;
  document.getElementById("std-text").textContent = data.standard_version;
  document.getElementById("sim-text").textContent = data.simplified_version;

  worksheetResults.classList.remove("hidden");
}

document.querySelectorAll(".copy-worksheet-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const text = document.getElementById(btn.dataset.target).textContent;
    navigator.clipboard.writeText(text).then(() => {
      btn.textContent = "Copied!";
      setTimeout(() => (btn.textContent = "Copy"), 2000);
    });
  });
});

// ===== Transform (legacy) =====
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
    if (!res.ok) throw new Error((await res.json()).detail || "Transform failed");
    renderTransformResults(await res.json());
  } catch (err) {
    showError(err.message);
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

copyBtn.addEventListener("click", () => {
  const text = document.getElementById("transformed-text").textContent;
  navigator.clipboard.writeText(text).then(() => {
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = "Copy to Clipboard"), 2000);
  });
});

// ===== Utilities =====
function showLoading(text) {
  loadingText.textContent = text;
  loading.classList.remove("hidden");
}

function hideLoading() {
  loading.classList.add("hidden");
}

function showError(message) {
  // Simple inline toast — no external deps
  const toast = document.createElement("div");
  toast.className = "error-toast";
  toast.textContent = `Error: ${message}`;
  document.querySelector(".container").appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}
