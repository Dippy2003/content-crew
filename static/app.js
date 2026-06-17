const form = document.getElementById("generate-form");
const topicInput = document.getElementById("topic-input");
const generateBtn = document.getElementById("generate-btn");
const btnLabel = generateBtn.querySelector(".btn-label");
const statusBox = document.getElementById("pipeline-status");
const progressFill = document.getElementById("progress-fill");
const errorBox = document.getElementById("error-box");
const resultCard = document.getElementById("result-card");
const resultContent = document.getElementById("result-content");
const downloadCurrentBtn = document.getElementById("download-current");
const articleList = document.getElementById("article-list");
const refreshBtn = document.getElementById("refresh-list");

const modalBackdrop = document.getElementById("modal-backdrop");
const modalTitle = document.getElementById("modal-title");
const modalContent = document.getElementById("modal-content");
const modalClose = document.getElementById("modal-close");

let currentArticle = null;
let stepTimers = [];

function setStep(stepName, state) {
  const el = statusBox.querySelector(`[data-step="${stepName}"]`);
  el.classList.remove("active", "done");
  if (state) el.classList.add(state);
}

function startFakeProgress() {
  statusBox.classList.remove("hidden");
  ["research", "write", "edit"].forEach((s) => setStep(s, null));
  progressFill.style.width = "4%";
  setStep("research", "active");

  stepTimers.push(setTimeout(() => { progressFill.style.width = "30%"; }, 200));

  stepTimers.push(setTimeout(() => {
    setStep("research", "done");
    setStep("write", "active");
    progressFill.style.width = "62%";
  }, 12000));

  stepTimers.push(setTimeout(() => {
    setStep("write", "done");
    setStep("edit", "active");
    progressFill.style.width = "88%";
  }, 28000));
}

function finishProgress(success) {
  stepTimers.forEach(clearTimeout);
  stepTimers = [];
  if (success) {
    progressFill.style.width = "100%";
    ["research", "write", "edit"].forEach((s) => setStep(s, "done"));
  }
  setTimeout(() => statusBox.classList.add("hidden"), 700);
}

function setLoading(isLoading) {
  generateBtn.disabled = isLoading;
  if (isLoading) {
    btnLabel.innerHTML = '<span class="spinner"></span> Generating';
  } else {
    btnLabel.textContent = "Generate";
  }
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function hideError() {
  errorBox.classList.add("hidden");
}

async function loadArticles() {
  const res = await fetch("/api/articles");
  const articles = await res.json();

  articleList.innerHTML = "";
  if (articles.length === 0) {
    articleList.innerHTML = '<div class="empty-state">No articles generated yet.</div>';
    return;
  }

  for (const { filename } of articles) {
    const row = document.createElement("div");
    row.className = "article-row";
    const title = filename.replace(/_\d{8}-\d{6}\.md$/, "").replace(/-/g, " ");
    row.innerHTML = `
      <span class="title">📄 ${title}</span>
      <span class="date">${filename}</span>
    `;
    row.addEventListener("click", () => openArticle(filename));
    articleList.appendChild(row);
  }
}

async function openArticle(filename) {
  const res = await fetch(`/api/articles/${encodeURIComponent(filename)}`);
  if (!res.ok) return;
  const data = await res.json();
  modalTitle.textContent = data.filename;
  modalContent.innerHTML = marked.parse(data.content);
  modalBackdrop.classList.remove("hidden");
}

modalClose.addEventListener("click", () => modalBackdrop.classList.add("hidden"));
modalBackdrop.addEventListener("click", (e) => {
  if (e.target === modalBackdrop) modalBackdrop.classList.add("hidden");
});

refreshBtn.addEventListener("click", loadArticles);

downloadCurrentBtn.addEventListener("click", () => {
  if (!currentArticle) return;
  const blob = new Blob([currentArticle.content], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = currentArticle.filename;
  a.click();
  URL.revokeObjectURL(url);
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) return;

  hideError();
  resultCard.classList.add("hidden");
  setLoading(true);
  startFakeProgress();

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Generation failed.");
    }

    const data = await res.json();
    currentArticle = data;
    resultContent.innerHTML = marked.parse(data.content);
    resultCard.classList.remove("hidden");
    finishProgress(true);
    await loadArticles();
  } catch (err) {
    finishProgress(false);
    statusBox.classList.add("hidden");
    showError(err.message || "Something went wrong.");
  } finally {
    setLoading(false);
  }
});

loadArticles();
