(function () {
  const token = document.currentScript.getAttribute("data-token");
  const API_URL = document.currentScript.getAttribute("data-api-url") || "https://everydayai-backend-production.up.railway.app";

  if (!token) {
    console.error("EverydayAI Widget: No data-token provided");
    return;
  }

  let threadId = localStorage.getItem("everydayai_thread_" + token) || null;
  let isOpen = false;

  const styles = `
    #everydayai-widget * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'JetBrains Mono', monospace, sans-serif; }
    #everydayai-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 99999;
      width: 56px; height: 56px; border-radius: 50%;
      background: #ff5500; border: none; cursor: pointer;
      box-shadow: 0 4px 20px rgba(255,85,0,0.4);
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s ease;
    }
    #everydayai-btn:hover { transform: scale(1.1); box-shadow: 0 6px 28px rgba(255,85,0,0.6); }
    #everydayai-btn svg { width: 24px; height: 24px; fill: white; }
    #everydayai-window {
      position: fixed; bottom: 92px; right: 24px; z-index: 99998;
      width: 340px; height: 480px;
      background: #111111; border: 1px solid #222;
      border-top: 2px solid #ff5500; border-radius: 8px;
      display: none; flex-direction: column;
      box-shadow: 0 8px 40px rgba(0,0,0,0.6);
      overflow: hidden;
    }
    #everydayai-window.open { display: flex; }
    #everydayai-header {
      padding: 12px 16px; background: #0a0a0a;
      border-bottom: 1px solid #222;
      display: flex; align-items: center; justify-content: space-between;
    }
    #everydayai-header-left { display: flex; align-items: center; gap: 8px; }
    #everydayai-status { width: 8px; height: 8px; border-radius: 50%; background: #00ff88; }
    #everydayai-title { font-size: 12px; color: #e8e8e8; font-weight: 500; }
    #everydayai-close { background: none; border: none; color: #555; cursor: pointer; font-size: 16px; padding: 2px 6px; transition: color 0.15s; }
    #everydayai-close:hover { color: #ff5500; }
    #everydayai-messages {
      flex: 1; overflow-y: auto; padding: 14px;
      display: flex; flex-direction: column; gap: 10px;
    }
    #everydayai-messages::-webkit-scrollbar { width: 3px; }
    #everydayai-messages::-webkit-scrollbar-thumb { background: #333; }
    .eai-msg { display: flex; gap: 8px; }
    .eai-msg.user { flex-direction: row-reverse; }
    .eai-msg-label { font-size: 9px; flex-shrink: 0; padding-top: 3px; }
    .eai-msg.bot .eai-msg-label { color: #ff5500; }
    .eai-msg.user .eai-msg-label { color: #555; }
    .eai-bubble {
      max-width: 78%; padding: 9px 12px;
      font-size: 12px; line-height: 1.7; border-radius: 4px;
    }
    .eai-msg.bot .eai-bubble {
      background: #1a1a1a; border: 1px solid #222;
      border-left: 2px solid #ff5500; color: #ccc;
    }
    .eai-msg.user .eai-bubble {
      background: rgba(255,85,0,0.1);
      border: 1px solid rgba(255,85,0,0.25); color: #e8e8e8;
    }
    .eai-typing { display: flex; gap: 3px; align-items: center; padding: 9px 12px; background: #1a1a1a; border: 1px solid #222; border-left: 2px solid #ff5500; border-radius: 4px; width: fit-content; }
    .eai-dot { width: 4px; height: 4px; border-radius: 50%; background: #ff5500; animation: eaiPulse 1.2s ease-in-out infinite; }
    .eai-dot:nth-child(2) { animation-delay: 0.2s; }
    .eai-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes eaiPulse { 0%,60%,100%{opacity:0.2;transform:scale(0.8)} 30%{opacity:1;transform:scale(1)} }
    #everydayai-input-row {
      display: flex; gap: 8px; padding: 10px 14px;
      border-top: 1px solid #222; align-items: center;
      background: #0a0a0a;
    }
    #everydayai-prompt { font-size: 10px; color: #ff5500; flex-shrink: 0; }
    #everydayai-input {
      flex: 1; background: none; border: none;
      color: #e8e8e8; font-size: 12px; outline: none;
      font-family: 'JetBrains Mono', monospace, sans-serif;
    }
    #everydayai-input::placeholder { color: #555; }
    #everydayai-send {
      background: #ff5500; color: #000; border: none;
      width: 28px; height: 28px; border-radius: 4px;
      cursor: pointer; font-size: 14px; font-weight: 700;
      flex-shrink: 0; transition: all 0.15s;
    }
    #everydayai-send:hover { background: #ff6a1a; }
    #everydayai-powered {
      text-align: center; padding: 6px;
      font-size: 9px; color: #333; border-top: 1px solid #1a1a1a;
      background: #0a0a0a;
    }
    #everydayai-powered span { color: #ff5500; }
  `;

  const styleEl = document.createElement("style");
  styleEl.textContent = styles;
  document.head.appendChild(styleEl);

  const btn = document.createElement("button");
  btn.id = "everydayai-btn";
  btn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>`;
  document.body.appendChild(btn);

  const win = document.createElement("div");
  win.id = "everydayai-window";
  win.innerHTML = `
    <div id="everydayai-header">
      <div id="everydayai-header-left">
        <div id="everydayai-status"></div>
        <span id="everydayai-title">// AI Assistant</span>
      </div>
      <button id="everydayai-close">×</button>
    </div>
    <div id="everydayai-messages"></div>
    <div id="everydayai-input-row">
      <span id="everydayai-prompt">>_</span>
      <input id="everydayai-input" placeholder="type message..." />
      <button id="everydayai-send">↑</button>
    </div>
    <div id="everydayai-powered">Powered by <span>EverydayAI</span></div>
  `;
  document.body.appendChild(win);

  const messagesEl = document.getElementById("everydayai-messages");
  const inputEl = document.getElementById("everydayai-input");

  function addMessage(role, text) {
    const row = document.createElement("div");
    row.className = `eai-msg ${role}`;
    row.innerHTML = `
      <div class="eai-msg-label">${role === "bot" ? "[bot]" : "[you]"}</div>
      <div class="eai-bubble">${text}</div>
    `;
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function showTyping() {
    const row = document.createElement("div");
    row.className = "eai-msg bot";
    row.id = "eai-typing-row";
    row.innerHTML = `
      <div class="eai-msg-label">[bot]</div>
      <div class="eai-typing">
        <div class="eai-dot"></div>
        <div class="eai-dot"></div>
        <div class="eai-dot"></div>
      </div>
    `;
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeTyping() {
    const el = document.getElementById("eai-typing-row");
    if (el) el.remove();
  }

  async function sendMessage() {
    const message = inputEl.value.trim();
    if (!message) return;
    inputEl.value = "";
    addMessage("user", message);
    showTyping();

    try {
      const response = await fetch(`${API_URL}/widget/${token}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, thread_id: threadId })
      });

      const data = await response.json();
      removeTyping();

      if (data.reply) {
        threadId = data.thread_id;
        localStorage.setItem("everydayai_thread_" + token, threadId);
        addMessage("bot", data.reply);
      } else {
        addMessage("bot", "Sorry, something went wrong. Please try again.");
      }
    } catch (error) {
      removeTyping();
      addMessage("bot", "Connection error. Please try again.");
    }
  }

  btn.addEventListener("click", function () {
    isOpen = !isOpen;
    if (isOpen) {
      win.classList.add("open");
      if (messagesEl.children.length === 0) {
        addMessage("bot", "Hello! How can I help you today?");
      }
      inputEl.focus();
    } else {
      win.classList.remove("open");
    }
  });

  document.getElementById("everydayai-close").addEventListener("click", function () {
    isOpen = false;
    win.classList.remove("open");
  });

  document.getElementById("everydayai-send").addEventListener("click", sendMessage);

  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter") sendMessage();
  });
})();