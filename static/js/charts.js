/* Renders the five Chart.js dashboard charts using /api/dashboard/charts */
const PALETTE = ['#12213d', '#e8a33d', '#2f6f62', '#6a5acd', '#c2483a', '#1c6f9c', '#5c7a1e'];

async function loadDashboardCharts() {
  let data;
  try {
    data = await API.get('/api/dashboard/charts');
  } catch (e) {
    showToast('Could not load charts: ' + e.message, 'error');
    return;
  }

  const roomCtx = document.getElementById('chart-room');
  if (roomCtx) {
    new Chart(roomCtx, {
      type: 'bar',
      data: {
        labels: data.room_utilization.map(r => r.room),
        datasets: [{ label: 'Classes scheduled', data: data.room_utilization.map(r => r.classes), backgroundColor: '#12213d', borderRadius: 4 }],
      },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
  }

  const teacherCtx = document.getElementById('chart-teacher');
  if (teacherCtx) {
    new Chart(teacherCtx, {
      type: 'bar',
      data: {
        labels: data.teacher_workload.map(t => t.teacher),
        datasets: [{ label: 'Periods/week', data: data.teacher_workload.map(t => t.classes), backgroundColor: '#2f6f62', borderRadius: 4 }],
      },
      options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
  }

  const typeCtx = document.getElementById('chart-coursetype');
  if (typeCtx) {
    new Chart(typeCtx, {
      type: 'doughnut',
      data: {
        labels: data.course_type_distribution.map(d => d.type),
        datasets: [{ data: data.course_type_distribution.map(d => d.count), backgroundColor: PALETTE }],
      },
      options: { plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } } },
    });
  }

  const deptCtx = document.getElementById('chart-dept');
  if (deptCtx) {
    new Chart(deptCtx, {
      type: 'pie',
      data: {
        labels: data.department_course_distribution.map(d => d.department),
        datasets: [{ data: data.department_course_distribution.map(d => d.count), backgroundColor: PALETTE }],
      },
      options: { plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } } },
    });
  }

  const dailyCtx = document.getElementById('chart-daily');
  if (dailyCtx) {
    const order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
    const sorted = [...data.daily_distribution].sort((a, b) => order.indexOf(a.day) - order.indexOf(b.day));
    new Chart(dailyCtx, {
      type: 'line',
      data: {
        labels: sorted.map(d => d.day),
        datasets: [{ label: 'Classes', data: sorted.map(d => d.count), borderColor: '#e8a33d', backgroundColor: 'rgba(232,163,61,.2)', fill: true, tension: .35 }],
      },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
  }
}

document.addEventListener('DOMContentLoaded', loadDashboardCharts);
