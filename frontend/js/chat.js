/* chat.js  –  GuardianText Real-Time Chat Client */

let socket       = null;
let currentRoom  = 'General';
let currentUser  = null;
let typingTimer  = null;
let isTyping     = false;
let pendingSuggestion = null;

// ── Toast ──────────────────────────────────────────────────────────────────────
function showToast(title, body = '', type = '') {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type ? 'toast-' + type : ''}`;
  t.innerHTML = `<div class="toast-title">${title}</div>${body ? `<div class="toast-body">${body}</div>` : ''}`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 5000);
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
            .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function timeStr(ts) {
  const d = ts ? new Date(ts + ' UTC') : new Date();
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function avatarLetter(name) {
  return (name || '?')[0].toUpperCase();
}

// ── Render a message bubble ────────────────────────────────────────────────────
function renderMessage(msg) {
  const area    = document.getElementById('messages-area');
  const isOwn   = msg.sender_username === currentUser?.username;
  const filtered = msg.is_filtered || msg.is_filtered === 1;

  const div = document.createElement('div');
  div.className = `msg${isOwn ? ' own' : ''}${filtered ? ' filtered' : ''}`;
  div.innerHTML = `
    <div class="msg-avatar">${avatarLetter(msg.sender_username)}</div>
    <div class="msg-body">
      <div class="msg-meta">
        <span class="msg-sender">${escapeHtml(msg.sender_username)}</span>
        <span class="msg-time">${timeStr(msg.timestamp)}</span>
        ${filtered ? '<span class="filtered-tag">🛡️ filtered</span>' : ''}
      </div>
      <div class="msg-content">${escapeHtml(msg.content)}</div>
    </div>`;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

// ── System message (join/leave) ────────────────────────────────────────────────
function renderSystemMsg(text) {
  const area = document.getElementById('messages-area');
  const div  = document.createElement('div');
  div.style.cssText = 'text-align:center;font-size:.78rem;color:var(--text-dim);margin:.3rem 0;';
  div.textContent   = text;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

// ── Load historical messages ───────────────────────────────────────────────────
async function loadHistory(room) {
  const area = document.getElementById('messages-area');
  area.innerHTML = `<div style="text-align:center;color:var(--text-dim);font-size:.85rem;margin-top:2rem;">
    🛡️ Messages in this channel are monitored for toxic language.<br>Be respectful and kind!
  </div>`;

  try {
    const res  = await fetch(`/api/messages/${encodeURIComponent(room)}`);
    const data = await res.json();
    (data.messages || []).forEach(renderMessage);
  } catch (e) {
    console.error('Could not load history:', e);
  }
}

// ── Load rooms list ────────────────────────────────────────────────────────────
async function loadRooms() {
  try {
    const res  = await fetch('/api/rooms');
    const data = await res.json();
    const list = document.getElementById('room-list');
    list.innerHTML = '';
    (data.rooms || []).forEach(room => {
      const div = document.createElement('div');
      div.className = `room-item${room === currentRoom ? ' active' : ''}`;
      div.dataset.room = room;
      div.innerHTML = `<span class="room-icon">#</span> ${escapeHtml(room)}`;
      div.addEventListener('click', () => switchRoom(room));
      list.appendChild(div);
    });
  } catch (e) {
    console.error('Could not load rooms:', e);
  }
}

// ── Switch room ────────────────────────────────────────────────────────────────
function switchRoom(newRoom) {
  if (newRoom === currentRoom) return;

  socket.emit('leave_room', { room: currentRoom });

  currentRoom = newRoom;
  document.getElementById('topbar-room').textContent    = `# ${newRoom}`;
  document.getElementById('header-room').textContent    = `# ${newRoom}`;

  // Update sidebar active state
  document.querySelectorAll('.room-item').forEach(el => {
    el.classList.toggle('active', el.dataset.room === newRoom);
  });

  loadHistory(newRoom);
  socket.emit('join_room', { room: newRoom });
}

// ── Online users ───────────────────────────────────────────────────────────────
function updateOnlineUsers(users) {
  const list = document.getElementById('online-users-list');
  list.innerHTML = '';
  (users || []).forEach(u => {
    const div = document.createElement('div');
    div.className = 'user-pill';
    div.innerHTML = `<span class="user-dot"></span><span>${escapeHtml(u)}</span>`;
    list.appendChild(div);
  });
  document.getElementById('topbar-online').textContent = `● ${users.length} online`;
}

