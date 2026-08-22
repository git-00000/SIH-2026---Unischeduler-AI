/*
 * Shared front-end utilities loaded on every page (via base.html).
 * Keeps a tiny fetch wrapper + toast/loading helpers + the dashboard
 * stat-card renderer, so individual page scripts stay short.
 */
const API = {
  async _req(method, url, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok) {
      const msg = (data && (data.error || data.message)) || `Request failed (${res.status})`;
      throw new Error(msg);
    }
    return data;
  },
  get(url) { return this._req('GET', url); },
  post(url, body) { return this._req('POST', url, body); },
  put(url, body) { return this._req('PUT', url, body); },
  del(url) { return this._req('DELETE', url); },
};

function showToast(message, type = 'success') {
  let region = document.getElementById('toast-region');
  if (!region) {
    region = document.createElement('div');
    region.id = 'toast-region';
    region.style.position = 'fixed';
    region.style.top = '18px';
    region.style.right = '18px';
    region.style.zIndex = 3000;
    region.style.display = 'flex';
    region.style.flexDirection = 'column';
    region.style.gap = '8px';
    document.body.appendChild(region);
  }
  const el = document.createElement('div');
  el.className = `alert alert-${type === 'error' ? 'danger' : type} shadow-sm mb-0`;
  el.style.minWidth = '260px';
  el.textContent = message;
  region.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

function setLoading(active, message) {
  let overlay = document.getElementById('loading-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `<div class="spinner-ring"></div><div id="loading-msg" style="font-size:.9rem;"></div>`;
    document.body.appendChild(overlay);
  }
  document.getElementById('loading-msg').textContent = message || 'Working…';
  overlay.classList.toggle('active', !!active);
}

async function loadDepartmentsInto(selectEl, includeAll) {
  const departments = await API.get('/api/departments');
  selectEl.innerHTML = (includeAll ? '<option value="">All departments</option>' : '') +
    departments.map(d => `<option value="${d.id}">${escapeHtml(d.name)} (${escapeHtml(d.code)})</option>`).join('');
  return departments;
}

function coursePillClass(type) {
  const map = {
    'Core': 'pill-core',
    'Elective': 'pill-elective',
    'Multidisciplinary': 'pill-multidisciplinary',
    'Skill Enhancement': 'pill-skill',
    'Ability Enhancement': 'pill-ability',
    'Value Added': 'pill-value',
  };
  return map[type] || 'pill-core';
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

// ---- Dashboard stat cards (only runs if #stat-cards exists on the page) ----
async function loadDashboardStats() {
  const container = document.getElementById('stat-cards');
  if (!container) return;
  try {
    const s = await API.get('/api/dashboard/summary');
    const cards = [
      ['Students', s.total_students, '#12213d'],
      ['Teachers', s.total_teachers, '#12213d'],
      ['Courses', s.total_courses, '#12213d'],
      ['Rooms', s.total_rooms, '#12213d'],
      ['Student Groups', s.total_groups, '#12213d'],
      ['Multidisciplinary Courses', s.multidisciplinary_courses, '#e8a33d'],
      ['Hard Conflicts', s.hard_conflicts ?? '—', s.hard_conflicts ? '#c2483a' : '#2f6f62'],
      ['Soft Conflicts', s.soft_conflicts ?? '—', '#e8a33d'],
      ['Room Utilization', s.room_utilization + '%', '#2f6f62'],
      ['Teacher Utilization', s.teacher_utilization + '%', '#2f6f62'],
      ['Optimization Score', s.optimization_score ?? '—', '#2f6f62'],
      ['Last Generated', s.last_generation_time ? new Date(s.last_generation_time).toLocaleString() : 'Never', '#12213d'],
    ];
    container.innerHTML = cards.map(([label, value, color]) => `
      <div class="col-6 col-lg-3">
        <div class="stat-card">
          <div class="stat-accent" style="background:${color};"></div>
          <div class="stat-value">${value}</div>
          <div class="stat-label">${label}</div>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = `<div class="col-12"><div class="alert alert-warning">Could not load dashboard summary: ${escapeHtml(e.message)}</div></div>`;
  }
}

document.addEventListener('DOMContentLoaded', loadDashboardStats);
