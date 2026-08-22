async function loadInsights() {
  const body = document.getElementById('insights-body');
  try {
    const data = await API.get('/api/insights');
    if (!data.run) {
      return; // keep the default empty-state markup
    }
    const r = data.run;
    body.innerHTML = `
      <div class="alert alert-light border mb-3">
        <strong>Methodology:</strong> ${escapeHtml(data.methodology)}
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-3"><div class="stat-card"><div class="stat-value">${data.num_variables}</div><div class="stat-label">Decision Variables</div></div></div>
        <div class="col-md-3"><div class="stat-card"><div class="stat-value">${data.num_constraints}</div><div class="stat-label">Core Constraints</div></div></div>
        <div class="col-md-3"><div class="stat-card"><div class="stat-value">${data.solver_status}</div><div class="stat-label">Solver Status</div></div></div>
        <div class="col-md-3"><div class="stat-card"><div class="stat-value">${data.generation_time_seconds.toFixed(2)}s</div><div class="stat-label">Generation Time</div></div></div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-6">
          <div class="card card-pad">
            <h3 style="font-size:1rem;">Before Optimization <span class="text-muted small">(naive baseline)</span></h3>
            <p class="mb-1">Hard Conflicts: <strong class="text-danger">${data.before.hard_conflicts}</strong></p>
            <p class="mb-0">Soft Conflicts: <strong>${data.before.soft_conflicts}</strong></p>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card card-pad">
            <h3 style="font-size:1rem;">After CP-SAT Optimization</h3>
            <p class="mb-1">Hard Conflicts: <strong class="text-success">${data.after.hard_conflicts}</strong></p>
            <p class="mb-0">Soft Conflicts (weighted objective): <strong>${data.after.soft_conflicts}</strong></p>
          </div>
        </div>
      </div>

      <div class="card card-pad">
        <h3 style="font-size:1rem;">Optimization Improvement</h3>
        <div class="stat-value" style="font-size:2.4rem;">${data.optimization_improvement_percent}%</div>
        <p class="text-muted mb-0" style="font-size:.82rem;">
          Reduction in total (hard + soft) conflicts compared to a naive, non-optimized first-fit
          assignment of the same courses, teachers and rooms.
        </p>
      </div>
    `;
  } catch (e) {
    body.innerHTML = `<div class="alert alert-warning">${escapeHtml(e.message)}</div>`;
  }
}

document.addEventListener('DOMContentLoaded', loadInsights);
