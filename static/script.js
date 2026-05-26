const state = {
  sessionId: null,
  history: [],
  busy: false,
};

const uploadForm = document.querySelector("#uploadForm");
const uploadButton = document.querySelector("#uploadButton");
const pdfInput = document.querySelector("#pdfInput");
const fileName = document.querySelector("#fileName");
const progressBar = document.querySelector("#progressBar");
const documentTitle = document.querySelector("#documentTitle");
const documentMeta = document.querySelector("#documentMeta");
const statusPill = document.querySelector("#statusPill");
const messages = document.querySelector("#messages");
const chatForm = document.querySelector("#chatForm");
const messageInput = document.querySelector("#messageInput");
const sendButton = document.querySelector("#sendButton");
const historyList = document.querySelector("#historyList");
const newChat = document.querySelector("#newChat");
const themeToggle = document.querySelector("#themeToggle");

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function setStatus(text) {
  statusPill.textContent = text;
}

function setProgress(value) {
  progressBar.style.width = `${value}%`;
}

function addMessage(role, text, typing = false) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (typing) {
    bubble.innerHTML = '<div class="typing" aria-label="Typing"><span></span><span></span><span></span></div>';
  } else {
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    const time = document.createElement("time");
    time.textContent = nowTime();
    bubble.append(paragraph, time);
  }

  article.appendChild(bubble);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function resetChatSurface() {
  messages.innerHTML = "";
  addMessage("ai", "Upload a PDF, then ask questions grounded only in that document.");
}

function enableChat(enabled) {
  messageInput.disabled = !enabled;
  sendButton.disabled = !enabled;
}

function renderHistory() {
  historyList.innerHTML = "";
  state.history.forEach((item) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "history-item";
    row.textContent = item;
    historyList.appendChild(row);
  });
}

function uploadFile(file) {
  if (!file) return;
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    addMessage("ai", "Only PDF files are supported.");
    return;
  }

  const formData = new FormData();
  formData.append("pdf", file);
  fileName.textContent = file.name;
  setStatus("Uploading");
  setProgress(18);
  enableChat(false);

  const request = new XMLHttpRequest();
  request.open("POST", "/upload");

  request.upload.onprogress = (event) => {
    if (event.lengthComputable) {
      setProgress(Math.min(90, Math.round((event.loaded / event.total) * 90)));
    }
  };

  request.onload = () => {
    let data = {};
    try {
      data = JSON.parse(request.responseText);
    } catch {
      data = { ok: false, error: "Unexpected server response." };
    }

    if (!data.ok) {
      setStatus("Error");
      setProgress(0);
      addMessage("ai", data.error || "Upload failed.");
      return;
    }

    state.sessionId = data.session_id;
    state.history.unshift(data.filename);
    renderHistory();
    documentTitle.textContent = data.filename;
    documentMeta.textContent = `${data.chunks} searchable chunks`;
    setProgress(100);
    setStatus("Ready");
    enableChat(true);
    resetChatSurface();
    addMessage("ai", "PDF indexed. Ask anything that appears in the document.");
    messageInput.focus();
  };

  request.onerror = () => {
    setStatus("Error");
    setProgress(0);
    addMessage("ai", "Network error while uploading the PDF.");
  };

  request.send(formData);
}

uploadButton.addEventListener("click", () => pdfInput.click());
pdfInput.addEventListener("change", () => uploadFile(pdfInput.files[0]));

["dragenter", "dragover"].forEach((eventName) => {
  uploadForm.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadForm.classList.add("dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  uploadForm.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadForm.classList.remove("dragging");
  });
});

uploadForm.addEventListener("drop", (event) => uploadFile(event.dataTransfer.files[0]));

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text || !state.sessionId || state.busy) return;

  state.busy = true;
  enableChat(false);
  setStatus("Thinking");
  addMessage("user", text);
  messageInput.value = "";
  messageInput.style.height = "auto";
  const typing = addMessage("ai", "", true);

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.sessionId, message: text }),
    });
    const data = await response.json();
    typing.remove();

    if (!data.ok) {
      addMessage("ai", data.error || "Could not answer right now.");
    } else {
      addMessage("ai", data.answer);
    }
  } catch {
    typing.remove();
    addMessage("ai", "Network error while contacting the chatbot.");
  } finally {
    state.busy = false;
    enableChat(true);
    setStatus("Ready");
    messageInput.focus();
  }
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = `${messageInput.scrollHeight}px`;
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

newChat.addEventListener("click", () => {
  state.sessionId = null;
  enableChat(false);
  setStatus("Idle");
  setProgress(0);
  fileName.textContent = "Drop a document here";
  documentTitle.textContent = "No PDF uploaded";
  documentMeta.textContent = "Upload a document to begin";
  resetChatSurface();
});

themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("dark");
  localStorage.setItem("datagpt-theme", document.body.classList.contains("dark") ? "dark" : "light");
});

if (localStorage.getItem("datagpt-theme") === "dark") {
  document.body.classList.add("dark");
}

window.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) window.lucide.createIcons();
});
