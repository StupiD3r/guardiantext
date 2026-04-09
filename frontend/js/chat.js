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
        <span class="msg-friend-status" id="friend-${msg.sender_id || msg.sender_username}"></span>
        <span class="msg-time">${timeStr(msg.timestamp)}</span>
        ${filtered ? '<span class="filtered-tag">?? filtered</span>' : ''}
      </div>
      <div class="msg-content">${escapeHtml(msg.content)}</div>
    </div>`;
  area.appendChild(div);
  
  // Check friendship status for this sender
  if (!isOwn && msg.sender_id) {
    checkFriendStatus(msg.sender_id, msg.sender_username);
  }
  
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
      const roomName = typeof room === 'string' ? room : room.name;
      const isPrivate = room && room.is_private ? true : false;
      
      const div = document.createElement('div');
      div.className = `room-item${roomName === currentRoom ? ' active' : ''}`;
      div.dataset.room = roomName;
      
      if (isPrivate) {
        div.style.display = 'flex';
        div.style.justifyContent = 'space-between';
        div.style.alignItems = 'center';
        div.innerHTML = `
          <span><span class="room-icon">🔒</span> ${escapeHtml(roomName)}</span>
          <div style="display: flex; gap: 0.3rem;">
            <button class="btn btn-ghost btn-xs" onclick="showMembersModal(${room.id})" title="Members">👥</button>
            <button class="btn btn-ghost btn-xs" onclick="showInviteFriendsModal(${room.id})" title="Invite">➕</button>
          </div>
        `;
        div.querySelector('span:first-child').addEventListener('click', () => switchRoom(roomName));
      } else {
        div.innerHTML = `<span class="room-icon">#</span> ${escapeHtml(roomName)}`;
        div.addEventListener('click', () => switchRoom(roomName));
      }
      
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
  await loadRoomInvitations();

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
      ? `${list.join(', ')} ${list.length === 1 ? 'is' : 'are'} typing...`
      : '';
  });

  // ── Friend request notifications ──
  socket.on('friend_request_received', (data) => {
    console.log('[DEBUG] Friend request received:', data);
    showToast('🤝 Friend Request', data.message, 'success');
    loadFriendRequests(); // Refresh the requests list
  });

  // ── Room invitation notifications ──
  socket.on('room_invitation_received', (data) => {
    console.log('[DEBUG] Room invitation received:', data);
    showToast('📬 Room Invitation', data.message, 'success');
    loadRoomInvitations(); // Refresh the invitations list
  });

  // ── Room role management notifications ──
  socket.on('member_promoted', (data) => {
    showToast('⬆️ Member Promoted', `${data.promoted_by} promoted a member to admin`, 'success');
    loadMembers(roomIdForMembers);
  });

  socket.on('member_demoted', (data) => {
    showToast('⬇️ Member Demoted', `${data.demoted_by} demoted a member to member`, 'info');
    loadMembers(roomIdForMembers);
  });

  socket.on('member_kicked', (data) => {
    showToast('👢 Member Kicked', `${data.kicked_by} kicked a member`, 'warning');
    loadMembers(roomIdForMembers);
  });

  socket.on('kicked_from_room', (data) => {
    showToast('👢 Kicked from Room', `You were kicked by ${data.kicked_by}`, 'danger');
    currentRoom = 'General';
    loadRooms();
    loadHistory(currentRoom);
  });

  socket.on('room_renamed', (data) => {
    showToast('✏️ Room Renamed', `Room renamed to "${data.new_name}" by ${data.renamed_by}`, 'info');
    loadRooms();
    if (currentRoom === data.room_id || currentRoom === data.new_name) {
      currentRoom = data.new_name;
    }
  });

  socket.on('room_deleted', (data) => {
    showToast('🗑️ Room Deleted', `Room was deleted by ${data.deleted_by}`, 'warning');
    currentRoom = 'General';
    loadRooms();
    loadHistory(currentRoom);
    closeMembersModal();
  });
}

// ── Room Member Management ─────────────────────────────────────────────────────
let roomIdForMembers = null;
let currentUserRole = null;

