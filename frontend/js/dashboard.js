/* dashboard.js  –  GuardianText Dashboard */

function showToast(title, body = '', type = '') {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type ? 'toast-' + type : ''}`;
  t.innerHTML = `<div class="toast-title">${title}</div>${body ? `<div class="toast-body">${body}</div>` : ''}`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 4500);
}

function escapeHtml(str) {
  if (!str) return '—';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;')
                    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function actionBadge(action) {
  const map = { blocked: 'badge-blocked', warned: 'badge-warned', allowed: 'badge-allowed' };
  return `<span class="badge ${map[action] || ''}">${action || '—'}</span>`;
}

function scoreBadge(score) {
  const n = parseFloat(score) || 0;
  let cls = 'badge-clean';
  if (n >= 0.7) cls = 'badge-severe';
  else if (n >= 0.4) cls = 'badge-moderate';
  else if (n >= 0.2) cls = 'badge-mild';
  return `<span class="badge ${cls}">${(n * 100).toFixed(0)}%</span>`;
}

function formatTime(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleString();
}

// ── Load stats ─────────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const res  = await fetch('/api/dashboard/stats');
    if (!res.ok) {
      console.error('Stats API error:', res.status, res.statusText);
      if (res.status === 401) {
        window.location.href = '/';
        return;
      }
      return;
    }
    const data = await res.json();

    document.getElementById('stat-total').textContent    = data.total_messages ?? '—';
    document.getElementById('stat-filtered').textContent = data.filtered_count ?? '—';
    document.getElementById('stat-blocked').textContent  = data.blocked_count ?? '—';
    document.getElementById('stat-warned').textContent   = data.warned_count ?? '—';
    document.getElementById('stat-users').textContent    = data.total_users ?? '—';
    document.getElementById('stat-rate').textContent     = data.filter_rate != null ? `${data.filter_rate}%` : '—';

    // Top offenders
    const to = document.getElementById('top-offenders');
    to.innerHTML = '';
    if (data.top_offenders && data.top_offenders.length) {
      data.top_offenders.forEach((o, i) => {
        const pill = document.createElement('div');
        pill.className = 'badge badge-moderate';
        pill.style.padding = '.3rem .8rem';
        pill.textContent = `#${i + 1} ${o.username}  (${o.cnt})`;
        to.appendChild(pill);
      });
    } else {
      to.innerHTML = '<span class="text-muted text-sm">No flagged users yet.</span>';
    }
  } catch (e) {
    console.error('Stats error:', e);
  }
}

// ── Admin: users overview & ban controls ────────────────────────────────────────
async function loadUsersAdmin() {
  const container = document.getElementById('admin-users-body');
  if (!container) return;
  container.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-dim);padding:1rem;">Loading users…</td></tr>';

  try {
    const res = await fetch('/api/admin/users');
    if (res.status === 403) {
      // Not an admin – hide section
      document.getElementById('admin-users-card').style.display = 'none';
      return;
    }
    if (res.status === 401) {
      window.location.href = '/';
      return;
    }
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    const users = data.users || [];
    if (!users.length) {
      container.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-dim);padding:1rem;">No users yet.</td></tr>';
      return;
    }
    container.innerHTML = users.map((u, idx) => `
      <tr>
        <td class="text-xs text-muted">${idx + 1}</td>
        <td><strong>${escapeHtml(u.username)}</strong>${u.is_admin ? ' <span class="badge badge-allowed">admin</span>' : ''}</td>
        <td>${u.incidents}</td>
        <td>${(parseFloat(u.total_toxicity) || 0).toFixed(2)}</td>
        <td>${u.is_banned ? '<span class="badge badge-blocked">banned</span>' : '<span class="badge badge-clean">active</span>'}</td>
        <td>
          <button class="btn btn-sm ${u.is_banned ? 'btn-primary' : 'btn-danger'}"
                  onclick="toggleBanUser(${u.id}, ${u.is_banned ? 'false' : 'true'})">
            ${u.is_banned ? 'Unban' : 'Ban'}
          </button>
        </td>
        <td>
          <button class="btn btn-sm btn-danger" onclick="deleteUser(${u.id}, '${escapeHtml(u.username)}')">Delete</button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    container.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--danger);padding:1rem;">Error loading users: ${e.message}</td></tr>`;
  }
}

async function toggleBanUser(userId, banned) {
  try {
    const res = await fetch(`/api/admin/users/${userId}/ban`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ banned }),
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      showToast('Error', data.error || 'Failed to update user.', 'danger');
      return;
    }
    showToast('Success', banned ? 'User has been banned.' : 'User has been unbanned.', 'success');
    loadUsersAdmin();
  } catch (e) {
    showToast('Error', e.message, 'danger');
  }
}

