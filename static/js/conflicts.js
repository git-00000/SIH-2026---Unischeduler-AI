function renderConflictList(containerId, conflicts) {
  const el = document.getElementById(containerId);
  if (!conflicts.length) {
    el.innerHTML = `<div class="empty-state py-3"><p class="mb-0">No conflicts recorded for this stage. 🎉</p></div>`;
    return;
  }
  el.innerHTML = conflicts.map(c => `
    <div class="conflict-item ${c.severity === 'soft' ? 'soft' : ''}">
      <span class="pill ${c.severity === 'hard' ? 'pill-hard' : 'pill-soft'}">${c.severity.toUpperCase()}</span>
      <span class="text-muted" style="font-size:.72rem; text-transform:uppercase;"> ${escapeHtml(c.conflict_type)}</span>
      <p class="mb-0 mt-1">${escapeHtml(c.description)}</p>
    </div>
  `).join('');
}

async function loadConflicts() {
  try {
    const [before, after] = await Promise.all([
      API.get('/api/conflicts?stage=before'),
      API.get('/api/conflicts?stage=after'),
    ]);
    renderConflictList('conflicts-before', before);
    renderConflictList('conflicts-after', after);
  } catch (e) {
    showToast(e.message, 'error');
  }
}

document.addEventListener('DOMContentLoaded', loadConflicts);
