const form = document.getElementById("generate-form");
const topicInput = document.getElementById("topic-input");
const generateBtn = document.getElementById("generate-btn");
const btnLabel = generateBtn.querySelector(".btn-label");
const statusBox = document.getElementById("pipeline-status");
const progressFill = document.getElementById("progress-fill");
const orbHeadline = document.getElementById("orb-headline");
const agentLog = document.getElementById("agent-log");
const errorBox = document.getElementById("error-box");
const resultCard = document.getElementById("result-card");
const resultContent = document.getElementById("result-content");
const readingBadge = document.getElementById("reading-badge");
const copyCurrentBtn = document.getElementById("copy-current");
const downloadCurrentBtn = document.getElementById("download-current");
const exportPdfBtn = document.getElementById("export-pdf");
const exportDocxBtn = document.getElementById("export-docx");
const shareCurrentBtn = document.getElementById("share-current");
const shareRow = document.getElementById("share-row");
const shareLinkInput = document.getElementById("share-link");
const copyShareLinkBtn = document.getElementById("copy-share-link");
const unshareCurrentBtn = document.getElementById("unshare-current");
const articleList = document.getElementById("article-list");
const refreshBtn = document.getElementById("refresh-list");

const modalBackdrop = document.getElementById("modal-backdrop");
const modalTitle = document.getElementById("modal-title");
const modalContent = document.getElementById("modal-content");
const modalClose = document.getElementById("modal-close");

const signinCard = document.getElementById("signin-card");
const appCard = document.getElementById("app-card");
const articlesCard = document.getElementById("articles-card");
const userBox = document.getElementById("user-box");
const userAvatar = document.getElementById("user-avatar");
const userName = document.getElementById("user-name");

async function checkAuth() {
  const res = await fetch("/api/me");
  const user = await res.json();

  if (!user) {
    signinCard.classList.remove("hidden");
    appCard.classList.add("hidden");
    articlesCard.classList.add("hidden");
    userBox.classList.add("hidden");
    return false;
  }

  signinCard.classList.add("hidden");
  appCard.classList.remove("hidden");
  articlesCard.classList.remove("hidden");
  userBox.classList.remove("hidden");
  userName.textContent = user.name;
  if (user.picture) userAvatar.src = user.picture;
  return true;
}

let currentArticle = null;
let stepTimers = [];
let logInterval = null;

function setStep(stepName, state) {
  const el = statusBox.querySelector(`[data-step="${stepName}"]`);
  el.classList.remove("active", "done");
  if (state) el.classList.add(state);
}

const LOG_LINES = {
  research: [
    ["WEB", "querying search index for source material..."],
    ["WEB", "ranking results by relevance and recency"],
    ["AGENT", "Senior Research Analyst is cross-checking facts"],
    ["AGENT", "flagging unverified claims for review"],
    ["WEB", "extracting key data points from top sources"],
    ["AGENT", "compiling structured findings + citations"],
  ],
  write: [
    ["AGENT", "Content Writer is reading the research brief"],
    ["LLM", "drafting opening hook and section outline"],
    ["LLM", "expanding sections with supporting detail"],
    ["AGENT", "weaving in source references inline"],
    ["LLM", "shaping a conversational, jargon-free tone"],
  ],
  edit: [
    ["AGENT", "Senior Editor is reviewing the draft"],
    ["LLM", "tightening sentences, trimming filler"],
    ["AGENT", "verifying claims against the original research"],
    ["LLM", "polishing tone and structure for readability"],
    ["AGENT", "finalizing publication-ready copy"],
  ],
};

const HEADLINES = {
  research: "Researching the web",
  write: "Drafting the article",
  edit: "Polishing the final copy",
};

function setHeadline(text) {
  orbHeadline.innerHTML = `${text}<span class="ellipsis"><span>.</span><span>.</span><span>.</span></span>`;
}

function pushLogLine(tag, text) {
  const line = document.createElement("div");
  line.className = "log-line";
  const ts = new Date().toLocaleTimeString([], { hour12: false });
  line.innerHTML = `<span class="ts">${ts}</span><span class="tag">[${tag}]</span><span>${text}</span>`;
  agentLog.appendChild(line);
  while (agentLog.children.length > 6) {
    agentLog.removeChild(agentLog.firstChild);
  }
}

function runLogFeedFor(phase) {
  if (logInterval) clearInterval(logInterval);
  const lines = LOG_LINES[phase];
  let i = 0;
  pushLogLine(...lines[0]);
  i = 1;
  logInterval = setInterval(() => {
    pushLogLine(...lines[i % lines.length]);
    i++;
  }, 1700);
}

