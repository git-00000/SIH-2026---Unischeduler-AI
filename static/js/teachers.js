async function loadTeachers() {
  const teachers = await API.get('/api/teachers');
  const tbody = document.querySelector('#teacher-table tbody');
  tbody.innerHTML = teachers.length ? teachers.map(t => `
    <tr>
      <td><strong>${escapeHtml(t.name)}</strong></td>
      <td>${escapeHtml(t.email)}</td>
      <td>${escapeHtml(t.department)}</td>
      <td>${t.max_hours_per_week}</td>
      <td><button class="btn btn-sm btn-outline-danger" onclick="deleteTeacher(${t.id})">Delete</button></td>
    </tr>`).join('') : `<tr><td colspan="5" class="text-center text-muted py-4">No teachers yet.</td></tr>`;

  const teacherSelect = document.getElementById('off-teacher');
  teacherSelect.innerHTML = teachers.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('');
}

async function deleteTeacher(id) {
  if (!confirm('Delete this teacher?')) return;
  try { await API.del(`/api/teachers/${id}`); showToast('Teacher deleted'); loadTeachers(); }
  catch (e) { showToast(e.message, 'error'); }
}

document.getElementById('save-teacher').addEventListener('click', async () => {
  const payload = {
    name: document.getElementById('t-name').value.trim(),
    email: document.getElementById('t-email').value.trim(),
    department_id: parseInt(document.getElementById('t-dept').value),
    max_hours_per_week: parseInt(document.getElementById('t-max').value) || 18,
  };
  try {
    await API.post('/api/teachers', payload);
    showToast('Teacher added');
    bootstrap.Modal.getInstance(document.getElementById('teacherModal')).hide();
    document.getElementById('teacher-form').reset();
    loadTeachers();
  } catch (e) { showToast(e.message, 'error'); }
});

async function loadCoursesIntoSelect() {
  const courses = await API.get('/api/courses');
  document.getElementById('off-course').innerHTML =
    courses.map(c => `<option value="${c.id}">${escapeHtml(c.course_code)} — ${escapeHtml(c.name)}</option>`).join('');
}

async function loadOfferings() {
  const rows = await API.get('/api/course-offerings');
  const tbody = document.querySelector('#offering-table tbody');
  tbody.innerHTML = rows.length ? rows.map(o => `
    <tr><td>${escapeHtml(o.course_name)}</td><td>${escapeHtml(o.teacher_name)}</td>
    <td><button class="btn btn-sm btn-outline-danger" onclick="deleteOffering(${o.id})">Remove</button></td></tr>
  `).join('') : `<tr><td colspan="3" class="text-center text-muted py-3">No qualifications assigned yet.</td></tr>`;
}

async function addOffering() {
  const course_id = parseInt(document.getElementById('off-course').value);
  const teacher_id = parseInt(document.getElementById('off-teacher').value);
  if (!course_id || !teacher_id) { showToast('Select a course and a teacher', 'error'); return; }
  try {
    await API.post('/api/course-offerings', { course_id, teacher_id });
    showToast('Teacher assigned to course');
    loadOfferings();
  } catch (e) { showToast(e.message, 'error'); }
}

async function deleteOffering(id) {
  try { await API.del(`/api/course-offerings/${id}`); loadOfferings(); }
  catch (e) { showToast(e.message, 'error'); }
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadDepartmentsInto(document.getElementById('t-dept'), false);
  await loadTeachers();
  await loadCoursesIntoSelect();
  await loadOfferings();
});
