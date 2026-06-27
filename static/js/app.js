/* NotaIA - lógica del frontend.
 * Web Speech API para transcribir en vivo + fetch al backend para chat y guardado.
 */
(() => {
  "use strict";

  // ---------- Estado ----------
  let recognition = null;
  let isRecording = false;
  let finalTranscript = "";
  let chatHistory = []; // [{role, content}]
  let seconds = 0;
  let timerId = null;

  // ---------- Referencias al DOM ----------
  const $ = (id) => document.getElementById(id);
  const recordBtn = $("record-btn");
  const recordIcon = $("record-icon");
  const statusDot = $("status-dot");
  const statusText = $("status-text");
  const timerEl = $("timer");
  const transcriptBox = $("transcript-box");
  const transcriptEmpty = $("transcript-empty");
  const transcriptFinal = $("transcript-final");
  const transcriptInterim = $("transcript-interim");
  const copyBtn = $("copy-transcript");
  const actions = $("actions");
  const saveBtn = $("save-btn");
  const discardBtn = $("discard-btn");
  const chatMessages = $("chat-messages");
  const chatEmpty = $("chat-empty");
  const chatForm = $("chat-form");
  const chatInput = $("chat-input");
  const chatSend = $("chat-send");

  // ---------- Utilidades ----------
  function toast(msg, isError = false) {
    const t = $("toast");
    t.textContent = msg;
    t.classList.toggle("border-pink-500/40", isError);
    t.classList.remove("hidden");
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.add("hidden"), 3000);
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function fmtTime(total) {
    const m = String(Math.floor(total / 60)).padStart(2, "0");
    const s = String(total % 60).padStart(2, "0");
    return `${m}:${s}`;
  }

  function hasTranscript() {
    return finalTranscript.trim().length > 0;
  }

  // ---------- Reconocimiento de voz ----------
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  function setupRecognition() {
    if (!SpeechRecognition) {
      $("browser-warning").classList.remove("hidden");
      recordBtn.disabled = true;
      recordBtn.classList.add("opacity-40", "cursor-not-allowed");
      return;
    }
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "es-AR";

    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const chunk = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += chunk + " ";
        } else {
          interim += chunk;
        }
      }
      renderTranscript(interim);
    };

    recognition.onerror = (e) => {
      if (e.error === "no-speech" || e.error === "aborted") return;
      toast("Error de micrófono: " + e.error, true);
    };

    // Si sigue grabando, reiniciar al cortarse solo (límite del navegador)
    recognition.onend = () => {
      if (isRecording) recognition.start();
    };
  }

  function renderTranscript(interim = "") {
    if (hasTranscript() || interim) transcriptEmpty.classList.add("hidden");
    transcriptFinal.textContent = finalTranscript;
    transcriptInterim.textContent = interim;
    transcriptBox.scrollTop = transcriptBox.scrollHeight;
  }

  // ---------- Control de grabación ----------
  function startRecording() {
    finalTranscript = "";
    chatHistory = [];
    renderChat();
    renderTranscript();
    actions.classList.add("hidden");

    isRecording = true;
    seconds = 0;
    timerEl.textContent = "00:00";
    timerId = setInterval(() => {
      seconds++;
      timerEl.textContent = fmtTime(seconds);
    }, 1000);

    recognition.start();
    recordBtn.classList.add("rec-pulse");
    recordIcon.innerHTML =
      '<svg class="h-8 w-8 text-white" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
    statusDot.className = "h-2.5 w-2.5 rounded-full bg-pink-500 animate-pulse";
    statusText.textContent = "Grabando...";
  }

  function stopRecording() {
    isRecording = false;
    clearInterval(timerId);
    if (recognition) recognition.stop();

    recordBtn.classList.remove("rec-pulse");
    recordIcon.innerHTML =
      '<svg class="h-9 w-9 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>';

    if (hasTranscript()) {
      statusDot.className = "h-2.5 w-2.5 rounded-full bg-emerald-500";
      statusText.textContent = "Grabación lista";
      actions.classList.remove("hidden");
      copyBtn.classList.remove("hidden");
      enableChat(true);
      renderTranscript();
    } else {
      statusDot.className = "h-2.5 w-2.5 rounded-full bg-slate-500";
      statusText.textContent = "No se detectó audio";
    }
  }

  recordBtn.addEventListener("click", () => {
    if (!recognition) return;
    isRecording ? stopRecording() : startRecording();
  });

  // ---------- Chat ----------
  function enableChat(on) {
    chatInput.disabled = !on;
    chatSend.disabled = !on;
  }

  function renderChat() {
    chatMessages.querySelectorAll(".bubble").forEach((n) => n.remove());
    if (chatHistory.length === 0) {
      chatEmpty.classList.remove("hidden");
      return;
    }
    chatEmpty.classList.add("hidden");
    for (const m of chatHistory) addBubble(m.role, m.content);
  }

  function addBubble(role, content) {
    const wrap = document.createElement("div");
    wrap.className = "bubble fade-in flex " + (role === "user" ? "justify-end" : "justify-start");
    const inner = document.createElement("div");
    inner.className =
      "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap " +
      (role === "user"
        ? "grad-bg text-white rounded-br-sm"
        : "bg-white/8 border border-white/10 text-slate-100 rounded-bl-sm");
    inner.innerHTML = escapeHtml(content);
    wrap.appendChild(inner);
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return wrap;
  }

  function showTyping() {
    const wrap = document.createElement("div");
    wrap.className = "bubble flex justify-start";
    wrap.innerHTML =
      '<div class="bg-white/8 border border-white/10 rounded-2xl rounded-bl-sm px-4 py-3 typing"><span></span><span></span><span></span></div>';
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return wrap;
  }

  async function sendQuestion(question) {
    if (!question.trim() || !hasTranscript()) return;
    chatHistory.push({ role: "user", content: question });
    chatEmpty.classList.add("hidden");
    addBubble("user", question);
    const typing = showTyping();
    enableChat(false);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript: finalTranscript,
          question,
          messages: chatHistory.slice(0, -1),
        }),
      });
      const data = await res.json();
      typing.remove();
      if (!res.ok) {
        toast(data.error || "Error al consultar la IA", true);
        chatHistory.pop();
        return;
      }
      chatHistory.push({ role: "assistant", content: data.reply });
      addBubble("assistant", data.reply);
    } catch (err) {
      typing.remove();
      chatHistory.pop();
      toast("No se pudo conectar con el servidor", true);
    } finally {
      enableChat(true);
      chatInput.focus();
    }
  }

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = chatInput.value.trim();
    if (!q) return;
    chatInput.value = "";
    chatInput.style.height = "auto";
    sendQuestion(q);
  });

  // Enter envía, Shift+Enter hace salto de línea
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.requestSubmit();
    }
  });
  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
  });

  // Sugerencias rápidas
  document.querySelectorAll(".suggestion").forEach((b) => {
    b.addEventListener("click", () => {
      if (!hasTranscript()) {
        toast("Primero grabá una clase", true);
        return;
      }
      sendQuestion(b.textContent.trim());
    });
  });

  // ---------- Copiar transcript ----------
  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(finalTranscript.trim());
      toast("Transcripción copiada");
    } catch {
      toast("No se pudo copiar", true);
    }
  });

  // ---------- Descartar ----------
  discardBtn.addEventListener("click", () => {
    if (!confirm("¿Descartar esta grabación? No se va a guardar.")) return;
    resetAll();
    toast("Grabación descartada");
  });

  function resetAll() {
    finalTranscript = "";
    chatHistory = [];
    renderTranscript();
    transcriptEmpty.classList.remove("hidden");
    renderChat();
    actions.classList.add("hidden");
    copyBtn.classList.add("hidden");
    enableChat(false);
    statusDot.className = "h-2.5 w-2.5 rounded-full bg-slate-500";
    statusText.textContent = "Listo para grabar";
    timerEl.textContent = "00:00";
  }

  // ---------- Guardar (modal) ----------
  const saveModal = $("save-modal");
  const saveTitle = $("save-title");

  function openSaveModal() {
    if (!hasTranscript()) return;
    const hoy = new Date().toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long" });
    saveTitle.value = "Clase · " + hoy;
    saveModal.classList.remove("hidden");
    setTimeout(() => saveTitle.focus(), 50);
  }
  function closeSaveModal() {
    saveModal.classList.add("hidden");
  }

  saveBtn.addEventListener("click", openSaveModal);
  $("save-cancel").addEventListener("click", closeSaveModal);
  $("save-modal-backdrop").addEventListener("click", closeSaveModal);

  $("save-confirm").addEventListener("click", async () => {
    const title = saveTitle.value.trim();
    if (!title) {
      toast("Ponele un título", true);
      return;
    }
    try {
      const res = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, transcript: finalTranscript, messages: chatHistory }),
      });
      const data = await res.json();
      if (!res.ok) {
        toast(data.error || "No se pudo guardar", true);
        return;
      }
      closeSaveModal();
      resetAll();
      toast("Sesión guardada ✓");
    } catch {
      toast("No se pudo conectar con el servidor", true);
    }
  });

  // ---------- Drawer de sesiones ----------
  const drawer = $("sessions-drawer");
  const backdrop = $("sessions-backdrop");
  const sessionsList = $("sessions-list");

  function openDrawer() {
    backdrop.classList.remove("hidden");
    drawer.classList.remove("translate-x-full");
    loadSessions();
  }
  function closeDrawer() {
    backdrop.classList.add("hidden");
    drawer.classList.add("translate-x-full");
  }
  $("open-sessions").addEventListener("click", openDrawer);
  $("close-sessions").addEventListener("click", closeDrawer);
  backdrop.addEventListener("click", closeDrawer);

  async function loadSessions() {
    try {
      const res = await fetch("/api/sessions");
      const list = await res.json();
      renderSessions(list);
    } catch {
      toast("No se pudieron cargar las sesiones", true);
    }
  }

  function renderSessions(list) {
    sessionsList.querySelectorAll(".session-card").forEach((n) => n.remove());
    const empty = $("sessions-empty");
    if (!list.length) {
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");
    for (const s of list) {
      const card = document.createElement("div");
      card.className =
        "session-card glass hover:bg-white/10 transition rounded-xl p-4 cursor-pointer flex items-start justify-between gap-3";
      card.innerHTML = `
        <div class="min-w-0">
          <p class="font-semibold truncate">${escapeHtml(s.title)}</p>
          <p class="text-xs text-slate-400 mt-0.5">${escapeHtml(s.created_at)}</p>
        </div>
        <button class="del-btn text-slate-500 hover:text-pink-400 transition shrink-0" data-id="${s.id}" title="Borrar">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/></svg>
        </button>`;
      card.addEventListener("click", (e) => {
        if (e.target.closest(".del-btn")) return;
        openSession(s.id);
      });
      card.querySelector(".del-btn").addEventListener("click", () => deleteSession(s.id));
      sessionsList.appendChild(card);
    }
  }

  async function openSession(id) {
    try {
      const res = await fetch(`/api/sessions/${id}`);
      const s = await res.json();
      if (!res.ok) {
        toast(s.error || "No se encontró la sesión", true);
        return;
      }
      finalTranscript = s.transcript + " ";
      chatHistory = (s.messages || []).map((m) => ({ role: m.role, content: m.content }));
      renderTranscript();
      transcriptEmpty.classList.add("hidden");
      renderChat();
      actions.classList.add("hidden");
      copyBtn.classList.remove("hidden");
      enableChat(true);
      statusDot.className = "h-2.5 w-2.5 rounded-full bg-indigo-400";
      statusText.textContent = "Sesión guardada";
      closeDrawer();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch {
      toast("No se pudo abrir la sesión", true);
    }
  }

  async function deleteSession(id) {
    if (!confirm("¿Borrar esta sesión guardada?")) return;
    try {
      const res = await fetch(`/api/sessions/${id}`, { method: "DELETE" });
      if (res.ok) {
        toast("Sesión borrada");
        loadSessions();
      } else {
        toast("No se pudo borrar", true);
      }
    } catch {
      toast("No se pudo conectar con el servidor", true);
    }
  }

  // ---------- Init ----------
  setupRecognition();
})();
