"""Work out a submission's deductions, extra credit, and score."""
from dataclasses import dataclass, field

from grader.output.formatting import number

MAX_SCORE = 10
TEST_DEDUCTION = 0.5
README_BLANK_DEDUCTION = 0.5
MAX_TEST_DEDUCTION = 10


@dataclass
class ScoreResult:
    tests_ran: bool
    reasons: dict
    failing_core: list
    lost: list  # (deduction, label, reason or None)
    challenges: list = field(default_factory=list)  # Tier and Bonus rows, in tier order
    extra_credit: float = 0
    rubric: list = field(default_factory=list)  # (section, [(points earned, points, label)])
    extra_blocked: str = None  # why extra credit was not given, for rubric test files

    @property
    def deductions(self):
        return sum(lost[0] for lost in self.lost)

    @property
    def score(self):
        return max(MAX_SCORE - self.deductions + self.extra_credit, 0)


def file_points_lost(submission):
    """Return the (deduction, label, reason) entries for what the zip contains."""
    lost = []
    if submission.app_dir is None:
        lost.append((10, "No app.py was found, so nothing could be graded", None))
    if submission.has_venv_db_pycache or submission.has_test_file:
        lost.append((1, "Included files that should not be submitted (venv, .db, __pycache__, or the test file)", None))
    if not submission.has_readme:
        lost.append((1, "No README file", None))
    elif submission.readme_blanks:
        count = len(submission.readme_blanks)
        lost.append((
            count * README_BLANK_DEDUCTION,
            f"README has {count} blank answer{'s' if count != 1 else ''}",
            "Blank: " + ", ".join(submission.readme_blanks),
        ))
    if submission.has_postman_folder:
        lost.append((1, "Included a Postman folder; submit only the exported .json collection", None))
    elif not submission.has_postman:
        lost.append((1, "No exported Postman collection (.json)", None))
    return lost


def points_lost(submission, failing_core, tests_ran):
    """Return the (deduction, label, reason) entries for this submission."""
    lost = file_points_lost(submission)
    if submission.app_dir is not None and failing_core:
        count = len(failing_core)
        deduction = min(count * TEST_DEDUCTION, MAX_TEST_DEDUCTION)
        each = f"-{number(TEST_DEDUCTION)} each"
        if tests_ran:
            label = f"{count} core test{'s' if count != 1 else ''} failed, {each} (listed below)"
        else:
            label = f"All {count} core tests counted as failed because the tests could not run, {each} (see Notes)"
        lost.append((deduction, label, None))
    return lost


def grade_rubric(info, submission, passed, result):
    """Score each rubric item by its own points instead of a deduction per failed test."""
    for section, items in info.rubric:
        rows = []
        for name, points, label, lost_label in items:
            earned = points if name in passed else 0
            rows.append((earned, points, label))
            if not earned and submission.app_dir is not None:
                result.lost.append((points, lost_label, result.reasons.get(name)))
        result.rubric.append((section, rows))


@dataclass
class Tier:
    tier: int
    points: float  # what the student received: 1 or 0
    tests: list
    failing: list


@dataclass
class Bonus:
    tier: int  # the bonus needs every tier up to this one
    points: float  # what the student received
    value: float  # what it is worth


def grade_tiers(info, passed, result):
    """Add each tier's outcome to the result. A bonus needs every tier up to it earned."""
    all_earned = True
    for tier in sorted(info.tiers):
        names = info.tiers[tier]
        failing = [name for name in names if name not in passed]
        all_earned = all_earned and not failing
        result.challenges.append(Tier(tier, 0 if failing else 1, names, failing))
        result.extra_credit += 0 if failing else 1
        bonus = info.bonuses.get(tier)
        if bonus:
            result.challenges.append(Bonus(tier, bonus if all_earned else 0, bonus))
            result.extra_credit += bonus if all_earned else 0


def score_submission(info, submission, run, extra_mode):
    """Return the ScoreResult for one submission."""
    tests_ran = bool(run) and run["status"] == "ok"
    tests = run["tests"] if tests_ran else {}
    passed = {name for name, outcome in tests.items() if outcome == "pass"}
    failing_core = [name for name in info.core if name not in passed]
    reasons = run.get("reasons", {}) if tests_ran else {}
    if info.rubric:
        result = ScoreResult(tests_ran, reasons, failing_core, file_points_lost(submission))
        grade_rubric(info, submission, passed, result)
        needed = info.extra_needs
        if extra_mode and needed and needed[0] not in passed:
            result.extra_blocked = f"not given because {needed[1]}"
            return result
    else:
        result = ScoreResult(tests_ran, reasons, failing_core, points_lost(submission, failing_core, tests_ran))
    if extra_mode and tests_ran:
        grade_tiers(info, passed, result)
    return result
