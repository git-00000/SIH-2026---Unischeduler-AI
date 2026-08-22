function resultCard(run, message) {
  const badgeClass = (run.status === 'OPTIMAL' || run.status === 'FEASIBLE') ? 'pill-elective' : 'pill-hard';
  return `
    <div class="alert alert-light border">
      <span class="pill ${badgeClass}">${escapeHtml(run.status)}</span>
      <p class="mb-1 mt-2">${escapeHtml(message)}</p>
      <ul class="mb-0" style="font-size:.85rem;">
        <li>Objective score: <strong>${run.objective_score ?? '—'}</strong></li>
        <li>Hard conflicts: <strong>${run.hard_conflicts}</strong> | Soft conflicts: <strong>${run.soft_conflicts}</strong></li>
        <li>Generation time: <strong>${run.generation_time?.toFixed(2)}s</strong></li>
        ${run.notes ? `<li class="text-danger">${escapeHtml(run.notes)}</li>` : ''}
      </ul>
      <a href="/timetable" class="btn btn-sm btn-navy mt-2">View Timetable</a>
      <a href="/insights" class="btn btn-sm btn-outline-secondary mt-2">View AI Insights</a>
    </div>`;
}

document.getElementById('btn-generate').addEventListener('click', async () => {
  setLoading(true, 'Running CP-SAT optimizer…');
  try {
    const data = await API.post('/api/generate-timetable', {});
    document.getElementById('generate-result').innerHTML = resultCard(data.run, data.message);
    showToast('Generation complete');
    loadRuns();
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    setLoading(false);
  }
});

document.getElementById('btn-reoptimize').addEventListener('click', async () => {
  const roomId = document.getElementById('reopt-room').value;
  if (!roomId) { showToast('Select a room to mark unavailable', 'error'); return; }
  setLoading(true, 'Marking room unavailable and re-optimizing…');
  try {
    await API.post(`/api/rooms/${roomId}/toggle-availability`, { is_available: false });
    const data = await API.post('/api/reoptimize', {});
    document.getElementById('reoptimize-result').innerHTML =
      resultCard(data.run, data.message) +
      `<p class="text-muted" style="font-size:.8rem;">${data.preserved_assignments} previous assignment(s) were preserved unchanged.</p>`;
    showToast('Re-optimization complete');
    loadRuns();
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    setLoading(false);
  }
});

async function loadRunsAndRooms() {
  const rooms = await API.get('/api/rooms');
  document.getElementById('reopt-room').innerHTML = rooms
    .filter(r => r.is_available)
    .map(r => `<option value="${r.id}">${escapeHtml(r.room_number)} (${escapeHtml(r.room_type)})</option>`).join('');
  loadRuns();
}

async function loadRuns() {
  const runs = await API.get('/api/generation-runs');
  const tbody = document.querySelector('#runs-table tbody');
  tbody.innerHTML = runs.length ? runs.map(r => `
    <tr>
      <td>${new Date(r.timestamp).toLocaleString()}</td>
      <td>${escapeHtml(r.status)}</td>
      <td>${r.objective_score ?? '—'}</td>
      <td>${r.hard_conflicts}</td>
      <td>${r.soft_conflicts}</td>
      <td>${r.generation_time?.toFixed(2)}</td>
      <td>${r.is_active ? '✓' : ''}</td>
    </tr>`).join('') : `<tr><td colspan="7" class="text-center text-muted py-3">No runs yet.</td></tr>`;
}

document.addEventListener('DOMContentLoaded', loadRunsAndRooms);