// ── Filter warning banner ──────────────────────────────────────────────────────
function showFilterWarning(toxic_words, suggestion, action) {
  const banner = document.getElementById("filter-warning");
  const reason = document.getElementById("filter-reason");

  const wordList = toxic_words && toxic_words.length
    ? "<br><b>Flagged words:</b> " + toxic_words.map(w => "<span style='color:#f87171'>" + w + "</span>").join(", ")
    : "";

  const suggestionText = suggestion
    ? "<br><b>💡 Suggestion:</b> <span style='color:#34d399'>" + suggestion + "</span>"
    : "";

  const actionLabel = action === "blocked"
    ? "<span style='color:#f87171'>🚫 Message was <b>blocked</b> and not sent.</span>"
    : "<span style='color:#fbbf24'>⚠️ Message was <b>filtered</b> — toxic words replaced with asterisks.</span>";

  reason.innerHTML = actionLabel + wordList + suggestionText;
  banner.classList.add("show");
  clearTimeout(banner._timer);
  banner._timer = setTimeout(clearFilterWarning, 12000);
}

function clearFilterWarning() {
  document.getElementById("filter-warning").classList.remove("show");
}

// ── Suggestion panel (sender chooses what to send) ─────────────────────────────
function hideSuggestionsPanel() {
  const panel = document.getElementById("suggestions-panel");
  if (!panel) return;
  panel.style.display = "none";
  pendingSuggestion = null;
}

function showSuggestionsPanel(payload) {
  const panel = document.getElementById("suggestions-panel");
  const origEl = document.getElementById("suggestions-original");
  const optionsEl = document.getElementById("suggestions-options");
  const cancelBtn = document.getElementById("suggestions-cancel-btn");
  if (!panel || !origEl || !optionsEl || !cancelBtn) return;

  // Use backend suggestions if available, otherwise generate locally
  let suggestions = [];
  if (payload.options && payload.options.length > 0) {
    // Use trained ML suggestions from backend
    suggestions = payload.options.map(opt => ({
      id: opt.id,
      text: opt.text,
      hint: opt.hint || "ML-powered suggestion"
    }));
  } else {
    // Fallback to local generation if backend options not available
    const baseSuggestion = payload.suggestion_text || "";
    suggestions = generateMultipleSuggestions(payload.original_message, baseSuggestion, payload.toxic_words || []);
  }
  
  if (suggestions.length === 0) {
    return;
  }

  pendingSuggestion = {
    room: payload.room,
    original_message: payload.original_message,
    toxicity_score: payload.toxicity_score,
    toxic_words: payload.toxic_words || [],
    suggestion_text: payload.suggestion_text || "",
    decision: payload.decision || "warned",
    suggestions: suggestions,
  };

  // Display original message
  origEl.textContent = "Original: " + (payload.original_message || "");

  // Clear and populate options
  optionsEl.innerHTML = "";
  suggestions.forEach((suggestion, index) => {
    const optionDiv = document.createElement("div");
    optionDiv.className = "suggestion-option";
    optionDiv.innerHTML = `
      <div class="suggestion-text">${suggestion.text}</div>
      <div class="suggestion-hint">${suggestion.hint}</div>
    `;
    optionDiv.onclick = () => {
      if (!socket || !pendingSuggestion) return;
      const p = pendingSuggestion;
      socket.emit("confirm_message", {
        room: p.room || currentRoom,
        message: suggestion.text,
        original_message: p.original_message,
        toxicity_score: p.toxicity_score,
        toxic_words: p.toxic_words,
        suggestion_text: p.suggestion_text,
        suggestion_type: suggestion.id || 'unknown',
        suggested_text: suggestion.text,
        decision: p.decision,
      });
      hideSuggestionsPanel();
    };
    optionsEl.appendChild(optionDiv);
  });

  cancelBtn.onclick = () => {
    hideSuggestionsPanel();
  };

  panel.style.display = "block";
}

