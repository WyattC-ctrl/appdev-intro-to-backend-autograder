"""Write a student's grade sheet from their score."""
from grader.grading.scoring import MAX_SCORE
from grader.output.formatting import number


def last_line(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[-1] if lines else "No details are available."


def header_lines(result):
    deductions = result.deductions
    extra_credit = result.extra_credit
    return [
        f"Total:         {MAX_SCORE}",
        f"Deductions:   {'-' + number(deductions) if deductions else '0'}",
        f"Extra Credit: {'+' + number(extra_credit) if extra_credit else '0'}",
        f"Score:         {number(result.score)}",
    ]


def points_lost_lines(result):
    if not result.lost:
        return ["Points lost: none"]
    return ["Points lost:", *[f"-{number(amount)}  {label}" for amount, label in result.lost]]


def failed_line(name, reasons):
    return f"- {name}: {reasons[name]}" if reasons.get(name) else f"- {name}"


def core_test_lines(info, result):
    if not result.failing_core:
        return [f"Core tests: all {len(info.core)} passed"]
    return [
        f"Core tests failed ({len(result.failing_core)} of {len(info.core)}):",
        *[failed_line(name, result.reasons) for name in result.failing_core],
    ]


def missed_tier_lines(result):
    lines = []
    for tier, names, failing in result.missed_tiers:
        passed = len(names) - len(failing)
        summary = f"Tier {tier} not earned ({passed} of {len(names)} tests passed)"
        # A tier with no passes is usually not attempted, so skip the full list.
        if passed:
            lines.append(f"{summary}. Failed:")
            lines.extend(failed_line(name, result.reasons) for name in failing)
        else:
            lines.append(f"{summary}.")
    return lines


def extra_credit_lines(result):
    missed = missed_tier_lines(result) if result.tests_ran else []
    if not result.earned and not missed:
        return []
    return ["Extra credit:", *result.earned, *missed]


def note_lines(info, submission, run, extra_mode):
    notes = list(submission.notes)
    if not extra_mode:
        notes.append("Extra credit was not checked for this run.")
    elif not info.tiers:
        notes.append("No tiers defined in the test file.")
    if run and run["status"] != "ok":
        notes.append(f"The tests could not run ({run['status']}): {last_line(run.get('error'))}")
    return ["Notes:", *[f"- {note}" for note in notes]] if notes else []


def style_lines(submission):
    if not submission.style:
        return []
    return ["Style feedback (no points lost):", *[f"- {line}" for line in submission.style]]


def build_sheet(info, submission, run, extra_mode, result):
    """Return the sheet text. Sections with nothing to say are left out."""
    sections = [
        header_lines(result),
        points_lost_lines(result),
        core_test_lines(info, result) if result.tests_ran else [],
        extra_credit_lines(result),
        note_lines(info, submission, run, extra_mode),
        style_lines(submission),
    ]
    return "\n\n".join("\n".join(section) for section in sections if section) + "\n"
