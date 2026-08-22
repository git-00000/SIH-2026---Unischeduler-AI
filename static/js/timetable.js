function pillTypeClass(courseType) {
  const t = (courseType || '').toLowerCase().replace(/ /g, '.');
  if (t.includes('core')) return 'core';
  if (t.includes('elective')) return 'elective';
  if (t.includes('multidisciplinary')) return 'multidisciplinary';
  return 'skill.enhancement';
}

async function loadEntitySelect() {
  const mode = document.getElementById('view-mode').value;
  const sel = document.getElementById('entity-select');
  document.getElementById('entity-label').textContent = mode === 'group' ? 'Student Group' : 'Teacher';
  if (mode === 'group') {
    const groups = await API.get('/api/student-groups');
    sel.innerHTML = groups.map(g => `<option value="${g.id}">${escapeHtml(g.name)}</option>`).join('');
  } else {
    const teachers = await API.get('/api/teachers');
    sel.innerHTML = teachers.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('');
  }
  renderGrid();
}

async function renderGrid() {
  const mode = document.getElementById('view-mode').value;
  const entityId = document.getElementById('entity-select').value;
  const wrap = document.getElementById('grid-wrap');
  if (!entityId) return;

  const slots = await API.get('/api/time-slots');
  const days = [...new Set(slots.map(s => s.day))];
  const periods = [...new Map(slots.map(s => [s.period_number, s])).values()]
    .sort((a, b) => a.period_number - b.period_number);

  const qs = mode === 'group' ? `group_id=${entityId}` : `teacher_id=${entityId}`;
  const data = await API.get(`/api/timetable?${qs}`);

  if (!data.run) {
    wrap.innerHTML = `<div class="empty-state"><h4>No timetable generated yet</h4><p>Go to "Generate Timetable" to run the AI optimizer.</p></div>`;
    return;
  }

  const byDayPeriod = {};
  data.entries.forEach(e => { byDayPeriod[`${e.day}-${e.period_number}`] = e; });

  let html = '<div class="table-responsive"><table class="tt-grid"><thead><tr><th></th>';
  days.forEach(d => html += `<th>${d}</th>`);
  html += '</tr></thead><tbody>';

  periods.forEach(p => {
    const slotForPeriod = slots.find(s => s.period_number === p.period_number);
    html += `<tr><td class="tt-time-col">${slotForPeriod ? slotForPeriod.start_time : ''}<br>P${p.period_number}</td>`;
    days.forEach(d => {
      const slotMeta = slots.find(s => s.day === d && s.period_number === p.period_number);
      if (slotMeta && slotMeta.is_break) {
        html += `<td class="tt-cell break text-center text-muted">Lunch</td>`;
        return;
      }
      const e = byDayPeriod[`${d}-${p.period_number}`];
      if (!e) {
        html += `<td class="tt-cell">&nbsp;</td>`;
      } else {
        const typeClass = pillTypeClass(e.course_type);
        const labClass = e.course_type ? '' : '';
        html += `<td class="tt-cell filled ${typeClass}">
          <span class="c-code">${escapeHtml(e.course_code)}</span>
          <span class="c-meta">${escapeHtml(e.teacher_name)}</span>
          <span class="c-meta">${escapeHtml(e.room_number)} · ${escapeHtml(e.group_name)}</span>
        </td>`;
      }
    });
    html += '</tr>';
  });

  html += '</tbody></table></div>';
  wrap.innerHTML = html;
}

document.getElementById('view-mode').addEventListener('change', loadEntitySelect);
document.getElementById('entity-select').addEventListener('change', renderGrid);
document.addEventListener('DOMContentLoaded', loadEntitySelect);
