"""Work out a submission's deductions, extra credit, and score."""
from dataclasses import dataclass, field

from grader.output.formatting import number

MAX_SCORE = 10
TEST_DEDUCTION = 0.5
MAX_TEST_DEDUCTION = 10


@dataclass
class ScoreResult:
    tests_ran: bool
    reasons: dict
    failing_core: list
    lost: list  # (deduction, label)
    earned: list = field(default_factory=list)  # lines for extra credit earned
    missed_tiers: list = field(default_factory=list)  # (tier, tests in tier, failing tests)
    extra_credit: float = 0

    @property
    def deductions(self):
        return sum(amount for amount, _ in self.lost)

    @property
    def score(self):
        return max(MAX_SCORE - self.deductions + self.extra_credit, 0)


def points_lost(submission, failing_core):
    """Return the (deduction, label) pairs for this submission."""
    lost = []
    if submission.app_dir is None:
        lost.append((10, "Cannot find source code"))
    if submission.has_venv_db_pycache:
        lost.append((1, "Zipped venv, .db, or pycache"))
    if not submission.has_readme:
        lost.append((1, "No README"))
    if not submission.has_postman:
        lost.append((1, "No exported Postman collection"))
    if submission.app_dir is not None and failing_core:
        deduction = min(len(failing_core) * TEST_DEDUCTION, MAX_TEST_DEDUCTION)
        lost.append((deduction, f"{len(failing_core)} tests fail"))
    return lost


def grade_tiers(info, passed, result):
    """Add each tier's outcome to the result. A bonus needs every lower tier earned."""
    all_lower_earned = True
    for tier in sorted(info.tiers):
        names = info.tiers[tier]
        failing = [name for name in names if name not in passed]
        if failing:
            all_lower_earned = False
            result.missed_tiers.append((tier, names, failing))
            continue
        result.earned.append(f"+1  Implemented tier {tier} challenge")
        result.extra_credit += 1
        bonus = info.bonuses.get(tier)
        if bonus and all_lower_earned:
            result.earned.append(f"+{number(bonus)}  Completed all tiers through tier {tier}")
            result.extra_credit += bonus


def score_submission(info, submission, run, extra_mode):
    """Return the ScoreResult for one submission."""
    tests_ran = bool(run) and run["status"] == "ok"
    tests = run["tests"] if tests_ran else {}
    passed = {name for name, outcome in tests.items() if outcome == "pass"}
    failing_core = [name for name in info.core if name not in passed]
    result = ScoreResult(
        tests_ran=tests_ran,
        reasons=run.get("reasons", {}) if tests_ran else {},
        failing_core=failing_core,
        lost=points_lost(submission, failing_core),
    )
    if extra_mode:
        grade_tiers(info, passed, result)
    return result
