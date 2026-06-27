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

  // ---------- Grabación de audio (MediaRecorder + Whisper/Groq) ----------
  let mediaStream = null;
  let mediaRecorder = null;
  let segmentTimer = null;
  let transcribeChain = Promise.resolve();
  let pendingChunks = 0;
  const SEGMENT_MS = 10000; // largo de cada fragmento que se transcribe
  let transcriptLang = "original"; // idioma mostrado en el recuadro
  let translationCache = {}; // { español: "...", inglés: "..." }

  function supportsRecording() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
  }

  function pickMime() {
    const opts = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"];
    for (const m of opts) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return m;
    }
    return "";
  }

  function setupRecorder() {
    if (!supportsRecording()) {
      $("browser-warning").classList.remove("hidden");
      recordBtn.disabled = true;
      recordBtn.classList.add("opacity-40", "cursor-not-allowed");
    }
  }

  function renderTranscript() {
    if (hasTranscript()) transcriptEmpty.classList.add("hidden");
    // Solo refrescamos el texto en vivo cuando estamos viendo el original.
    if (transcriptLang === "original") {
      transcriptFinal.textContent = finalTranscript;
      transcriptInterim.textContent = pendingChunks > 0 ? " ⏳ transcribiendo..." : "";
    }
    transcriptBox.scrollTop = transcriptBox.scrollHeight;
  }

  function resetTranscriptLang() {
    transcriptLang = "original";
    translationCache = {};
    const sel = $("transcript-lang");
    if (sel) {
      sel.value = "original";
      sel.classList.add("hidden");
    }
  }

  function showTranscriptLangToggle() {
    const sel = $("transcript-lang");
    if (sel && hasTranscript()) sel.classList.remove("hidden");
  }

  async function onTranscriptLangChange() {
    const sel = $("transcript-lang");
    const lang = sel.value;
    transcriptLang = lang;
    transcriptInterim.textContent = "";
    if (lang === "original") {
      transcriptFinal.textContent = finalTranscript;
      return;
    }
    if (translationCache[lang]) {
      transcriptFinal.textContent = translationCache[lang];
      return;
    }
    transcriptFinal.textContent = "Traduciendo a " + lang + "...";
    try {
      const d = await apiPost("/api/translate", {
        transcript: finalTranscript,
        target: lang,
        glossary: getGlossary(),
      });
      translationCache[lang] = d.translation;
      if (transcriptLang === lang) transcriptFinal.textContent = d.translation;
    } catch (e) {
      toast(e.message, true);
      sel.value = "original";
      transcriptLang = "original";
      transcriptFinal.textContent = finalTranscript;
    }
  }

  // ---------- Control de grabación ----------
  const MIC_ICON =
    '<svg class="h-9 w-9 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>';
  const STOP_ICON =
    '<svg class="h-8 w-8 text-white" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';

  function extFor(type) {
    if (type.includes("mp4")) return "mp4";
    if (type.includes("ogg")) return "ogg";
    return "webm";
  }

  function queueTranscription(blob, type) {
    pendingChunks++;
    renderTranscript();
    transcribeChain = transcribeChain.then(async () => {
      const fd = new FormData();
      fd.append("audio", blob, "segmento." + extFor(type));
      try {
        const res = await fetch("/api/transcribe", { method: "POST", body: fd });
        if (res.status === 401) {
          window.location = "/login";
          return;
        }
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.text) {
          const sep = finalTranscript && !finalTranscript.endsWith(" ") ? " " : "";
          finalTranscript += sep + data.text.trim() + " ";
          transcriptEmpty.classList.add("hidden");
        } else if (!res.ok) {
          toast(data.error || "Error al transcribir un fragmento", true);
        }
      } catch {
        toast("No se pudo transcribir un fragmento", true);
      } finally {
        pendingChunks--;
        renderTranscript();
      }
    });
  }

  function startSegment() {
    const mime = pickMime();
    const chunks = [];
    mediaRecorder = mime
      ? new MediaRecorder(mediaStream, { mimeType: mime, audioBitsPerSecond: 64000 })
      : new MediaRecorder(mediaStream);
    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size) chunks.push(e.data);
    };
    mediaRecorder.onstop = () => {
      const type = mediaRecorder.mimeType || mime || "audio/webm";
      const blob = new Blob(chunks, { type });
      const wasRecording = isRecording;
      if (wasRecording) {
        startSegment(); // arranca el próximo segmento ya, mínimo hueco
      } else if (mediaStream) {
        mediaStream.getTracks().forEach((t) => t.stop());
      }
      if (blob.size > 1000) queueTranscription(blob, type);
      if (!wasRecording) transcribeChain.then(finalizeAfterStop);
    };
    mediaRecorder.start();
  }

  async function startRecording() {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: { noiseSuppression: true, echoCancellation: true, autoGainControl: true },
      });
    } catch {
      toast("No se pudo acceder al micrófono. Dale permiso al navegador.", true);
      return;
    }
    finalTranscript = "";
    chatHistory = [];
    resetTranscriptLang();
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

    startSegment();
    segmentTimer = setInterval(() => {
      if (mediaRecorder && mediaRecorder.state === "recording") mediaRecorder.stop();
    }, SEGMENT_MS);

    recordBtn.classList.add("rec-pulse");
    recordIcon.innerHTML = STOP_ICON;
    statusDot.className = "h-2.5 w-2.5 rounded-full bg-pink-500 animate-pulse";
    statusText.textContent = "Grabando...";
  }

  function finalizeAfterStop() {
    if (hasTranscript()) {
      statusDot.className = "h-2.5 w-2.5 rounded-full bg-emerald-500";
      statusText.textContent = "Grabación lista";
      actions.classList.remove("hidden");
      copyBtn.classList.remove("hidden");
      showTranscriptLangToggle();
      enableChat(true);
    } else {
      statusDot.className = "h-2.5 w-2.5 rounded-full bg-slate-500";
      statusText.textContent = "No se detectó audio";
    }
    renderTranscript();
  }

  function stopRecording() {
    isRecording = false;
    clearInterval(timerId);
    clearInterval(segmentTimer);
    recordBtn.classList.remove("rec-pulse");
    recordIcon.innerHTML = MIC_ICON;
    statusDot.className = "h-2.5 w-2.5 rounded-full bg-amber-400 animate-pulse";
    statusText.textContent = "Procesando audio...";
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop(); // dispara la transcripción del último fragmento
    } else {
      transcribeChain.then(finalizeAfterStop);
    }
  }

  recordBtn.addEventListener("click", () => {
    if (!supportsRecording()) return;
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

    let assistantText = "";
    let inner = null; // burbuja de la IA, se crea con el primer token
    let gotError = false;

    const ensureBubble = () => {
      if (!inner) {
        if (typing.parentNode) typing.remove();
        inner = addBubble("assistant", "").querySelector("div");
      }
    };

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript: finalTranscript,
          question,
          messages: chatHistory.slice(0, -1),
          glossary: getGlossary(),
        }),
      });
      if (res.status === 401) {
        window.location = "/login";
        return;
      }
      if (!res.ok) {
        if (typing.parentNode) typing.remove();
        const data = await res.json().catch(() => ({}));
        toast(data.error || "Error al consultar la IA", true);
        chatHistory.pop();
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop(); // el último puede estar incompleto
        for (const evt of events) {
          let type = "message";
          let dataStr = "";
          for (const line of evt.split("\n")) {
            if (line.startsWith("event:")) type = line.slice(6).trim();
            else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
          }
          if (!dataStr) continue;
          if (type === "error") {
            gotError = true;
            let msg = "Error de la IA";
            try { msg = JSON.parse(dataStr).error || msg; } catch {}
            toast(msg, true);
          } else if (type === "message") {
            try {
              const payload = JSON.parse(dataStr);
              if (payload.text) {
                ensureBubble();
                assistantText += payload.text;
                inner.textContent = assistantText;
                chatMessages.scrollTop = chatMessages.scrollHeight;
              }
            } catch {}
          }
        }
      }

      if (typing.parentNode) typing.remove();
      if (gotError || !assistantText) {
        chatHistory.pop();
        if (inner) inner.closest(".bubble").remove();
      } else {
        chatHistory.push({ role: "assistant", content: assistantText });
      }
    } catch (err) {
      if (typing.parentNode) typing.remove();
      chatHistory.pop();
      if (inner) inner.closest(".bubble").remove();
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
    const text =
      transcriptLang === "original"
        ? finalTranscript
        : translationCache[transcriptLang] || finalTranscript;
    try {
      await navigator.clipboard.writeText(text.trim());
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
    resetTranscriptLang();
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
      resetTranscriptLang();
      renderTranscript();
      transcriptEmpty.classList.add("hidden");
      renderChat();
      actions.classList.add("hidden");
      copyBtn.classList.remove("hidden");
      showTranscriptLangToggle();
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

  // ---------- Glosario ----------
  const glossaryText = $("glossary-text");

  function getGlossary() {
    return (glossaryText.value || "").trim();
  }
  function loadGlossary() {
    const g = localStorage.getItem("notaia_glossary");
    if (g) glossaryText.value = g;
  }
  glossaryText.addEventListener("input", () => {
    localStorage.setItem("notaia_glossary", glossaryText.value);
  });
  $("btn-glossary").addEventListener("click", () => {
    $("glossary-box").classList.toggle("hidden");
  });

  // ---------- Modal de resultado ----------
  const resultModal = $("result-modal");
  let resultCopyText = "";
  let currentIcsTasks = null;
  let resultIsImage = false;

  function showResult(
    title,
    { loading = false, text = null, mermaid = null, html = null, copyText = null, icsTasks = null } = {}
  ) {
    $("result-title").textContent = title;
    resultModal.classList.remove("hidden");
    $("result-loading").classList.toggle("hidden", !loading);
    $("result-text").classList.add("hidden");
    $("result-html").classList.add("hidden");
    $("result-mermaid").classList.add("hidden");
    $("result-copy").classList.toggle("hidden", loading);
    currentIcsTasks = icsTasks;
    $("result-ics").classList.toggle("hidden", !(icsTasks && icsTasks.length));
    resultIsImage = mermaid !== null;
    $("result-png").classList.toggle("hidden", mermaid === null || loading);
    if (text !== null) {
      $("result-text").textContent = text;
      $("result-text").classList.remove("hidden");
      resultCopyText = text;
    }
    if (html !== null) {
      $("result-html").innerHTML = html;
      $("result-html").classList.remove("hidden");
      resultCopyText = copyText || "";
    }
    if (mermaid !== null) {
      renderMermaid(mermaid);
      $("result-mermaid").classList.remove("hidden");
      resultCopyText = mermaid;
    }
  }
  function closeResult() {
    resultModal.classList.add("hidden");
  }
  $("result-close").addEventListener("click", closeResult);
  $("result-backdrop").addEventListener("click", closeResult);
  $("result-copy").addEventListener("click", async () => {
    if (resultIsImage) {
      await copyMindmapImage();
      return;
    }
    try {
      await navigator.clipboard.writeText(resultCopyText);
      toast("Copiado");
    } catch {
      toast("No se pudo copiar", true);
    }
  });

  // Convierte el SVG del mapa mental en una imagen PNG (con fondo de la app).
  function svgToPngBlob(svg, scale = 2) {
    return new Promise((resolve, reject) => {
      const vb = svg.viewBox && svg.viewBox.baseVal;
      const rect = svg.getBoundingClientRect();
      const w = (vb && vb.width) || rect.width || 800;
      const h = (vb && vb.height) || rect.height || 600;
      const xml = new XMLSerializer().serializeToString(svg);
      const src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(xml)));
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(w * scale);
        canvas.height = Math.round(h * scale);
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#0b1020";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("toBlob"))), "image/png");
      };
      img.onerror = reject;
      img.src = src;
    });
  }

  async function copyMindmapImage() {
    const svg = $("result-mermaid").querySelector("svg");
    if (!svg) return;
    try {
      const blob = await svgToPngBlob(svg);
      await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
      toast("Imagen copiada ✓");
    } catch {
      toast("Tu navegador no deja copiar imágenes; usá 'Descargar imagen'", true);
    }
  }

  $("result-png").addEventListener("click", async () => {
    const svg = $("result-mermaid").querySelector("svg");
    if (!svg) return;
    try {
      const blob = await svgToPngBlob(svg);
      const file = new File([blob], "mapa-mental.png", { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: "Mapa mental" });
        return;
      }
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "mapa-mental.png";
      a.click();
      URL.revokeObjectURL(a.href);
      toast("Imagen descargada");
    } catch {
      toast("No se pudo generar la imagen", true);
    }
  });

  function buildIcs(tasks) {
    const pad = (n) => String(n).padStart(2, "0");
    let ics = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//NotaIA//ES\r\n";
    tasks.forEach((t, i) => {
      let d = new Date(t.due);
      if (isNaN(d.getTime())) d = new Date();
      const dt = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
      ics += "BEGIN:VEVENT\r\n";
      ics += `UID:notaia-${Date.now()}-${i}@notaia\r\n`;
      ics += `DTSTART;VALUE=DATE:${dt}\r\n`;
      ics += `SUMMARY:${(t.task || "").replace(/[\r\n]+/g, " ")}\r\n`;
      if (t.due) ics += `DESCRIPTION:Vence: ${t.due.replace(/[\r\n]+/g, " ")}\r\n`;
      ics += "END:VEVENT\r\n";
    });
    ics += "END:VCALENDAR\r\n";
    return ics;
  }

  $("result-ics").addEventListener("click", () => {
    if (!currentIcsTasks || !currentIcsTasks.length) return;
    const blob = new Blob([buildIcs(currentIcsTasks)], { type: "text/calendar;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "tareas.ics";
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Calendario .ics descargado");
  });

  async function renderMermaid(code) {
    const container = $("result-mermaid");
    container.innerHTML = "";
    try {
      const { svg } = await window.mermaid.render("mm" + Date.now(), code);
      container.innerHTML = svg;
    } catch {
      container.innerHTML =
        '<pre class="text-xs text-pink-300 whitespace-pre-wrap text-left">No se pudo dibujar el diagrama. Codigo generado:\n\n' +
        escapeHtml(code) +
        "</pre>";
    }
  }

  // ---------- Herramientas IA ----------
  async function apiPost(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.status === 401) {
      window.location = "/login";
      throw new Error("Sesión expirada");
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Error del servidor");
    return data;
  }

  function requireTranscript() {
    if (!hasTranscript()) {
      toast("Primero grabá o abrí una sesión", true);
      return false;
    }
    return true;
  }

  async function doSummary() {
    if (!requireTranscript()) return;
    const type = $("summary-type").value;
    showResult("Resumen", { loading: true });
    try {
      const d = await apiPost("/api/summary", {
        transcript: finalTranscript,
        type,
        glossary: getGlossary(),
      });
      showResult("Resumen", { text: d.summary });
    } catch (e) {
      closeResult();
      toast(e.message, true);
    }
  }

  async function doMindmap() {
    if (!requireTranscript()) return;
    showResult("Mapa mental", { loading: true });
    try {
      const d = await apiPost("/api/mindmap", {
        transcript: finalTranscript,
        glossary: getGlossary(),
      });
      showResult("Mapa mental", { mermaid: d.mermaid });
    } catch (e) {
      closeResult();
      toast(e.message, true);
    }
  }

  $("btn-summary").addEventListener("click", doSummary);
  $("btn-mindmap").addEventListener("click", doMindmap);

  // ---------- Exportar ----------
  function buildMarkdown() {
    let md = "# Transcripción\n\n" + finalTranscript.trim() + "\n";
    if (chatHistory.length) {
      md += "\n# Chat\n\n";
      for (const m of chatHistory) {
        md += (m.role === "user" ? "**Vos:** " : "**Claude:** ") + m.content + "\n\n";
      }
    }
    return md;
  }
  $("btn-export-md").addEventListener("click", () => {
    if (!requireTranscript()) return;
    const blob = new Blob([buildMarkdown()], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "notaia.md";
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Archivo .md descargado");
  });
  $("btn-print").addEventListener("click", () => {
    if (!requireTranscript()) return;
    window.print();
  });

  // ---------- Flashcards: generar y guardar ----------
  let generatedCards = [];

  function closeFcModal() {
    $("fc-modal").classList.add("hidden");
  }

  function renderGeneratedCards() {
    const list = $("fc-list");
    list.innerHTML = "";
    generatedCards.forEach((c, i) => {
      const el = document.createElement("div");
      el.className = "glass rounded-xl p-3";
      el.innerHTML =
        '<p class="text-sm font-medium">' + (i + 1) + ". " + escapeHtml(c.question) + "</p>" +
        '<p class="text-sm text-slate-400 mt-1">' + escapeHtml(c.answer) + "</p>";
      list.appendChild(el);
    });
  }

  async function doFlashcards() {
    if (!requireTranscript()) return;
    $("fc-modal").classList.remove("hidden");
    $("fc-loading").classList.remove("hidden");
    $("fc-list").classList.add("hidden");
    $("fc-actions").classList.add("hidden");
    try {
      const d = await apiPost("/api/flashcards/generate", {
        transcript: finalTranscript,
        glossary: getGlossary(),
        count: 8,
      });
      generatedCards = d.cards || [];
      renderGeneratedCards();
      $("fc-loading").classList.add("hidden");
      $("fc-list").classList.remove("hidden");
      $("fc-actions").classList.remove("hidden");
    } catch (e) {
      closeFcModal();
      toast(e.message, true);
    }
  }

  $("btn-flashcards").addEventListener("click", doFlashcards);
  $("fc-close").addEventListener("click", closeFcModal);
  $("fc-cancel").addEventListener("click", closeFcModal);
  $("fc-backdrop").addEventListener("click", closeFcModal);
  $("fc-save").addEventListener("click", async () => {
    if (!generatedCards.length) return;
    try {
      const d = await apiPost("/api/flashcards", { cards: generatedCards });
      closeFcModal();
      toast(d.saved + " tarjetas guardadas ✓");
      refreshDueBadge();
    } catch (e) {
      toast(e.message, true);
    }
  });

  // ---------- Estudiar (repaso espaciado) ----------
  let studyQueue = [];
  let studyIndex = 0;
  let studyTotal = 0;

  async function refreshDueBadge() {
    try {
      const res = await fetch("/api/flashcards/due");
      if (!res.ok) return;
      const d = await res.json();
      const due = d.stats ? d.stats.due : 0;
      const badge = $("study-due-badge");
      if (due > 0) {
        badge.textContent = due;
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    } catch {
      /* sin badge si falla */
    }
  }

  function showStudyCard() {
    const card = studyQueue[studyIndex];
    $("study-card").classList.remove("hidden");
    $("study-question").textContent = card.question;
    $("study-answer").textContent = card.answer;
    $("study-answer-wrap").classList.add("hidden");
    $("study-grades").classList.add("hidden");
    $("study-show").classList.remove("hidden");
    $("study-progress").textContent = studyIndex + 1 + " / " + studyTotal;
  }

  function finishStudy() {
    $("study-card").classList.add("hidden");
    $("study-empty").classList.remove("hidden");
    $("study-progress").textContent = "";
    refreshDueBadge();
  }

  async function openStudy() {
    $("study-modal").classList.remove("hidden");
    $("study-card").classList.add("hidden");
    $("study-empty").classList.add("hidden");
    $("study-progress").textContent = "";
    try {
      const res = await fetch("/api/flashcards/due");
      if (res.status === 401) {
        window.location = "/login";
        return;
      }
      const d = await res.json();
      studyQueue = d.cards || [];
      studyTotal = studyQueue.length;
      studyIndex = 0;
      if (!studyQueue.length) {
        $("study-empty").classList.remove("hidden");
      } else {
        showStudyCard();
      }
    } catch {
      toast("No se pudieron cargar las tarjetas", true);
    }
  }

  function closeStudy() {
    $("study-modal").classList.add("hidden");
    refreshDueBadge();
  }

  $("open-study").addEventListener("click", openStudy);
  $("study-close").addEventListener("click", closeStudy);
  $("study-backdrop").addEventListener("click", closeStudy);
  $("study-show").addEventListener("click", () => {
    $("study-answer-wrap").classList.remove("hidden");
    $("study-show").classList.add("hidden");
    $("study-grades").classList.remove("hidden");
  });
  document.querySelectorAll(".study-grade").forEach((b) => {
    b.addEventListener("click", async () => {
      const card = studyQueue[studyIndex];
      const quality = parseInt(b.dataset.q, 10);
      try {
        await apiPost("/api/flashcards/" + card.id + "/grade", { quality });
      } catch (e) {
        toast(e.message, true);
        return;
      }
      studyIndex++;
      if (studyIndex >= studyQueue.length) {
        finishStudy();
      } else {
        showStudyCard();
      }
    });
  });

  // ---------- Secciones colapsables ----------
  function setupCollapse(toggleId, contentId, chevronId) {
    const t = $(toggleId);
    const c = $(contentId);
    const ch = $(chevronId);
    if (!t || !c) return;
    t.addEventListener("click", () => {
      const nowHidden = c.classList.toggle("hidden");
      if (ch) ch.classList.toggle("rotate-180", !nowHidden);
    });
  }

  // ---------- Pulir texto ----------
  async function doPolish() {
    if (!requireTranscript()) return;
    const btn = $("btn-polish");
    btn.disabled = true;
    btn.textContent = "Puliendo...";
    try {
      const d = await apiPost("/api/polish", {
        transcript: finalTranscript,
        glossary: getGlossary(),
      });
      finalTranscript = d.polished.endsWith(" ") ? d.polished : d.polished + " ";
      translationCache = {};
      transcriptLang = "original";
      const sel = $("transcript-lang");
      if (sel) sel.value = "original";
      renderTranscript();
      toast("Texto pulido ✓");
    } catch (e) {
      toast(e.message, true);
    } finally {
      btn.disabled = false;
      btn.textContent = "Pulir texto";
    }
  }

  // ---------- Tareas y fechas ----------
  async function doTasks() {
    if (!requireTranscript()) return;
    showResult("Tareas y fechas", { loading: true });
    try {
      const d = await apiPost("/api/tasks", {
        transcript: finalTranscript,
        glossary: getGlossary(),
      });
      const items = d.tasks || [];
      if (!items.length) {
        showResult("Tareas y fechas", {
          html: '<p class="text-slate-400">No se detectaron tareas ni fechas en esta clase.</p>',
        });
        return;
      }
      const rows = items
        .map(
          (t) =>
            `<li class="py-2 border-b border-white/10 flex justify-between gap-3"><span>${escapeHtml(
              t.task
            )}</span>${t.due ? `<span class="text-purple-300 shrink-0">${escapeHtml(t.due)}</span>` : ""}</li>`
        )
        .join("");
      const copyText = items.map((t) => "- " + t.task + (t.due ? " (" + t.due + ")" : "")).join("\n");
      showResult("Tareas y fechas", {
        html: `<ul>${rows}</ul>`,
        copyText,
        icsTasks: items.filter((t) => t.due),
      });
    } catch (e) {
      closeResult();
      toast(e.message, true);
    }
  }

  // ---------- Cuadro comparativo ----------
  async function doTable() {
    if (!requireTranscript()) return;
    showResult("Cuadro comparativo", { loading: true });
    try {
      const d = await apiPost("/api/table", {
        transcript: finalTranscript,
        glossary: getGlossary(),
      });
      const t = d.table || {};
      if (!t.headers || !t.headers.length) {
        showResult("Cuadro comparativo", {
          html: '<p class="text-slate-400">No se pudo armar el cuadro.</p>',
        });
        return;
      }
      const thead = `<tr>${t.headers
        .map((h) => `<th class="text-left p-2 border-b border-white/20 font-semibold">${escapeHtml(h)}</th>`)
        .join("")}</tr>`;
      const tbody = (t.rows || [])
        .map(
          (r) =>
            `<tr>${r.map((c) => `<td class="p-2 border-b border-white/10 align-top">${escapeHtml(c)}</td>`).join("")}</tr>`
        )
        .join("");
      const html = `${
        t.title ? `<p class="font-semibold mb-3">${escapeHtml(t.title)}</p>` : ""
      }<div class="overflow-x-auto"><table class="w-full text-sm">${thead}${tbody}</table></div>`;
      const copyText = [t.headers.join("\t"), ...(t.rows || []).map((r) => r.join("\t"))].join("\n");
      showResult("Cuadro comparativo", { html, copyText });
    } catch (e) {
      closeResult();
      toast(e.message, true);
    }
  }

  // ---------- Cuestionario autoevaluable ----------
  let quizData = [];

  function renderQuiz() {
    $("quiz-body").innerHTML = quizData
      .map((q, qi) => {
        const opts = q.options
          .map(
            (o, oi) =>
              `<label class="quiz-opt flex items-center gap-2 rounded-lg px-3 py-2 cursor-pointer hover:bg-white/5" data-q="${qi}" data-o="${oi}"><input type="radio" name="q${qi}" value="${oi}" class="accent-purple-500"><span>${escapeHtml(o)}</span></label>`
          )
          .join("");
        return `<div class="quiz-q" data-q="${qi}"><p class="font-medium mb-2">${qi + 1}. ${escapeHtml(
          q.question
        )}</p><div class="space-y-1">${opts}</div><p class="quiz-exp hidden text-xs text-slate-400 mt-2"></p></div>`;
      })
      .join("");
  }

  async function doQuiz() {
    if (!requireTranscript()) return;
    $("quiz-modal").classList.remove("hidden");
    $("quiz-loading").classList.remove("hidden");
    $("quiz-body").classList.add("hidden");
    $("quiz-actions").classList.add("hidden");
    $("quiz-score").textContent = "";
    try {
      const d = await apiPost("/api/quiz", {
        transcript: finalTranscript,
        glossary: getGlossary(),
        count: 5,
      });
      quizData = d.quiz || [];
      renderQuiz();
      $("quiz-loading").classList.add("hidden");
      $("quiz-body").classList.remove("hidden");
      $("quiz-actions").classList.remove("hidden");
      $("quiz-submit").disabled = false;
    } catch (e) {
      $("quiz-modal").classList.add("hidden");
      toast(e.message, true);
    }
  }

  function closeQuiz() {
    $("quiz-modal").classList.add("hidden");
  }
  $("quiz-close").addEventListener("click", closeQuiz);
  $("quiz-backdrop").addEventListener("click", closeQuiz);
  $("quiz-submit").addEventListener("click", () => {
    let score = 0;
    quizData.forEach((q, qi) => {
      const sel = $("quiz-body").querySelector(`input[name="q${qi}"]:checked`);
      const chosen = sel ? parseInt(sel.value, 10) : -1;
      if (chosen === q.correct) score++;
      const qEl = $("quiz-body").querySelector(`.quiz-q[data-q="${qi}"]`);
      qEl.querySelectorAll(".quiz-opt").forEach((lab) => {
        const oi = parseInt(lab.dataset.o, 10);
        if (oi === q.correct) lab.classList.add("bg-emerald-500/20");
        else if (oi === chosen) lab.classList.add("bg-pink-500/20");
      });
      const exp = qEl.querySelector(".quiz-exp");
      if (q.explanation) {
        exp.textContent = "💡 " + q.explanation;
        exp.classList.remove("hidden");
      }
    });
    $("quiz-score").textContent = `Puntaje: ${score}/${quizData.length}`;
    $("quiz-submit").disabled = true;
  });

  $("btn-polish").addEventListener("click", doPolish);
  $("btn-tasks").addEventListener("click", doTasks);
  $("btn-table").addEventListener("click", doTable);
  $("btn-quiz").addEventListener("click", doQuiz);

  // ---------- Init ----------
  setupCollapse("tools-toggle", "tools-content", "tools-chevron");
  setupCollapse("chat-toggle", "chat-content", "chat-chevron");
  $("transcript-lang").addEventListener("change", onTranscriptLangChange);
  if (window.mermaid) {
    window.mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "loose" });
  }
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
  loadGlossary();
  refreshDueBadge();
  setupRecorder();
})();