function startFakeProgress() {
  statusBox.classList.remove("hidden");
  agentLog.innerHTML = "";
  ["research", "write", "edit"].forEach((s) => setStep(s, null));
  progressFill.style.width = "4%";
  setStep("research", "active");
  setHeadline(HEADLINES.research);
  runLogFeedFor("research");

  stepTimers.push(setTimeout(() => { progressFill.style.width = "30%"; }, 200));

  stepTimers.push(setTimeout(() => {
    setStep("research", "done");
    setStep("write", "active");
    setHeadline(HEADLINES.write);
    runLogFeedFor("write");
    progressFill.style.width = "62%";
  }, 12000));

  stepTimers.push(setTimeout(() => {
    setStep("write", "done");
    setStep("edit", "active");
    setHeadline(HEADLINES.edit);
    runLogFeedFor("edit");
    progressFill.style.width = "88%";
  }, 28000));
}

function finishProgress(success) {
  stepTimers.forEach(clearTimeout);
  stepTimers = [];
  if (logInterval) clearInterval(logInterval);
  if (success) {
    progressFill.style.width = "100%";
    setHeadline("Done");
    ["research", "write", "edit"].forEach((s) => setStep(s, "done"));
    pushLogLine("DONE", "article finalized and saved.");
  }
  setTimeout(() => statusBox.classList.add("hidden"), 900);
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

function showReadingBadge(article) {
  if (article && article.reading_time_minutes) {
    readingBadge.textContent = `${article.reading_time_minutes} min read · ${article.words} words`;
    readingBadge.classList.remove("hidden");
  } else {
    readingBadge.classList.add("hidden");
  }
}

async function copyText(text, btn) {
  const label = btn.querySelector(".btn-text");
  const original = label ? label.textContent : "";
  try {
    await navigator.clipboard.writeText(text);
    if (label) label.textContent = "Copied!";
  } catch {
    if (label) label.textContent = "Copy failed";
  }
  btn.classList.add("copied");
  setTimeout(() => {
    if (label) label.textContent = original;
    btn.classList.remove("copied");
  }, 1600);
}

copyCurrentBtn.addEventListener("click", () => {
  if (currentArticle) copyText(currentArticle.content, copyCurrentBtn);
});

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function exportArticle(format, btn) {
  if (!currentArticle) return;
  const label = btn.querySelector(".btn-text");
  const original = label ? label.textContent : "";
  if (label) label.textContent = "…";
  btn.disabled = true;
  try {
    const res = await fetch(
      `/api/articles/${encodeURIComponent(currentArticle.filename)}/export?format=${format}`
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Export failed.");
    }
    const blob = await res.blob();
    const base = currentArticle.filename.replace(/\.md$/, "");
    triggerDownload(blob, `${base}.${format}`);
  } catch (err) {
    showError(err.message || "Export failed.");
  } finally {
    if (label) label.textContent = original;
    btn.disabled = false;
  }
}

exportPdfBtn.addEventListener("click", () => exportArticle("pdf", exportPdfBtn));
exportDocxBtn.addEventListener("click", () => exportArticle("docx", exportDocxBtn));

function showShareLink(url) {
  shareLinkInput.value = url;
  shareRow.classList.remove("hidden");
  shareCurrentBtn.classList.add("active");
}

function hideShareLink() {
  shareRow.classList.add("hidden");
  shareCurrentBtn.classList.remove("active");
}

shareCurrentBtn.addEventListener("click", async () => {
  if (!currentArticle) return;
  // Already showing a link? Treat the button as a toggle to hide the row.
  if (!shareRow.classList.contains("hidden")) {
    hideShareLink();
    return;
  }
  shareCurrentBtn.disabled = true;
  try {
    const res = await fetch(
      `/api/articles/${encodeURIComponent(currentArticle.filename)}/share`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error("Could not create a share link.");
    const data = await res.json();
    showShareLink(data.share_url);
    await loadArticles();
  } catch (err) {
    showError(err.message);
  } finally {
    shareCurrentBtn.disabled = false;
  }
});

copyShareLinkBtn.addEventListener("click", () => {
  copyText(shareLinkInput.value, copyShareLinkBtn);
});

unshareCurrentBtn.addEventListener("click", async () => {
  if (!currentArticle) return;
  unshareCurrentBtn.disabled = true;
  try {
    const res = await fetch(
      `/api/articles/${encodeURIComponent(currentArticle.filename)}/share`,
      { method: "DELETE" }
    );
    if (!res.ok) throw new Error("Could not stop sharing.");
    hideShareLink();
    await loadArticles();
  } catch (err) {
    showError(err.message);
  } finally {
    unshareCurrentBtn.disabled = false;
  }
});

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

    if (res.status === 401) {
      await checkAuth();
      throw new Error("Your session expired. Please sign in again.");
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Generation failed.");
    }

    const data = await res.json();
    currentArticle = data;
    resultContent.innerHTML = marked.parse(data.content);
    showReadingBadge(data);
    hideShareLink();
    resultContent.classList.remove("reveal");
    resultCard.classList.remove("hidden");
    void resultContent.offsetWidth;
    resultContent.classList.add("reveal");
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

(async () => {
  const signedIn = await checkAuth();
  if (signedIn) await loadArticles();
})();