function generateMultipleSuggestions(original, baseSuggestion, toxicWords) {
  // This function is now a fallback - backend should provide the 4 structured options
  // But keeping it for compatibility in case backend doesn't send options
  const suggestions = [];
  
  // 1. Filtered version (same sentence without toxic words)
  const filteredVersion = createFilteredVersion(original, toxicWords);
  if (filteredVersion && filteredVersion !== original) {
    suggestions.push({
      text: filteredVersion,
      hint: "Same sentence without toxic words"
    });
  }
  
  // 2. Natural rephrased version
  if (baseSuggestion && baseSuggestion !== original) {
    suggestions.push({
      text: baseSuggestion,
      hint: "Paraphrased version"
    });
  }
  
  // 3. Alternative paraphrase
  const alternativeParaphrase = createAlternativeParaphrase(original, toxicWords);
  if (alternativeParaphrase) {
    suggestions.push({
      text: alternativeParaphrase,
      hint: "Alternative paraphrase"
    });
  }
  
  // 4. Flexible contextual option
  const contextualOption = createContextualOption(original, toxicWords);
  if (contextualOption) {
    suggestions.push({
      text: contextualOption,
      hint: "Alternative option"
    });
  }
  
  // Ensure we have exactly 4 options, fill with defaults if needed
  const defaultOptions = [
    {
      text: "I'd like to keep our conversation constructive.",
      hint: "Alternative option"
    },
    {
      text: "Let's focus on finding common ground.",
      hint: "Alternative option"
    },
    {
      text: "I appreciate you sharing your perspective.",
      hint: "Alternative option"
    },
    {
      text: "Let's try to approach this more calmly.",
      hint: "Alternative option"
    }
  ];
  
  while (suggestions.length < 4 && defaultOptions.length > 0) {
    const defOpt = defaultOptions.shift();
    if (!suggestions.some(s => s.text === defOpt.text)) {
      suggestions.push(defOpt);
    }
  }
  
  return suggestions.slice(0, 4);
}

function createAlternativeParaphrase(original, toxicWords) {
  const originalLower = original.toLowerCase();
  
  // School context
  if (originalLower.includes('school') || originalLower.includes('teacher') || 
      originalLower.includes('homework') || originalLower.includes('exam')) {
    if (originalLower.includes('fucking') || originalLower.includes('hate')) {
      return "I'm finding this school work really challenging.";
    }
    if (originalLower.includes('stupid') || originalLower.includes('dumb')) {
      return "I don't quite understand what we're learning.";
    }
  }
  
  // Personal disagreement
  if (originalLower.includes('stupid') || originalLower.includes('idiot') || 
      originalLower.includes('dumb') || originalLower.includes('moron')) {
    return "I have a completely different perspective on this.";
  }
  
  // Frustration
  if (originalLower.includes('fuck') || originalLower.includes('shit') || 
      originalLower.includes('crap') || originalLower.includes('damn')) {
    return "This situation is making me feel frustrated.";
  }
  
  return null;
}

function createContextualOption(original, toxicWords) {
  const originalLower = original.toLowerCase();
  
  // Work/professional context
  if (originalLower.includes('work') || originalLower.includes('job') || 
      originalLower.includes('boss') || originalLower.includes('project')) {
    return "I'd like to discuss how we can improve this situation.";
  }
  
  // Personal relationships
  if (originalLower.includes('you') || originalLower.includes('your') || 
      originalLower.includes('friend')) {
    return "I value our relationship and want to communicate better.";
  }
  
  // General conflict
  if (toxicWords.some(word => ['stupid', 'idiot', 'dumb'].includes(word))) {
    return "I think we're having trouble understanding each other.";
  }
  
  return null;
}

function createFilteredVersion(original, toxicWords) {
  // Create a filtered version by removing toxic words but keeping structure
  if (!toxicWords || toxicWords.length === 0) {
    return original;
  }
  
  let filtered = original;
  
  // Remove toxic words (case-insensitive, whole word matching)
  for (const word of toxicWords.sort((a, b) => b.length - a.length)) {
    const regex = new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
    filtered = filtered.replace(regex, '');
  }
  
  // Clean up extra spaces and punctuation
  filtered = filtered.replace(/\s+/g, ' ')  // Collapse multiple spaces
                 .replace(/\s*([,.!?])\s*/g, '$1')  // Fix spacing around punctuation
                 .replace(/\s+/g, ' ')  // Final cleanup
                 .trim();
  
  // Capitalize first letter
  if (filtered) {
    filtered = filtered.charAt(0).toUpperCase() + filtered.slice(1);
  }
  
  return filtered;
}

