"""
Anonymized representative excerpt from the scheduling system.

This public sample is intentionally simplified and contains no real
school, teacher, class, or timetable data.

The production system contains additional constraints, parsing,
validation, objectives, and school-specific rules.
"""

from collections import defaultdict

from ortools.sat.python import cp_model


def build_assignment_model(
    classes,
    slots,
    required_periods,
    teacher_of,
    unavailable_slots=None,
    fixed_slots=None,
):
    """
    Build a small CP-SAT model demonstrating several core hard constraints.

    Args:
        classes:
            Iterable of anonymized class/course identifiers.

        slots:
            Available timetable slots.

        required_periods:
            Mapping:
                class_id -> number of periods that must be scheduled

        teacher_of:
            Mapping:
                class_id -> anonymized teacher identifier

        unavailable_slots:
            Optional mapping:
                teacher_id -> set(slot_index)

        fixed_slots:
            Optional mapping:
                class_id -> set(slot_index)

    Returns:
        model:
            OR-Tools CP-SAT model.

        x:
            x[class_id][slot_index] is 1 when that class is scheduled
            in that slot.
    """

    unavailable_slots = unavailable_slots or {}
    fixed_slots = fixed_slots or {}

    model = cp_model.CpModel()

    # ------------------------------------------------------------
    # Decision variables
    # ------------------------------------------------------------
    # x[c][t] = 1 means class/course c is placed at slot t.
    x = {
        c: [
            model.NewBoolVar(f"x_{c}_{t}")
            for t in range(len(slots))
        ]
        for c in classes
    }

    # ------------------------------------------------------------
    # 1. Required number of periods
    # ------------------------------------------------------------
    # Every class/course must receive exactly its required load.
    for c in classes:
        model.Add(
            sum(x[c][t] for t in range(len(slots)))
            == required_periods[c]
        )

    # ------------------------------------------------------------
    # 2. Teacher conflict constraint
    # ------------------------------------------------------------
    # One teacher cannot teach two classes at the same time.
    teacher_to_classes = defaultdict(list)

    for c in classes:
        teacher_to_classes[teacher_of[c]].append(c)

    for teacher, assigned_classes in teacher_to_classes.items():
        for t in range(len(slots)):
            model.Add(
                sum(x[c][t] for c in assigned_classes) <= 1
            )

    # ------------------------------------------------------------
    # 3. Teacher unavailable slots
    # ------------------------------------------------------------
    # If a teacher is unavailable, all classes taught by that teacher
    # are forbidden from that slot.
    for teacher, blocked_slots in unavailable_slots.items():
        for c in teacher_to_classes.get(teacher, []):
            for t in blocked_slots:
                if 0 <= t < len(slots):
                    model.Add(x[c][t] == 0)

    # ------------------------------------------------------------
    # 4. Fixed-slot lessons
    # ------------------------------------------------------------
    # Some lessons must occur at explicitly declared slots.
    for c, required_slots in fixed_slots.items():
        for t in required_slots:
            if 0 <= t < len(slots):
                model.Add(x[c][t] == 1)

    return model, x


def solve_demo():
    """
    Tiny synthetic example.

    All identifiers below are fictional and are included only so the
    public sample can be executed independently.
    """

    classes = [
        "CLASS_A_MATH",
        "CLASS_B_MATH",
        "CLASS_C_SCIENCE",
    ]

    slots = list(range(8))

    required_periods = {
        "CLASS_A_MATH": 2,
        "CLASS_B_MATH": 2,
        "CLASS_C_SCIENCE": 2,
    }

    teacher_of = {
        "CLASS_A_MATH": "TEACHER_01",
        "CLASS_B_MATH": "TEACHER_01",
        "CLASS_C_SCIENCE": "TEACHER_02",
    }

    unavailable_slots = {
        "TEACHER_01": {0},
        "TEACHER_02": {7},
    }

    fixed_slots = {
        "CLASS_C_SCIENCE": {3},
    }

    model, x = build_assignment_model(
        classes=classes,
        slots=slots,
        required_periods=required_periods,
        teacher_of=teacher_of,
        unavailable_slots=unavailable_slots,
        fixed_slots=fixed_slots,
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        print("No feasible schedule.")
        return

    for c in classes:
        assigned = [
            t
            for t in range(len(slots))
            if solver.Value(x[c][t])
        ]
        print(f"{c}: {assigned}")


if __name__ == "__main__":
    solve_demo()
