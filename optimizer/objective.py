"""
Builds the weighted objective function.

Hard constraints in this model can never be violated by a feasible solution
(they are real CP-SAT constraints, not penalties), so the objective only
needs to minimise the weighted sum of soft-constraint badness terms. If a
"preserve previous assignment" bonus is supplied (used by re-optimization),
it is subtracted so that keeping an existing assignment is rewarded.
"""


def apply_objective(cp_model, soft_terms, preserve_terms=None, preserve_weight=3):
    objective_expr = []
    for weight, var in soft_terms:
        objective_expr.append(weight * var)

    if preserve_terms:
        # preserve_terms: list of BoolVars that equal 1 when an assignment
        # matches a previous timetable entry. Reward (negative penalty) for
        # keeping them, which biases re-optimisation towards minimal change.
        for var in preserve_terms:
            objective_expr.append(-preserve_weight * var)

    cp_model.Minimize(sum(objective_expr))