async function loadMembers(roomId) {
  roomIdForMembers = roomId;
  try {
    const res = await fetch(`/api/rooms/${roomId}/members`);
    if (!res.ok) {
      showToast('Error', 'Failed to load members', 'danger');
      return;
    }
    const data = await res.json();
    const membersList = document.getElementById('members-list');
    membersList.innerHTML = '';

    const members = data.members || [];
    members.forEach(member => {
      const isCurrentUser = member.id === currentUser.id;
      const isAdmin = member.role === 'admin';
      const isMember = member.role === 'member';

      const memberDiv = document.createElement('div');
      memberDiv.style.cssText = `
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem;
        border-bottom: 1px solid var(--border);
      `;

      const nameDiv = document.createElement('div');
      nameDiv.innerHTML = `
        <strong>${escapeHtml(member.username)}</strong>
        <span style="margin-left: 0.5rem; font-size: 0.8rem; background: ${isAdmin ? 'var(--primary)' : 'var(--text-dim)'}; 
          padding: 0.2rem 0.5rem; border-radius: 4px; color: white;">
          ${isAdmin ? '👑 Admin' : '👤 Member'}
        </span>
        ${isCurrentUser ? '<span style="margin-left: 0.5rem; color: var(--primary);">(You)</span>' : ''}
      `;

      const actionDiv = document.createElement('div');
      actionDiv.style.cssText = 'display: flex; gap: 0.5rem;';

      // Show admin controls if current user is admin
      if (currentUserRole === 'admin' && !isCurrentUser) {
        if (isAdmin) {
          const demoteBtn = document.createElement('button');
          demoteBtn.className = 'btn btn-sm btn-warning';
          demoteBtn.textContent = '⬇️ Demote';
          demoteBtn.onclick = () => demoteMember(roomId, member.id);
          actionDiv.appendChild(demoteBtn);
        } else {
          const promoteBtn = document.createElement('button');
          promoteBtn.className = 'btn btn-sm btn-success';
          promoteBtn.textContent = '⬆️ Promote';
          promoteBtn.onclick = () => promoteMember(roomId, member.id);
          actionDiv.appendChild(promoteBtn);
        }

        const kickBtn = document.createElement('button');
        kickBtn.className = 'btn btn-sm btn-danger';
        kickBtn.textContent = '👢 Kick';
        kickBtn.onclick = () => kickMember(roomId, member.id, member.username);
        actionDiv.appendChild(kickBtn);
      }

      memberDiv.appendChild(nameDiv);
      if (actionDiv.children.length > 0) {
        memberDiv.appendChild(actionDiv);
      }
      membersList.appendChild(memberDiv);
    });
  } catch (e) {
    console.error('Error loading members:', e);
    showToast('Error', 'Failed to load members', 'danger');
  }
}

async function showMembersModal(roomId) {
  // Check if user is admin of this room
  try {
    const res = await fetch(`/api/rooms/${roomId}/members`);
    const data = await res.json();
    const members = data.members || [];
    const userMember = members.find(m => m.id === currentUser.id);
    currentUserRole = userMember?.role || 'member';
  } catch (e) {
    currentUserRole = 'member';
  }

  await loadMembers(roomId);
  document.getElementById('members-modal').style.display = 'flex';

  // Show admin controls if user is admin
  const adminControls = document.getElementById('room-admin-controls');
  if (currentUserRole === 'admin') {
    adminControls.style.display = 'flex';
    adminControls.style.gap = '0.5rem';
  } else {
    adminControls.style.display = 'none';
  }
}

function closeMembersModal() {
  document.getElementById('members-modal').style.display = 'none';
}

async function promoteMember(roomId, userId) {
  try {
    const res = await fetch(`/api/rooms/${roomId}/promote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Success', data.message, 'success');
      loadMembers(roomId);
    } else {
      showToast('Error', data.message, 'danger');
    }
  } catch (e) {
    showToast('Error', 'Failed to promote member', 'danger');
  }
}

async function demoteMember(roomId, userId) {
  try {
    const res = await fetch(`/api/rooms/${roomId}/demote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Success', data.message, 'success');
      loadMembers(roomId);
    } else {
      showToast('Error', data.message, 'danger');
    }
  } catch (e) {
    showToast('Error', 'Failed to demote member', 'danger');
  }
}

