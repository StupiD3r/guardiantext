/* auth.js  –  GuardianText Login / Register */

// ── Toast helper ───────────────────────────────────────────────────────────────
function showToast(title, body = '', type = '') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type ? 'toast-' + type : ''}`;
  toast.innerHTML = `<div class="toast-title">${title}</div>${body ? `<div class="toast-body">${body}</div>` : ''}`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4500);
}

// ── Tab switching ──────────────────────────────────────────────────────────────
function switchTab(tab) {
  document.getElementById('form-login').classList.toggle('hidden', tab !== 'login');
  document.getElementById('form-register').classList.toggle('hidden', tab !== 'register');
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-reg').classList.toggle('active', tab === 'register');
}

// ── Login ──────────────────────────────────────────────────────────────────────
async function doLogin() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl    = document.getElementById('login-error');

  errEl.classList.add('hidden');
  if (!username || !password) {
    errEl.textContent = 'Please fill in all fields.';
    errEl.classList.remove('hidden');
    return;
  }

  try {
    const res  = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (data.success) {
      window.location.href = '/chat.html';
    } else {
      errEl.textContent = data.message || 'Login failed.';
      errEl.classList.remove('hidden');
    }
  } catch (e) {
    errEl.textContent = 'Connection error. Is the server running?';
    errEl.classList.remove('hidden');
  }
}

// ── Register ───────────────────────────────────────────────────────────────────
async function doRegister() {
  const username = document.getElementById('reg-username').value.trim();
  const password = document.getElementById('reg-password').value;
  const confirm  = document.getElementById('reg-confirm').value;
  const errEl    = document.getElementById('reg-error');

  errEl.classList.add('hidden');
  if (!username || !password || !confirm) {
    errEl.textContent = 'Please fill in all fields.';
    errEl.classList.remove('hidden');
    return;
  }
  if (password !== confirm) {
    errEl.textContent = 'Passwords do not match.';
    errEl.classList.remove('hidden');
    return;
  }

  try {
    const res  = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('Account created! ✅', 'You can now sign in.', 'success');
      switchTab('login');
      document.getElementById('login-username').value = username;
    } else {
      errEl.textContent = data.message || 'Registration failed.';
      errEl.classList.remove('hidden');
    }
  } catch (e) {
    errEl.textContent = 'Connection error. Is the server running?';
    errEl.classList.remove('hidden');
  }
}

// ── Enter key support ──────────────────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter') return;
  const active = document.querySelector('.tab-btn.active')?.id;
  if (active === 'tab-login')  doLogin();
  if (active === 'tab-reg')    doRegister();
});

// ── Redirect if already logged in ─────────────────────────────────────────────
(async function checkSession() {
  try {
    const res  = await fetch('/api/me');
    const data = await res.json();
    if (data.logged_in) window.location.href = '/chat.html';
  } catch (_) {}
})();
