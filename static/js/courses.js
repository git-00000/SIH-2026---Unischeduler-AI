function courseRow(c) {
  return `<tr>
    <td><strong>${escapeHtml(c.course_code)}</strong></td>
    <td>${escapeHtml(c.name)}</td>
    <td>${escapeHtml(c.department)}</td>
    <td><span class="pill ${coursePillClass(c.course_type)}">${escapeHtml(c.course_type)}</span></td>
    <td>${c.credits}</td>
    <td>${c.hours_per_week}</td>
    <td>${c.requires_lab ? 'Yes' : 'No'}</td>
    <td>${c.semester}</td>
    <td>${c.capacity}</td>
    <td><button class="btn btn-sm btn-outline-danger" onclick="deleteCourse(${c.id})">Delete</button></td>
  </tr>`;
}

async function loadCourses() {
  const deptId = document.getElementById('filter-dept').value;
  const url = deptId ? `/api/courses?department_id=${deptId}` : '/api/courses';
  const courses = await API.get(url);
  const tbody = document.querySelector('#course-table tbody');
  tbody.innerHTML = courses.length ? courses.map(courseRow).join('') :
    `<tr><td colspan="10" class="text-center text-muted py-4">No courses yet. Add one to get started.</td></tr>`;
}

async function deleteCourse(id) {
  if (!confirm('Delete this course? This cannot be undone.')) return;
  try {
    await API.del(`/api/courses/${id}`);
    showToast('Course deleted');
    loadCourses();
  } catch (e) { showToast(e.message, 'error'); }
}

document.getElementById('save-course').addEventListener('click', async () => {
  const payload = {
    course_code: document.getElementById('f-code').value.trim(),
    name: document.getElementById('f-name').value.trim(),
    department_id: parseInt(document.getElementById('f-dept').value),
    course_type: document.getElementById('f-type').value,
    credits: parseInt(document.getElementById('f-credits').value) || 3,
    hours_per_week: parseInt(document.getElementById('f-hours').value),
    semester: parseInt(document.getElementById('f-sem').value) || 1,
    capacity: parseInt(document.getElementById('f-cap').value) || 60,
    requires_lab: document.getElementById('f-lab').checked,
  };
  try {
    await API.post('/api/courses', payload);
    showToast('Course added');
    bootstrap.Modal.getInstance(document.getElementById('courseModal')).hide();
    document.getElementById('course-form').reset();
    loadCourses();
  } catch (e) { showToast(e.message, 'error'); }
});

document.getElementById('filter-dept').addEventListener('change', loadCourses);

document.addEventListener('DOMContentLoaded', async () => {
  await loadDepartmentsInto(document.getElementById('filter-dept'), true);
  await loadDepartmentsInto(document.getElementById('f-dept'), false);
  loadCourses();
});