async function kickMember(roomId, userId, username) {
  if (!confirm(`Kick ${username} from the room?`)) return;

  try {
    const res = await fetch(`/api/rooms/${roomId}/kick`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Success', `${username} kicked from room`, 'success');
      loadMembers(roomId);
    } else {
      showToast('Error', data.message, 'danger');
    }
  } catch (e) {
    showToast('Error', 'Failed to kick member', 'danger');
  }
}

function showRenameRoomModal() {
  document.getElementById('rename-room-input').value = '';
  document.getElementById('rename-room-modal').style.display = 'flex';
}

function closeRenameRoomModal() {
  document.getElementById('rename-room-modal').style.display = 'none';
}

async function renameRoom() {
  const newName = document.getElementById('rename-room-input').value.trim();
  if (!newName || newName.length < 2 || newName.length > 50) {
    showToast('Error', 'Room name must be 2-50 characters', 'danger');
    return;
  }

  try {
    const res = await fetch(`/api/rooms/${roomIdForMembers}/rename`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Success', 'Room renamed', 'success');
      closeRenameRoomModal();
      closeMembersModal();
      loadRooms();
    } else {
      showToast('Error', data.message, 'danger');
    }
  } catch (e) {
    showToast('Error', 'Failed to rename room', 'danger');
  }
}

function confirmDeleteRoom() {
  if (!confirm('⚠️ Are you sure? This will permanently delete the room and all its messages!')) return;
  deleteRoom();
}

