"""
Anonymized representative excerpt from the independent semantic oracle.

This public sample is intentionally simplified and contains no real school,
teacher, class, or timetable data.

The production oracle reads the raw workbook and exported timetable itself.
It does not import the Solver or reuse the Solver's parser as its authority.
That separation is deliberate: if the Solver misunderstands a rule, the
validator should not automatically repeat the same misunderstanding.
"""

from collections import Counter, defaultdict


SUPPORTED_CHECKS = {
    "course_count",
    "teacher_assignment",
    "teacher_conflict",
    "fixed_slot",
}


def _empty_report():
    return {
        "status": "ERROR",
        "independent_of_solver": True,
        "full_semantic_coverage": False,
        "violations": [],
        "unverified": [],
        "coverage": {},
        "metrics": {},
    }


def validate_schedule(
    source_courses,
    timetable_cells,
    *,
    unsupported_semantics=None,
):
    """Validate a timetable against independently supplied source facts.

    Parameters
    ----------
    source_courses:
        Iterable of dictionaries such as::

            {
                "class": "CLASS_A",
                "subject": "MATH",
                "count": 3,
                "teachers": {"TEACHER_01"},
                "fixed_slots": {(1, 2)},   # optional: (day, period)
            }

    timetable_cells:
        Mapping from ``(class_id, day, period)`` to either ``None`` or::

            {
                "subject": "MATH",
                "teachers": {"TEACHER_01"},
            }

    unsupported_semantics:
        Optional descriptions of rules that this small public oracle does not
        implement. These are reported as UNVERIFIED instead of being silently
        treated as PASS.

    Returns
    -------
    dict
        Validation report with PASS / FAIL / INCOMPLETE status.
    """

    report = _empty_report()
    unsupported_semantics = list(unsupported_semantics or [])

    # ------------------------------------------------------------
    # 1. Reconstruct expectations from the declared source facts.
    # ------------------------------------------------------------
    expected_counts = Counter()
    allowed_teachers = defaultdict(set)
    fixed_requirements = []
    known_classes = set()

    for record in source_courses:
        class_id = record["class"]
        subject = record["subject"]
        count = int(record["count"])
        teachers = frozenset(record.get("teachers", set()))

        if count < 0:
            raise ValueError("Course count must be non-negative.")

        known_classes.add(class_id)
        expected_counts[class_id, subject] += count
        allowed_teachers[class_id, subject].add(teachers)

        for day, period in record.get("fixed_slots", set()):
            fixed_requirements.append(
                (class_id, subject, day, period)
            )

    # ------------------------------------------------------------
    # 2. Read the produced timetable independently.
    # ------------------------------------------------------------
    actual_counts = Counter()
    teacher_busy = defaultdict(list)
    timetable_classes = set()

    for (class_id, day, period), cell in timetable_cells.items():
        timetable_classes.add(class_id)

        if cell is None:
            continue

        subject = cell["subject"]
        teachers = frozenset(cell.get("teachers", set()))

        actual_counts[class_id, subject] += 1

        # Teacher identity is checked against source data rather than against
        # a value supplied by the Solver itself.
        expected_teacher_sets = allowed_teachers.get(
            (class_id, subject),
            set(),
        )

        if teachers not in expected_teacher_sets:
            report["violations"].append(
                {
                    "type": "oracle_teacher_assignment",
                    "class": class_id,
                    "subject": subject,
                    "expected": [
                        sorted(option)
                        for option in expected_teacher_sets
                    ],
                    "actual": sorted(teachers),
                }
            )

        for teacher in teachers:
            teacher_busy[teacher, day, period].append(class_id)

    # ------------------------------------------------------------
    # 3. Missing class timetable.
    # ------------------------------------------------------------
    for class_id in sorted(known_classes - timetable_classes):
        report["violations"].append(
            {
                "type": "oracle_missing_class",
                "class": class_id,
            }
        )

    # ------------------------------------------------------------
    # 4. Weekly course-count check.
    # ------------------------------------------------------------
    for key in sorted(expected_counts.keys() | actual_counts.keys()):
        expected = expected_counts[key]
        actual = actual_counts[key]

        if expected != actual:
            report["violations"].append(
                {
                    "type": "oracle_course_count",
                    "class": key[0],
                    "subject": key[1],
                    "expected": expected,
                    "actual": actual,
                }
            )

    # ------------------------------------------------------------
    # 5. Teacher collision check.
    # ------------------------------------------------------------
    for (teacher, day, period), classes in teacher_busy.items():
        if len(classes) > 1:
            report["violations"].append(
                {
                    "type": "oracle_teacher_conflict",
                    "teacher": teacher,
                    "day": day,
                    "period": period,
                    "classes": sorted(classes),
                }
            )

    # ------------------------------------------------------------
    # 6. Fixed-slot obligations.
    # ------------------------------------------------------------
    for class_id, subject, day, period in fixed_requirements:
        cell = timetable_cells.get((class_id, day, period))

        if not cell or cell.get("subject") != subject:
            report["violations"].append(
                {
                    "type": "oracle_fixed_slot",
                    "class": class_id,
                    "subject": subject,
                    "day": day,
                    "period": period,
                }
            )

    # ------------------------------------------------------------
    # 7. Explicit coverage instead of false PASS.
    # ------------------------------------------------------------
    for item in unsupported_semantics:
        report["unverified"].append(
            {
                "type": "unsupported_semantics",
                "description": str(item),
            }
        )

    report["coverage"] = {
        name: "CHECKED"
        for name in sorted(SUPPORTED_CHECKS)
    }

    report["coverage"]["all_hard_constraints"] = (
        "UNVERIFIED"
        if report["unverified"]
        else "CHECKED_SUPPORTED_SCOPE"
    )

    report["full_semantic_coverage"] = not report["unverified"]

    # A detected violation is FAIL.
    # No violation but incomplete coverage is INCOMPLETE, not PASS.
    # PASS is reserved for the scope this validator can actually justify.
    if report["violations"]:
        report["status"] = "FAIL"
    elif report["unverified"]:
        report["status"] = "INCOMPLETE"
    else:
        report["status"] = "PASS"

    report["metrics"] = {
        "source_classes": len(known_classes),
        "expected_course_periods": sum(expected_counts.values()),
        "actual_course_periods": sum(actual_counts.values()),
        "violation_count": len(report["violations"]),
        "unverified_count": len(report["unverified"]),
    }

    return report


def demo():
    """Small synthetic example containing one deliberate teacher collision."""

    source_courses = [
        {
            "class": "CLASS_A",
            "subject": "MATH",
            "count": 1,
            "teachers": {"TEACHER_01"},
        },
        {
            "class": "CLASS_B",
            "subject": "MATH",
            "count": 1,
            "teachers": {"TEACHER_01"},
        },
    ]

    timetable = {
        ("CLASS_A", 1, 1): {
            "subject": "MATH",
            "teachers": {"TEACHER_01"},
        },
        ("CLASS_B", 1, 1): {
            "subject": "MATH",
            "teachers": {"TEACHER_01"},
        },
    }

    report = validate_schedule(
        source_courses,
        timetable,
        unsupported_semantics=[
            "alternating-week rules are outside this public sample"
        ],
    )

    print(report)


if __name__ == "__main__":
    demo()
