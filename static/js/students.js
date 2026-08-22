async function loadGroups() {
  const groups = await API.get('/api/student-groups');
  const tbody = document.querySelector('#group-table tbody');
  tbody.innerHTML = groups.length ? groups.map(g => `
    <tr><td><strong>${escapeHtml(g.name)}</strong></td><td>${escapeHtml(g.department)}</td>
    <td>${g.semester}</td><td>${g.strength}</td>
    <td><button class="btn btn-sm btn-outline-danger" onclick="deleteGroup(${g.id})">Delete</button></td></tr>
  `).join('') : `<tr><td colspan="5" class="text-center text-muted py-4">No student groups yet.</td></tr>`;

  document.getElementById('s-group').innerHTML =
    '<option value="">— none —</option>' + groups.map(g => `<option value="${g.id}">${escapeHtml(g.name)}</option>`).join('');
}

async function deleteGroup(id) {
  if (!confirm('Delete this group?')) return;
  try { await API.del(`/api/student-groups/${id}`); showToast('Group deleted'); loadGroups(); }
  catch (e) { showToast(e.message, 'error'); }
}

document.getElementById('save-group').addEventListener('click', async () => {
  const payload = {
    name: document.getElementById('g-name').value.trim(),
    department_id: parseInt(document.getElementById('g-dept').value),
    semester: parseInt(document.getElementById('g-sem').value),
    strength: parseInt(document.getElementById('g-strength').value),
  };
  try {
    await API.post('/api/student-groups', payload);
    showToast('Group added');
    bootstrap.Modal.getInstance(document.getElementById('groupModal')).hide();
    document.getElementById('group-form').reset();
    loadGroups();
  } catch (e) { showToast(e.message, 'error'); }
});

async function loadStudents() {
  const students = await API.get('/api/students');
  const tbody = document.querySelector('#student-table tbody');
  tbody.innerHTML = students.length ? students.map(s => `
    <tr><td>${escapeHtml(s.roll_number)}</td><td>${escapeHtml(s.name)}</td>
    <td>${escapeHtml(s.department)}</td><td>${s.semester}</td><td>${escapeHtml(s.group || '—')}</td>
    <td><button class="btn btn-sm btn-outline-danger" onclick="deleteStudent(${s.id})">Delete</button></td></tr>
  `).join('') : `<tr><td colspan="6" class="text-center text-muted py-4">No students yet.</td></tr>`;
}

async function deleteStudent(id) {
  if (!confirm('Delete this student?')) return;
  try { await API.del(`/api/students/${id}`); showToast('Student deleted'); loadStudents(); }
  catch (e) { showToast(e.message, 'error'); }
}

document.getElementById('save-student').addEventListener('click', async () => {
  const payload = {
    name: document.getElementById('s-name').value.trim(),
    roll_number: document.getElementById('s-roll').value.trim(),
    department_id: parseInt(document.getElementById('s-dept').value),
    semester: parseInt(document.getElementById('s-sem').value),
    group_id: document.getElementById('s-group').value ? parseInt(document.getElementById('s-group').value) : null,
  };
  try {
    await API.post('/api/students', payload);
    showToast('Student added');
    bootstrap.Modal.getInstance(document.getElementById('studentModal')).hide();
    document.getElementById('student-form').reset();
    loadStudents();
  } catch (e) { showToast(e.message, 'error'); }
});

document.addEventListener('DOMContentLoaded', async () => {
  await loadDepartmentsInto(document.getElementById('g-dept'), false);
  await loadDepartmentsInto(document.getElementById('s-dept'), false);
  await loadGroups();
  await loadStudents();
});
