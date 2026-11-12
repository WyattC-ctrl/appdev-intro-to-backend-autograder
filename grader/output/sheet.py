"""Write a student's grade sheet from their score."""
from grader.grading.scoring import MAX_SCORE, TEST_DEDUCTION, Bonus
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
    amounts = [f"-{number(amount)}" for amount, _, _ in result.lost]
    width = max(len(amount) for amount in amounts) + 2
    lines = ["Points lost:"]
    previous = None
    for amount, (_, label, reason) in zip(amounts, result.lost):
        lines.append(f"{amount:<{width}}{label}")
        if reason:
            lines.append(" " * width + ("Same reason as above." if reason == previous else reason))
        previous = reason
    return lines


def failed_line(name, reasons):
    return f"- {name}: {reasons[name]}" if reasons.get(name) else f"- {name}"


def tests_word(count):
    return "test" if count == 1 else "tests"


def core_test_lines(info, result):
    if not result.failing_core:
        return [f"Core tests: all {len(info.core)} passed"]
    return [
        f"Core tests failed ({len(result.failing_core)} of {len(info.core)}, "
        f"-{number(TEST_DEDUCTION)} each):",
        *[failed_line(name, result.reasons) for name in result.failing_core],
    ]


def rubric_lines(result):
    lines = ["Rubric (points earned):"]
    for section, rows in result.rubric:
        earned = sum(row[0] for row in rows)
        total = sum(row[1] for row in rows)
        lines.append(f"{section} {number(earned)}/{number(total)}")
        for got, points, label in rows:
            suffix = "" if got else f" (worth {number(points)})"
            lines.append(f"  +{number(got)}  {label}{suffix}")
    return lines


def tier_names(last):
    tiers = [str(tier) for tier in range(1, last + 1)]
    return tiers[0] if len(tiers) == 1 else ", ".join(tiers[:-1]) + " and " + tiers[-1]


def challenge_row_lines(row, reasons):
    if isinstance(row, Bonus):
        if row.points:
            return [f"Bonus: +{number(row.points)}, earned for completing tiers {tier_names(row.tier)}"]
        return [f"Bonus: +0, not earned (worth +{number(row.value)} when tiers {tier_names(row.tier)} are all earned)"]
    total = len(row.tests)
    passed = total - len(row.failing)
    if row.points:
        return [f"Tier {row.tier}: +1, earned ({passed} of {total} {tests_word(total)} passed)"]
    summary = f"Tier {row.tier}: +0, not earned ({passed} of {total} {tests_word(total)} passed)"
    # A tier with no passes was usually not attempted, so skip the full list.
    if not passed:
        return [summary]
    return [f"{summary}. Failed:", *[failed_line(name, reasons) for name in row.failing]]


def challenge_lines(info, submission, extra_mode, result):
    """Say plainly whether any challenge points were received, and why or why not."""
    title = "Challenges (extra credit)"
    if info.no_challenges:
        return [f"{title}: none for this assignment"]
    if not info.tiers:
        return [f"{title}: not graded, because the test file defines no tiers"]
    if not extra_mode:
        return [f"{title}: not checked for this run"]
    if submission.app_dir is None:
        return [f"{title}: +0, not checked because no app.py was found"]
    if result.extra_blocked:
        return [f"{title}: +0, {result.extra_blocked}"]
    if not result.tests_ran:
        return [f"{title}: +0, not checked because the tests could not run (see Notes)"]
    if result.extra_credit:
        lines = [f"{title}: +{number(result.extra_credit)} received"]
    else:
        lines = [f"{title}: +0, no challenge points received"]
    for row in result.challenges:
        lines.extend(challenge_row_lines(row, result.reasons))
    return lines


def note_lines(submission, run):
    notes = list(submission.notes)
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
        rubric_lines(result) if info.rubric else core_test_lines(info, result) if result.tests_ran else [],
        challenge_lines(info, submission, extra_mode, result),
        note_lines(submission, run),
        style_lines(submission),
    ]
    return "\n\n".join("\n".join(section) for section in sections if section) + "\n"
