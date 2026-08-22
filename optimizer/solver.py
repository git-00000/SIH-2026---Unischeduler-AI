"""
Thin wrapper around the CP-SAT solver so timing / status handling lives in
one place.
"""
import time
from ortools.sat.python import cp_model as cp_model_module


STATUS_NAMES = {
    cp_model_module.OPTIMAL: "OPTIMAL",
    cp_model_module.FEASIBLE: "FEASIBLE",
    cp_model_module.INFEASIBLE: "INFEASIBLE",
    cp_model_module.MODEL_INVALID: "MODEL_INVALID",
    cp_model_module.UNKNOWN: "UNKNOWN",
}


def solve_model(model, time_limit_seconds=30, num_workers=8):
    solver = cp_model_module.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = num_workers
    solver.parameters.random_seed = 42

    start = time.time()
    status = solver.Solve(model)
    elapsed = time.time() - start

    return {
        "solver": solver,
        "status": status,
        "status_name": STATUS_NAMES.get(status, "UNKNOWN"),
        "elapsed_seconds": elapsed,
        "objective_value": solver.ObjectiveValue() if status in (
            cp_model_module.OPTIMAL, cp_model_module.FEASIBLE
        ) else None,
    }
