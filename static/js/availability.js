let currentTeacherId = null;

async function loadTeacherSelect() {
  const teachers = await API.get('/api/teachers');
  const sel = document.getElementById('av-teacher');
  sel.innerHTML = teachers.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('');
  if (teachers.length) {
    currentTeacherId = teachers[0].id;
    loadAvailability();
  }
}

async function loadAvailability() {
  currentTeacherId = parseInt(document.getElementById('av-teacher').value);
  const rows = await API.get(`/api/teacher-availability?teacher_id=${currentTeacherId}`);
  const days = [...new Set(rows.map(r => r.day))];
  const periods = [...new Set(rows.map(r => r.period_number))].sort((a, b) => a - b);

  document.getElementById('av-head').innerHTML =
    '<th>Period</th>' + days.map(d => `<th class="text-center">${d}</th>`).join('');

  const byDayPeriod = {};
  rows.forEach(r => { byDayPeriod[`${r.day}-${r.period_number}`] = r; });

  document.getElementById('av-body').innerHTML = periods.map(p => {
    const cells = days.map(d => {
      const r = byDayPeriod[`${d}-${p}`];
      if (!r) return '<td></td>';
      if (r.is_break) return '<td class="text-center text-muted small">Break</td>';
      const cls = r.available ? 'btn-outline-success' : 'btn-danger';
      const label = r.available ? 'Available' : 'Unavailable';
      return `<td class="text-center">
        <button class="btn btn-sm ${cls}" style="width:110px;" onclick="toggleSlot(${r.time_slot_id}, ${!r.available})">${label}</button>
      </td>`;
    }).join('');
    const first = byDayPeriod[`${days[0]}-${p}`];
    const timeLabel = first ? `${first.start_time}-${first.end_time}` : '';
    return `<tr><td><strong>P${p}</strong><br><span class="text-muted small">${timeLabel}</span></td>${cells}</tr>`;
  }).join('');
}

async function toggleSlot(timeSlotId, makeAvailable) {
  try {
    await API.post('/api/teacher-availability', {
      teacher_id: currentTeacherId, time_slot_id: timeSlotId, available: makeAvailable,
    });
    loadAvailability();
  } catch (e) { showToast(e.message, 'error'); }
}

document.getElementById('av-teacher').addEventListener('change', loadAvailability);
document.addEventListener('DOMContentLoaded', loadTeacherSelect);
