"""Anonymized representative scenario tests for the scheduling portfolio.

The real private project uses OR-Tools CP-SAT. This public sample keeps the
core testing idea only: independently state the requirement, construct success
and failure cases, and make sure validation does not silently lower a Hard
constraint.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    name: str
    capacity: int
    declared_target: int
    strength: str
    expected_feasible: bool
    expected_required: int


def resolve_required_target(declared_target, capacity, strength):
    if strength == "hard":
        return declared_target
    if strength == "soft":
        return min(declared_target, capacity)
    raise ValueError("unsupported strength")


def synthetic_solver(capacity, required_target):
    feasible = required_target <= capacity
    return {"feasible": feasible, "achieved": capacity if feasible else 0}


def validate_exported_result(declared_required, achieved):
    gap = max(0, declared_required - achieved)
    return {
        "required": declared_required,
        "achieved": achieved,
        "gap": gap,
        "status": "PASS" if gap == 0 else "FAIL",
    }


def run_scenario(scenario):
    required = resolve_required_target(
        scenario.declared_target,
        scenario.capacity,
        scenario.strength,
    )
    assert required == scenario.expected_required

    result = synthetic_solver(scenario.capacity, required)
    assert result["feasible"] is scenario.expected_feasible
    return result


def test_hard_target_above_capacity_is_rejected():
    case = Scenario("hard_3_gt_2", 2, 3, "hard", False, 3)
    assert run_scenario(case)["feasible"] is False


def test_hard_target_equal_capacity_is_fulfilled():
    case = Scenario("hard_2_eq_2", 2, 2, "hard", True, 2)
    assert run_scenario(case)["achieved"] >= 2


def test_soft_target_can_be_capped():
    case = Scenario("soft_3_gt_2", 2, 3, "soft", True, 2)
    assert run_scenario(case)["feasible"] is True


def test_zero_capacity_hard_requirement_is_rejected():
    case = Scenario("hard_1_gt_0", 0, 1, "hard", False, 1)
    assert run_scenario(case)["feasible"] is False


def test_validator_keeps_original_hard_target():
    report = validate_exported_result(3, 2)
    assert report["required"] == 3
    assert report["achieved"] == 2
    assert report["gap"] == 1
    assert report["status"] == "FAIL"


def test_zero_achieved_reports_full_deficit():
    report = validate_exported_result(3, 0)
    assert report["gap"] == 3
    assert report["status"] == "FAIL"


def run_all():
    tests = [
        test_hard_target_above_capacity_is_rejected,
        test_hard_target_equal_capacity_is_fulfilled,
        test_soft_target_can_be_capped,
        test_zero_capacity_hard_requirement_is_rejected,
        test_validator_keeps_original_hard_target,
        test_zero_achieved_reports_full_deficit,
    ]
    for test in tests:
        test()
    print(f"PASS: {len(tests)} public scenario tests")


if __name__ == "__main__":
    run_all()