async function deleteRoom() {
  try {
    const res = await fetch(`/api/rooms/${roomIdForMembers}/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Success', 'Room deleted', 'success');
      closeMembersModal();
      currentRoom = 'General';
      loadRooms();
      loadHistory(currentRoom);
    } else {
      showToast('Error', data.message, 'danger');
    }
  } catch (e) {
    showToast('Error', 'Failed to delete room', 'danger');
  }
}

// ── DOM events ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  init();
  setupFriendTabs();
  loadFriends();

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

  // Friend search
  const searchInput = document.getElementById('friend-search-input');
  const searchBtn = document.getElementById('friend-search-btn');
  
  searchBtn.addEventListener('click', searchUsers);
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      searchUsers();
    }
  });

  // Hide search results when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.friend-search') && !e.target.closest('.search-results')) {
      hideSearchResults();
    }
  });
});

// ---- Friends Management ----
async function loadFriends() {
  try {
    const response = await fetch('/api/friends');
    const data = await response.json();
    renderFriends(data.friends);
  } catch (error) {
    console.error('Error loading friends:', error);
  }
}

async function loadFriendRequests() {
  try {
    console.log('[DEBUG] Loading friend requests...');
    const response = await fetch('/api/friends/requests');
    const data = await response.json();
    console.log('[DEBUG] Friend requests API response:', data);
    renderFriendRequests(data);
  } catch (error) {
    console.error('[DEBUG] Error loading friend requests:', error);
  }
}

function renderFriends(friends) {
  const container = document.getElementById('friends-list');
  if (!friends || friends.length === 0) {
    container.innerHTML = '<div class="text-muted text-xs">No friends yet</div>';
    return;
  }

  container.innerHTML = friends.map(friend => `
    <div class="friend-item">
      <div class="friend-info">
        <div class="friend-avatar">${avatarLetter(friend.username)}</div>
        <div>
          <div class="friend-name">${escapeHtml(friend.username)}</div>
          <div class="friend-status">Friend</div>
        </div>
      </div>
      <div class="friend-actions">
        <button class="btn btn-ghost btn-xs" onclick="removeFriend(${friend.id})">Remove</button>
      </div>
    </div>
  `).join('');
}

function renderFriendRequests(requests) {
  console.log('[DEBUG] renderFriendRequests called with:', requests);
  
  const container = document.getElementById('friend-requests');
  console.log('[DEBUG] friend-requests container:', container);
  
  if (!container) {
    console.error('[DEBUG] friend-requests container not found!');
    return;
  }
  
  const hasRequests = (requests.incoming && requests.incoming.length > 0) || 
                     (requests.outgoing && requests.outgoing.length > 0);
  
  console.log('[DEBUG] hasRequests:', hasRequests);
  console.log('[DEBUG] incoming:', requests.incoming);
  console.log('[DEBUG] outgoing:', requests.outgoing);
  
  if (!hasRequests) {
    container.innerHTML = '<div class="text-muted text-xs">No requests</div>';
    console.log('[DEBUG] Set "No requests" message');
    return;
  }

  let html = '';
  
  if (requests.incoming && requests.incoming.length > 0) {
    html += '<div class="text-xs text-muted mb-2">Incoming Requests</div>';
    requests.incoming.forEach(req => {
      html += `
        <div class="request-item">
          <div class="request-header">
            <div class="request-info">
              <div class="friend-avatar">${avatarLetter(req.username)}</div>
              <div>
                <div class="friend-name">${escapeHtml(req.username)}</div>
                <div class="request-time">${timeStr(req.created_at)}</div>
              </div>
            </div>
            <div class="request-actions">
              <button class="btn btn-success btn-xs" onclick="acceptFriendRequest(${req.id})">Accept</button>
              <button class="btn btn-danger btn-xs" onclick="declineFriendRequest(${req.id})">Decline</button>
            </div>
          </div>
        </div>
      `;
    });
  }
  
  if (requests.outgoing && requests.outgoing.length > 0) {
    html += '<div class="text-xs text-muted mb-2 mt-3">Outgoing Requests</div>';
    requests.outgoing.forEach(req => {
      html += `
        <div class="request-item">
          <div class="request-header">
            <div class="request-info">
              <div class="friend-avatar">${avatarLetter(req.username)}</div>
              <div>
                <div class="friend-name">${escapeHtml(req.username)}</div>
                <div class="request-time">${timeStr(req.created_at)}</div>
              </div>
            </div>
            <div class="request-actions">
              <button class="btn btn-ghost btn-xs" onclick="cancelFriendRequest(${req.id})">Cancel</button>
            </div>
          </div>
        </div>
      `;
    });
  }
  
  console.log('[DEBUG] Setting HTML:', html);
  container.innerHTML = html;
}

async function sendFriendRequest(username) {
  try {
    const response = await fetch('/api/friends/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast('Success', data.message, 'success');
      hideSearchResults();
      document.getElementById('friend-search-input').value = '';
      loadFriendRequests();
    } else {
      showToast('Error', data.message, 'error');
    }
  } catch (error) {
    console.error('Error sending friend request:', error);
    showToast('Error', 'Failed to send friend request', 'error');
  }
}

async function acceptFriendRequest(requesterId) {
  try {
    const response = await fetch('/api/friends/accept', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ requester_id: requesterId })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast('Success', data.message, 'success');
      loadFriends();
      loadFriendRequests();
    } else {
      showToast('Error', data.message, 'error');
    }
  } catch (error) {
    console.error('Error accepting friend request:', error);
    showToast('Error', 'Failed to accept friend request', 'error');
  }
}

async function declineFriendRequest(requesterId) {
  try {
    const response = await fetch('/api/friends/decline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ requester_id: requesterId })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast('Success', data.message, 'success');
      loadFriendRequests();
    } else {
      showToast('Error', data.message, 'error');
    }
  } catch (error) {
    console.error('Error declining friend request:', error);
    showToast('Error', 'Failed to decline friend request', 'error');
  }
}

async function cancelFriendRequest(friendId) {
  try {
    const response = await fetch('/api/friends/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ friend_id: friendId })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast('Success', data.message, 'success');
      loadFriendRequests();
    } else {
      showToast('Error', data.message, 'error');
    }
  } catch (error) {
    console.error('Error canceling friend request:', error);
    showToast('Error', 'Failed to cancel friend request', 'error');
  }
}

async function removeFriend(friendId) {
  try {
    const response = await fetch('/api/friends/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ friend_id: friendId })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast('Success', data.message, 'success');
      loadFriends();
    } else {
      showToast('Error', data.message, 'error');
    }
  } catch (error) {
    console.error('Error removing friend:', error);
    showToast('Error', 'Failed to remove friend', 'error');
  }
}

// ---- Friend Status Check ----
async function checkFriendStatus(userId, username) {
  try {
    const response = await fetch(`/api/friends/status/${userId}`);
    const data = await response.json();
    
    const statusElement = document.getElementById(`friend-${userId}`);
    if (statusElement) {
      if (data.status === 'accepted') {
        statusElement.innerHTML = ' <span class="friend-indicator">??</span>';
        statusElement.title = 'Friend';
      } else if (data.status === 'pending') {
        statusElement.innerHTML = ' <span class="pending-indicator">??</span>';
        statusElement.title = 'Friend request pending';
      }
    }
  } catch (error) {
    console.error('Error checking friend status:', error);
  }
}

// ---- Debug Friend Request Loading ----
async function debugFriendRequests() {
  try {
    const response = await fetch('/api/friends/requests');
    const data = await response.json();
    console.log('[DEBUG] Friend requests response:', data);
  } catch (error) {
    console.error('[DEBUG] Error loading friend requests:', error);
  }
}

// Make debug function available globally
window.debugFriendRequests = debugFriendRequests;

async function searchUsers() {
  const query = document.getElementById('friend-search-input').value.trim();
  if (!query) {
    hideSearchResults();
    return;
  }

  try {
    const response = await fetch(`/api/friends/search?q=${encodeURIComponent(query)}`);
    const data = await response.json();
    showSearchResults(data.users);
  } catch (error) {
    console.error('Error searching users:', error);
  }
}

function showSearchResults(users) {
  const existingResults = document.querySelector('.search-results');
  if (existingResults) existingResults.remove();

  if (!users || users.length === 0) {
    const resultsDiv = document.createElement('div');
    resultsDiv.className = 'search-results';
    resultsDiv.innerHTML = '<div class="text-muted text-xs">No users found</div>';
    document.querySelector('.friend-search').after(resultsDiv);
    return;
  }

  const resultsDiv = document.createElement('div');
  resultsDiv.className = 'search-results';
  resultsDiv.innerHTML = users.map(user => `
    <div class="search-result-item" onclick="sendFriendRequest('${user.username}')">
      <div class="friend-info">
        <div class="friend-avatar">${avatarLetter(user.username)}</div>
        <div class="friend-name">${escapeHtml(user.username)}</div>
      </div>
      <button class="btn btn-primary btn-xs">Add Friend</button>
    </div>
  `).join('');
  
  document.querySelector('.friend-search').after(resultsDiv);
}

function hideSearchResults() {
  const results = document.querySelector('.search-results');
  if (results) results.remove();
}

// ---- Friend Tab Switching ----
function setupFriendTabs() {
  const tabs = document.querySelectorAll('.friend-tab');
  const panels = document.querySelectorAll('.friends-panel');
  
  console.log('[DEBUG] Setting up friend tabs, found tabs:', tabs.length, 'panels:', panels.length);
  
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTab = tab.dataset.tab;
      console.log('[DEBUG] Tab clicked:', targetTab);
      
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      
      tab.classList.add('active');
      
      // Use correct element IDs
      const targetPanel = document.getElementById(
        targetTab === 'friends' ? 'friends-list' : 'friend-requests'
      );
      console.log('[DEBUG] Target panel:', targetPanel);
      
      if (targetPanel) {
        targetPanel.classList.add('active');
        
        if (targetTab === 'friends') {
          console.log('[DEBUG] Loading friends...');
          loadFriends();
        } else if (targetTab === 'requests') {
          console.log('[DEBUG] Loading friend requests...');
          loadFriendRequests();
        }
      } else {
        console.error('[DEBUG] Target panel not found for tab:', targetTab);
      }
    });
  });
}

// ---- Private Rooms Management ----

let currentPrivateRoomId = null;

async function loadRoomInvitations() {
  try {
    const res = await fetch('/api/rooms/invitations');
    const data = await res.json();
    const list = document.getElementById('room-invitations-list');
    
    if (!list) return;
    
    if (!data.invitations || data.invitations.length === 0) {
      list.innerHTML = '<div class="text-muted text-xs">No invitations</div>';
      return;
    }
    
    list.innerHTML = data.invitations.map(inv => `
      <div style="background: var(--bg3); padding: 0.5rem; border-radius: 6px; margin-bottom: 0.3rem;">
        <div class="text-xs text-muted">${escapeHtml(inv.inviter_username)} invited you</div>
        <div style="margin-top: 0.3rem; display: flex; gap: 0.3rem;">
          <button class="btn btn-primary btn-xs" onclick="acceptRoomInvitation(${inv.id})">Accept</button>
          <button class="btn btn-ghost btn-xs" onclick="declineRoomInvitation(${inv.id})">Decline</button>
        </div>
      </div>
    `).join('');
  } catch (e) {
    console.error('Failed to load room invitations:', e);
  }
}

async function acceptRoomInvitation(invitationId) {
  try {
    const res = await fetch(`/api/rooms/invitations/${invitationId}/accept`, {
      method: 'POST'
    });
    const data = await res.json();
    
    if (data.success) {
      showToast('Success', 'Invitation accepted', 'success');
      loadRoomInvitations();
      loadRooms();
    } else {
      showToast('Error', data.message, 'error');
    }
  } catch (e) {
    console.error('Error accepting invitation:', e);
    showToast('Error', 'Failed to accept invitation', 'error');
  }
}

async function declineRoomInvitation(invitationId) {
  try {
    const res = await fetch(`/api/rooms/invitations/${invitationId}/decline`, {
      method: 'POST'
    });
    const data = await res.json();
    
    if (data.success) {
      showToast('Success', 'Invitation declined', 'success');
      loadRoomInvitations();
    } else {
      showToast('Error', data.message, 'error');
    }
  } catch (e) {
    console.error('Error declining invitation:', e);
    showToast('Error', 'Failed to decline invitation', 'error');
  }
}

function showCreateRoomModal() {
  document.getElementById('create-room-modal').style.display = 'flex';
  document.getElementById('new-room-name').focus();
}

function closeCreateRoomModal() {
  document.getElementById('create-room-modal').style.display = 'none';
  document.getElementById('new-room-name').value = '';
}

async function createPrivateRoom() {
  const name = document.getElementById('new-room-name').value.trim();
  
  if (!name) {
    showToast('Error', 'Please enter a room name', 'error');
    return;
  }
  
  try {
    const res = await fetch('/api/rooms/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const data = await res.json();
    
    if (data.success) {
      showToast('Success', 'Private room created', 'success');
      closeCreateRoomModal();
      loadRooms();
    } else {
      showToast('Error', data.message, 'error');
    }
  } catch (e) {
    console.error('Error creating room:', e);
    showToast('Error', 'Failed to create room', 'error');
  }
}

function showInviteFriendsModal(roomId) {
  currentPrivateRoomId = roomId;
  document.getElementById('invite-friends-modal').style.display = 'flex';
  loadFriendsForInvite();
}

function closeInviteFriendsModal() {
  document.getElementById('invite-friends-modal').style.display = 'none';
  currentPrivateRoomId = null;
}

async function loadFriendsForInvite() {
  try {
    const res = await fetch('/api/friends');
    const data = await res.json();
    const list = document.getElementById('invite-friends-list');
    
    if (!data.friends || data.friends.length === 0) {
      list.innerHTML = '<div class="text-muted text-xs">No friends to invite</div>';
      return;
    }
    
    list.innerHTML = data.friends.map(friend => `
      <div class="friend-select-item">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--primary); display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.85rem;">
            ${avatarLetter(friend.username)}
          </div>
          <span>${escapeHtml(friend.username)}</span>
        </div>
        <button class="btn btn-primary btn-sm" onclick="inviteFriendToRoom(${friend.id})">Invite</button>
      </div>
    `).join('');
  } catch (e) {
    console.error('Failed to load friends:', e);
  }
}

async function inviteFriendToRoom(friendId) {
  try {
    const res = await fetch(`/api/rooms/${currentPrivateRoomId}/invite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ friend_id: friendId })
    });
    const data = await res.json();
    
    if (data.success) {
      showToast('Success', 'Invitation sent', 'success');
      loadFriendsForInvite();
    } else {
      showToast('Error', data.message, 'error');
    }
  } catch (e) {
    console.error('Error inviting friend:', e);
    showToast('Error', 'Failed to send invitation', 'error');
  }
}
