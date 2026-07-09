/**
 * CyberMentor Widget — Embeddable Version
 * ----------------------------------------
 * Self-contained floating chat widget for LMS integration.
 *
 * HOW IT WORKS:
 *   1. The LMS defines window.CYBERMENTOR_CONFIG (apiUrl + userId) BEFORE loading this script.
 *   2. This script injects its own styles + HTML and wires up the chat.
 *
 * If CYBERMENTOR_CONFIG is missing or userId is empty, the widget will
 * refuse to load and log a clear console error (so mis-configuration is obvious).
 */
(function () {
  "use strict";

  // ---- 1. Read configuration injected by the LMS -----------------------
  var config = window.CYBERMENTOR_CONFIG || {};
  var API_URL = (config.apiUrl || "").replace(/\/+$/, ""); // strip trailing slash
  var USER_ID = config.userId ? String(config.userId) : "";

  if (!API_URL) {
    console.error("[CyberMentor] Missing apiUrl in window.CYBERMENTOR_CONFIG. Widget not loaded.");
    return;
  }
  if (!USER_ID) {
    console.error("[CyberMentor] Missing userId in window.CYBERMENTOR_CONFIG. Widget not loaded.");
    return;
  }

  var BUBBLE_SIZE = 70;
  var SAFE_MARGIN = 12;
  var STORAGE_KEY = "cybermentor.bubblePos";

  // ---- 2. Inject styles -------------------------------------------------
  var css = ""
    + ".cm-bubble{position:fixed;bottom:24px;right:24px;width:70px;height:70px;border-radius:50%;background:#fff;cursor:pointer;box-shadow:0 8px 24px rgba(37,99,235,.35);border:3px solid #2563eb;z-index:2147483000;transition:transform .2s,box-shadow .2s,opacity .3s;user-select:none;padding:0;overflow:hidden;display:flex;align-items:center;justify-content:center}"
    + ".cm-bubble img{width:100%;height:100%;object-fit:cover;pointer-events:none}"
    + ".cm-bubble:hover{transform:scale(1.08);box-shadow:0 12px 32px rgba(37,99,235,.5)}"
    + ".cm-bubble:active{transform:scale(.95)}"
    + ".cm-bubble.cm-hidden{opacity:0;pointer-events:none;transform:scale(.5)}"
    + ".cm-popup{position:fixed;bottom:24px;right:24px;width:380px;height:560px;max-height:calc(100vh - 48px);background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.25);display:flex;flex-direction:column;overflow:hidden;z-index:2147483001;opacity:0;transform:translateY(20px) scale(.95);pointer-events:none;transition:opacity .25s,transform .25s;font-family:'Segoe UI',Tahoma,sans-serif}"
    + ".cm-popup.cm-open{opacity:1;transform:translateY(0) scale(1);pointer-events:auto}"
    + ".cm-header{background:linear-gradient(135deg,#2563eb,#7c3aed);color:#fff;padding:16px 18px;display:flex;align-items:center;gap:12px}"
    + ".cm-avatar{width:40px;height:40px;border-radius:50%;background:#fff;overflow:hidden;flex-shrink:0}"
    + ".cm-avatar img{width:100%;height:100%;object-fit:cover}"
    + ".cm-hinfo{flex:1}.cm-hinfo h2{font-size:16px;font-weight:600;margin:0}"
    + ".cm-status{font-size:12px;opacity:.9;display:flex;align-items:center;gap:6px}"
    + ".cm-dot{width:8px;height:8px;border-radius:50%;background:#10b981;display:inline-block}"
    + ".cm-close{background:rgba(255,255,255,.15);border:none;color:#fff;width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center;transition:background .2s}"
    + ".cm-close:hover{background:rgba(255,255,255,.3)}"
    + ".cm-messages{flex:1;overflow-y:auto;padding:18px 16px;display:flex;flex-direction:column;gap:12px;background:#f8fafc}"
    + ".cm-msg{max-width:80%;padding:10px 14px;border-radius:14px;line-height:1.5;font-size:14px;word-wrap:break-word;white-space:pre-wrap}"
    + ".cm-user{align-self:flex-end;background:#2563eb;color:#fff;border-bottom-right-radius:4px}"
    + ".cm-bot{align-self:flex-start;background:#fff;color:#1e293b;border:1px solid #e2e8f0;border-bottom-left-radius:4px}"
    + ".cm-hint-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:-4px;margin-bottom:4px;align-self:flex-start;max-width:80%}"
    + ".cm-hint-btn{padding:8px 14px;border:1px solid #2563eb;background:#fff;color:#2563eb;border-radius:18px;cursor:pointer;font-size:13px;font-weight:600;transition:background .2s,color .2s}"
    + ".cm-hint-btn:hover{background:#2563eb;color:#fff}"
    + ".cm-hint-btn.cm-secondary{border-color:#7c3aed;color:#7c3aed}"
    + ".cm-hint-btn.cm-secondary:hover{background:#7c3aed;color:#fff}"
    + ".cm-hint-btn:disabled{opacity:.4;cursor:not-allowed}"
    + ".cm-hint-message{align-self:flex-start;max-width:80%;padding:10px 14px;border-radius:14px;line-height:1.5;font-size:14px;background:#fef9c3;color:#713f12;border:1px solid #facc15;border-bottom-left-radius:4px}"
    + ".cm-hint-label{font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#92400e;margin-bottom:4px}"
    + ".cm-typing{align-self:flex-start;color:#94a3b8;font-style:italic;font-size:13px;padding:6px 12px;display:flex;align-items:center;gap:8px}"
    + ".cm-dots{display:inline-flex;gap:3px}.cm-dots span{width:6px;height:6px;background:#94a3b8;border-radius:50%;animation:cmbounce 1.4s infinite ease-in-out}"
    + ".cm-dots span:nth-child(2){animation-delay:.15s}.cm-dots span:nth-child(3){animation-delay:.3s}"
    + "@keyframes cmbounce{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-6px);opacity:1}}"
    + ".cm-input-area{display:flex;gap:8px;padding:12px;background:#fff;border-top:1px solid #e2e8f0}"
    + ".cm-input{flex:1;padding:10px 14px;border:1px solid #cbd5e1;border-radius:24px;font-size:14px;outline:none;transition:border-color .2s;font-family:inherit}"
    + ".cm-input:focus{border-color:#2563eb}"
    + ".cm-send{padding:10px 18px;background:#2563eb;color:#fff;border:none;border-radius:24px;cursor:pointer;font-size:14px;font-weight:600;transition:background .2s}"
    + ".cm-send:hover{background:#1d4ed8}.cm-send:disabled{opacity:.5;cursor:not-allowed}"
    + "@media(max-width:480px){.cm-popup{bottom:0;right:0;width:100%;height:100%;max-height:100vh;border-radius:0}}";

  var styleTag = document.createElement("style");
  styleTag.textContent = css;
  document.head.appendChild(styleTag);

  // ---- 3. Inject HTML ---------------------------------------------------
  var avatarUrl = API_URL + "/static/bot.jpg";

  var bubble = document.createElement("button");
  bubble.className = "cm-bubble";
  bubble.title = "Open CyberMentor";
  bubble.innerHTML = '<img src="' + avatarUrl + '" alt="CyberMentor bot" />';

  var popup = document.createElement("div");
  popup.className = "cm-popup";
  popup.innerHTML =
      '<div class="cm-header">'
    +   '<div class="cm-avatar"><img src="' + avatarUrl + '" alt="bot" /></div>'
    +   '<div class="cm-hinfo"><h2>CyberMentor</h2><div class="cm-status"><span class="cm-dot"></span>Online</div></div>'
    +   '<button class="cm-close" title="Close">\u2715</button>'
    + '</div>'
    + '<div class="cm-messages"></div>'
    + '<div class="cm-input-area">'
    +   '<input class="cm-input" type="text" placeholder="Ask a cybersecurity question..." />'
    +   '<button class="cm-send">Send</button>'
    + '</div>';

  document.body.appendChild(bubble);
  document.body.appendChild(popup);

  var closeBtn = popup.querySelector(".cm-close");
  var messagesEl = popup.querySelector(".cm-messages");
  var inputEl = popup.querySelector(".cm-input");
  var sendBtn = popup.querySelector(".cm-send");

  // ---- 4. Bubble drag + persistence ------------------------------------
  function loadBubblePosition() {
    try { var raw = localStorage.getItem(STORAGE_KEY); return raw ? JSON.parse(raw) : null; }
    catch (e) { return null; }
  }
  function saveBubblePosition(left, top) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ left: left, top: top })); } catch (e) {}
  }
  function clampToViewport(left, top) {
    var maxLeft = window.innerWidth - BUBBLE_SIZE - SAFE_MARGIN;
    var maxTop = window.innerHeight - BUBBLE_SIZE - SAFE_MARGIN;
    return { left: Math.max(SAFE_MARGIN, Math.min(left, maxLeft)), top: Math.max(SAFE_MARGIN, Math.min(top, maxTop)) };
  }
  function setBubblePosition(left, top) {
    var c = clampToViewport(left, top);
    bubble.style.left = c.left + "px"; bubble.style.top = c.top + "px";
    bubble.style.right = "auto"; bubble.style.bottom = "auto";
    return c;
  }
  function initBubblePosition() {
    var saved = loadBubblePosition();
    if (saved) setBubblePosition(saved.left, saved.top);
  }
  window.addEventListener("resize", function () {
    var saved = loadBubblePosition();
    if (saved) { var c = setBubblePosition(saved.left, saved.top); saveBubblePosition(c.left, c.top); }
  });

  var isDragging = false, dragMoved = false, startX = 0, startY = 0, offsetX = 0, offsetY = 0;
  var DRAG_THRESHOLD = 5;
  function getEventCoords(e) {
    if (e.touches && e.touches[0]) return { x: e.touches[0].clientX, y: e.touches[0].clientY };
    return { x: e.clientX, y: e.clientY };
  }
  function onPointerDown(e) {
    var c = getEventCoords(e); startX = c.x; startY = c.y;
    var r = bubble.getBoundingClientRect(); offsetX = c.x - r.left; offsetY = c.y - r.top;
    isDragging = true; dragMoved = false;
    bubble.style.transition = "none"; bubble.style.cursor = "grabbing";
  }
  function onPointerMove(e) {
    if (!isDragging) return;
    var c = getEventCoords(e);
    if (!dragMoved && Math.hypot(c.x - startX, c.y - startY) > DRAG_THRESHOLD) dragMoved = true;
    if (dragMoved) { e.preventDefault(); setBubblePosition(c.x - offsetX, c.y - offsetY); }
  }
  function onPointerUp() {
    if (!isDragging) return;
    isDragging = false;
    bubble.style.transition = ""; bubble.style.cursor = "pointer";
    if (dragMoved) { var r = bubble.getBoundingClientRect(); saveBubblePosition(r.left, r.top); }
    else { openChat(); }
  }
  bubble.addEventListener("mousedown", onPointerDown);
  document.addEventListener("mousemove", onPointerMove);
  document.addEventListener("mouseup", onPointerUp);
  bubble.addEventListener("touchstart", onPointerDown, { passive: true });
  document.addEventListener("touchmove", onPointerMove, { passive: false });
  document.addEventListener("touchend", onPointerUp);

  // ---- 5. Open / close --------------------------------------------------
  var historyLoaded = false;
  function openChat() {
    popup.classList.add("cm-open");
    bubble.classList.add("cm-hidden");
    setTimeout(function () { inputEl.focus(); }, 250);
    if (!historyLoaded) { loadHistory(); historyLoaded = true; }
  }
  function closeChat() {
    popup.classList.remove("cm-open");
    bubble.classList.remove("cm-hidden");
  }
  closeBtn.addEventListener("click", closeChat);

  function loadHistory() {
    var loadingEl = document.createElement("div");
    loadingEl.className = "cm-typing";
    loadingEl.innerHTML = 'Loading your conversation <span class="cm-dots"><span></span><span></span><span></span></span>';
    messagesEl.appendChild(loadingEl);
    fetch(API_URL + "/history?userId=" + encodeURIComponent(USER_ID) + "&limit=15")
      .then(function (r) { return r.json(); })
      .then(function (messages) {
        loadingEl.remove();
        if (!Array.isArray(messages) || messages.length === 0) {
          addMessage("Hi! I'm CyberMentor \uD83D\uDC4B Ask me anything about cybersecurity, ethical hacking, or networking fundamentals.", "bot");
          return;
        }
        messages.forEach(function (msg) { addMessage(msg.text, msg.role === "user" ? "user" : "bot"); });
      })
      .catch(function () {
        loadingEl.remove();
        addMessage("\u26A0\uFE0F Couldn't load previous conversation. Starting fresh.", "bot");
      });
  }

  // ---- 6. Rendering -----------------------------------------------------
  function addMessage(text, who) {
    var div = document.createElement("div");
    div.className = "cm-msg " + (who === "user" ? "cm-user" : "cm-bot");
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }
  function addHintMessage(level, text) {
    var wrapper = document.createElement("div");
    wrapper.className = "cm-hint-message";
    var label = document.createElement("div");
    label.className = "cm-hint-label";
    label.textContent = "\uD83D\uDCA1 Hint " + level;
    var body = document.createElement("div");
    body.textContent = text;
    wrapper.appendChild(label); wrapper.appendChild(body);
    messagesEl.appendChild(wrapper);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  function addHintActions(question, hints) {
    var actions = document.createElement("div");
    actions.className = "cm-hint-actions";
    var hintBtn = document.createElement("button");
    hintBtn.className = "cm-hint-btn";
    hintBtn.textContent = "\uD83D\uDCA1 Show hint";
    var fullBtn = document.createElement("button");
    fullBtn.className = "cm-hint-btn cm-secondary";
    fullBtn.textContent = "\uD83D\uDE80 Show full answer";
    actions.appendChild(hintBtn); actions.appendChild(fullBtn);
    messagesEl.appendChild(actions);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    var currentHint = 0;
    hintBtn.addEventListener("click", function () {
      currentHint += 1;
      var key = "hint" + currentHint;
      if (hints[key]) {
        addHintMessage(currentHint, hints[key]);
        if (currentHint < 3) { hintBtn.textContent = "\uD83D\uDCA1 Show next hint"; }
        else { hintBtn.disabled = true; hintBtn.textContent = "\u2705 All hints shown"; }
      }
    });
    fullBtn.addEventListener("click", function () {
      hintBtn.disabled = true; fullBtn.disabled = true;
      sendMessage('Please give me the full direct answer to: "' + question + '"', true);
    });
  }

  // ---- 7. Send ----------------------------------------------------------
  function sendMessage(forcedText, isFullAnswerRequest) {
    var text = forcedText || inputEl.value.trim();
    if (!text) return;
    if (!forcedText) addMessage(text, "user");
    inputEl.value = "";
    sendBtn.disabled = true;

    var typingEl = document.createElement("div");
    typingEl.className = "cm-typing";
    typingEl.innerHTML = 'CyberMentor is typing <span class="cm-dots"><span></span><span></span><span></span></span>';
    messagesEl.appendChild(typingEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    fetch(API_URL + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: USER_ID,
        query: text,
        metadata: { courseId: config.courseId || null, chapterId: config.chapterId || null }
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        typingEl.remove();
        var am = data.assistantMessage;
        if (!am) { addMessage("\u26A0\uFE0F Unexpected server response.", "bot"); return; }
        addMessage(am.text, "bot");
        if (am.topicHint === "how_to" && am.hints) { addHintActions(text, am.hints); }
      })
      .catch(function () {
        typingEl.remove();
        addMessage("\u26A0\uFE0F Sorry, I couldn't reach the server. Please try again.", "bot");
      })
      .then(function () {
        sendBtn.disabled = false;
        inputEl.focus();
      });
  }

  sendBtn.addEventListener("click", function () { sendMessage(); });
  inputEl.addEventListener("keypress", function (e) { if (e.key === "Enter") sendMessage(); });

  initBubblePosition();
})();