// ── Send a message ─────────────────────────────────────────────────────────────
function sendMessage() {
  const input   = document.getElementById('msg-input');
  const message = input.value.trim();
  if (!message || !socket) return;

  socket.emit('send_message', { room: currentRoom, message });
  input.value = '';
  input.style.height = 'auto';
  stopTyping();
}

// ── Typing events ──────────────────────────────────────────────────────────────
function startTyping() {
  if (!isTyping) {
    isTyping = true;
    socket.emit('typing', { room: currentRoom, typing: true });
  }
  clearTimeout(typingTimer);
  typingTimer = setTimeout(stopTyping, 1800);
}

function stopTyping() {
  if (isTyping) {
    isTyping = false;
    socket.emit('typing', { room: currentRoom, typing: false });
  }
  clearTimeout(typingTimer);
}

// ── Logout ─────────────────────────────────────────────────────────────────────
async function logout() {
  await fetch('/api/logout', { method: 'POST' });
  window.location.href = '/';
}

// ── Init ───────────────────────────────────────────────────────────────────────
async function init() {
  // Verify session
  const meRes  = await fetch('/api/me');
  const meData = await meRes.json();
  if (!meData.logged_in) {
    window.location.href = '/';
    return;
  }
  currentUser = meData;
  document.getElementById('header-username').textContent = `👤 ${meData.username}`;

  await loadRooms();
  await loadHistory(currentRoom);

  // Connect socket
  socket = io({ transports: ['websocket', 'polling'] });

  socket.on('connect', () => {
    console.log('[WS] Connected, sid=', socket.id);
    socket.emit('join_room', { room: currentRoom });
  });

  socket.on('disconnect', () => {
    showToast('⚠️ Disconnected', 'Trying to reconnect…', 'warning');
  });

  socket.on('connect_error', (err) => {
    showToast('Connection Error', err.message, 'danger');
  });

  // ── Room events ──
  socket.on('room_joined', (data) => {
    updateOnlineUsers(data.online_users || []);
  });

  socket.on('user_joined', (data) => {
    if (data.room === currentRoom) {
      updateOnlineUsers(data.online_users || []);
      renderSystemMsg(`${data.username} joined the channel`);
    }
  });

  socket.on('user_left', (data) => {
    if (data.room === currentRoom) {
      updateOnlineUsers(data.online_users || []);
      renderSystemMsg(`${data.username} left the channel`);
    }
  });

  // ── Messages ──
  socket.on('new_message', (msg) => {
    if (msg.room === currentRoom) renderMessage(msg);
  });

  // ── Filter feedback (legacy) ──
  socket.on("message_warned", (data) => {
    showToast("⚠️ Message Modified", "Toxic words were replaced before sending.", "warning");
    showFilterWarning(data.toxic_words, data.suggestion, "warned");
  });

  socket.on("message_blocked", (data) => {
    showToast("🚫 Message Blocked", "Your message was not sent.", "danger");
    showFilterWarning(data.toxic_words, data.suggestion, "blocked");
  });

  // ── New: suggestions flow ──
  socket.on("message_suggestions", (data) => {
    // Only show if this suggestion is for the active room
    if (data.room === currentRoom) {
      showSuggestionsPanel(data);
    }
  });

  // ── Typing indicator ──
  const typingUsers = new Set();
  socket.on('user_typing', (data) => {
    const el = document.getElementById('typing-indicator');
    if (data.typing) {
      typingUsers.add(data.username);
    } else {
      typingUsers.delete(data.username);
    }
    const list = [...typingUsers];
    el.textContent = list.length
      ? `${list.join(', ')} ${list.length === 1 ? 'is' : 'are'} typing…`
      : '';
  });
}

// ── DOM events ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  init();

  const input = document.getElementById('msg-input');

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    } else {
      startTyping();
    }
  });

  // Auto-resize textarea
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });
});