async function deleteUser(userId, username) {
  if (!confirm(`Are you sure you want to permanently delete user "${username}" and all their data?`)) return;
  
  try {
    const res = await fetch(`/api/admin/users/${userId}/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      showToast('Error', data.error || 'Failed to delete user.', 'danger');
      return;
    }
    showToast('Success', `User "${username}" has been deleted.`, 'success');
    loadUsersAdmin();
    loadStats();
  } catch (e) {
    showToast('Error', e.message, 'danger');
  }
}

// ── Admin: message list & clear/delete ─────────────────────────────────────────
async function loadAdminMessages() {
  const tbody = document.getElementById('admin-messages-body');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-dim);padding:1rem;">Loading…</td></tr>';

  try {
    const res = await fetch('/api/admin/messages');
    if (res.status === 403) {
      // Not an admin – hide section
      const card = document.getElementById('admin-users-card');
      if (card) card.style.display = 'none';
      return;
    }
    if (res.status === 401) {
      window.location.href = '/';
      return;
    }
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    const messages = data.messages || [];
    if (!messages.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-dim);padding:1rem;">No messages stored.</td></tr>';
      return;
    }
    tbody.innerHTML = messages.map(m => `
      <tr>
        <td class="text-xs text-muted">${m.id}</td>
        <td><strong>${escapeHtml(m.sender_username)}</strong></td>
        <td class="text-xs text-muted">${escapeHtml(m.room)}</td>
        <td class="truncate">${escapeHtml(m.content)}</td>
        <td>${scoreBadge(m.toxicity_score)}</td>
        <td class="text-xs text-muted" style="white-space:nowrap">${formatTime(m.timestamp)}</td>
        <td>
          <button class="btn btn-sm btn-danger" onclick="deleteMessage(${m.id})">Delete</button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--danger);padding:1rem;">Error loading messages: ${e.message}</td></tr>`;
  }
}

async function deleteMessage(messageId) {
  if (!confirm('Delete this message permanently?')) return;
  try {
    const res = await fetch(`/api/admin/messages/${messageId}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok || !data.success) {
      showToast('Error', data.error || 'Failed to delete message.', 'danger');
      return;
    }
    showToast('Success', 'Message deleted.', 'success');
    loadAdminMessages();
    loadStats();
  } catch (e) {
    showToast('Error', e.message, 'danger');
  }
}

async function clearAllChats() {
  if (!confirm('This will delete ALL chats and filter logs. Are you sure?')) return;
  try {
    const res = await fetch('/api/admin/messages', { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok || !data.success) {
      showToast('Error', data.error || 'Failed to clear chats.', 'danger');
      return;
    }
    showToast('Success', 'All chats and logs cleared.', 'success');
    loadAdminMessages();
    loadLogs(false);
    loadStats();
  } catch (e) {
    showToast('Error', e.message, 'danger');
  }
}

// ── Load logs ──────────────────────────────────────────────────────────────────
async function loadLogs(mineOnly = false) {
  // Update active tab button
  document.getElementById('btn-all').className  = `btn btn-sm ${mineOnly ? 'btn-ghost' : 'btn-primary'}`;
  document.getElementById('btn-mine').className = `btn btn-sm ${mineOnly ? 'btn-primary' : 'btn-ghost'}`;

  const tbody = document.getElementById('logs-tbody');
  tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-dim);padding:2rem;">Loading…</td></tr>';

  try {
    const url  = mineOnly ? '/api/dashboard/logs?mine=true' : '/api/dashboard/logs';
    const res  = await fetch(url);
    if (!res.ok) {
      if (res.status === 401) {
        window.location.href = '/';
        return;
      }
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();

    if (!data.logs || data.logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-dim);padding:2rem;">No filter events recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = data.logs.map((log, i) => `
      <tr>
        <td class="text-muted text-xs">${i + 1}</td>
        <td class="text-xs text-muted" style="white-space:nowrap">${formatTime(log.timestamp)}</td>
        <td><span style="font-weight:600">${escapeHtml(log.username)}</span></td>
        <td class="truncate" style="color:var(--danger);opacity:.85">${escapeHtml(log.original_message)}</td>
        <td class="truncate">${escapeHtml(log.cleaned_message)}</td>
        <td><span style="color:var(--warning);font-size:.8rem">${escapeHtml(log.toxic_words)}</span></td>
        <td>${scoreBadge(log.toxicity_score)}</td>
        <td>${actionBadge(log.action)}</td>
        <td class="truncate" style="font-size:.78rem;color:var(--text-muted)">${escapeHtml(log.suggestion)}</td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--danger)">Error loading logs: ${e.message}</td></tr>`;
  }
}

// ── Logout ─────────────────────────────────────────────────────────────────────
async function logout() {
  await fetch('/api/logout', { method: 'POST' });
  window.location.href = '/';
}

// ── Init ───────────────────────────────────────────────────────────────────────
async function init() {
  try {
    const meRes  = await fetch('/api/me');
    if (!meRes.ok) {
      console.error('Me API error:', meRes.status);
      window.location.href = '/';
      return;
    }
    const meData = await meRes.json();
    if (!meData.logged_in) { window.location.href = '/'; return; }
    document.getElementById('header-username').textContent = `👤 ${meData.username}`;

    await loadStats();
    await loadLogs(false);
    await loadUsersAdmin();
    await loadAdminMessages();

    // Auto-refresh every 30s
    setInterval(() => { loadStats(); loadLogs(false); }, 30000);
  } catch (e) {
    console.error('Dashboard init error:', e);
    showToast('Error', 'Failed to load dashboard: ' + e.message, 'danger');
  }
}

document.addEventListener('DOMContentLoaded', init);
