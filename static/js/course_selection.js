let allCourses = [];

async function loadGroupsAndCourses() {
  const groups = await API.get('/api/student-groups');
  document.getElementById('cs-group').innerHTML =
    groups.map(g => `<option value="${g.id}" data-dept="${g.department_id}">${escapeHtml(g.name)} (${escapeHtml(g.department)})</option>`).join('');

  allCourses = await API.get('/api/courses');
  document.getElementById('cs-course').innerHTML =
    allCourses.map(c => `<option value="${c.id}">${escapeHtml(c.course_code)} — ${escapeHtml(c.name)} [${escapeHtml(c.department)}]</option>`).join('');

  if (groups.length) loadSelections();
}

async function loadSelections() {
  const groupId = document.getElementById('cs-group').value;
  if (!groupId) return;
  const rows = await API.get(`/api/course-selection?group_id=${groupId}`);
  const tbody = document.querySelector('#selection-table tbody');
  tbody.innerHTML = rows.length ? rows.map(s => `
    <tr>
      <td><strong>${escapeHtml(s.course_code)}</strong> — ${escapeHtml(s.course_name)}</td>
      <td><span class="pill ${coursePillClass(s.course_type)}">${escapeHtml(s.course_type)}</span></td>
      <td>${s.is_cross_department ? '<span class="pill pill-multidisciplinary">Cross-department</span>' : '<span class="text-muted">Same dept.</span>'}</td>
      <td><button class="btn btn-sm btn-outline-danger" onclick="removeSelection(${s.id})">Remove</button></td>
    </tr>`).join('') : `<tr><td colspan="4" class="text-center text-muted py-4">No courses selected for this group yet.</td></tr>`;
}

async function addSelection() {
  const group_id = parseInt(document.getElementById('cs-group').value);
  const course_id = parseInt(document.getElementById('cs-course').value);
  if (!group_id || !course_id) return;
  try {
    await API.post('/api/course-selection', { group_id, course_id });
    showToast('Course added to group');
    loadSelections();
  } catch (e) { showToast(e.message, 'error'); }
}

async function removeSelection(id) {
  try { await API.del(`/api/course-selection/${id}`); loadSelections(); }
  catch (e) { showToast(e.message, 'error'); }
}

document.getElementById('cs-group').addEventListener('change', loadSelections);
document.addEventListener('DOMContentLoaded', loadGroupsAndCourses);
