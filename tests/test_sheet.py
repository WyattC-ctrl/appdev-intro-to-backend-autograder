"""Scoring and the layout of the .txt sheet."""
import re
import unittest

from fixture_apps import ALL_CHALLENGE, PA2_APP, pa1_app
from fixture_test_files import BONUS_TEST_FILE, TWENTY_FIVE_FAILING
from helpers import PA1, PA2, GraderTestCase, submission


class SheetTests(GraderTestCase):
    def test_full_layout_with_fixed_deductions(self):
        self.student_zip("a", submission(pa1_app(), postman=False, extra={"venv/pyvenv.cfg": "x"}))
        out = self.grade()
        self.assertRegex(out, r"(?m)^a: score ")
        self.assertIn(str(self.out), out)
        sheet = self.sheet("a")
        self.assertEqual(sheet.split("\n\nStyle feedback")[0] + "\n", (
            "Total:         10\nDeductions:   -2\nExtra Credit: 0\nScore:         8\n\n"
            "Points lost:\n"
            "-1  Included files that should not be submitted (venv, .db, __pycache__, or the test file)\n"
            "-1  No exported Postman collection (.json)\n\n"
            "Core tests: all 10 passed\n\n"
            "Challenges (extra credit): +0, no challenge points received\n"
            "Tier 1: +0, not earned (0 of 3 tests passed)\n"
            "Tier 2: +0, not earned (0 of 3 tests passed)\n"
        ))
        self.assertIn("\n\nStyle feedback (no points lost):\n- app.py: add a comment or docstring to", sheet)

    def test_three_failing_core_tests(self):
        self.student_zip("f", submission(pa1_app(broken={"get_posts", "edit"})))
        self.grade()
        sheet = self.sheet("f")
        self.assert_header(sheet, "-1.5", "0", "8.5")
        self.assertIn("-1.5  3 core tests failed, -0.5 each (listed below)", sheet)
        self.assertIn("Core tests failed (3 of 10, -0.5 each):\n- test_", sheet)
        self.assertEqual(len(re.findall(r"(?m)^- test_", sheet)), 3)

    def test_test_deduction_is_capped_and_score_stops_at_zero(self):
        self.student_zip("l", submission(pa1_app()))
        self.grade(test=self.write_test_file("many_test.py", TWENTY_FIVE_FAILING))
        sheet = self.sheet("l")
        self.assert_header(sheet, "-10", "0", "0")
        self.assertIn("-10  25 core tests failed, -0.5 each (listed below)", sheet)

    def test_both_tiers_earned(self):
        self.student_zip("g", submission(pa1_app(challenge=ALL_CHALLENGE)))
        self.grade()
        sheet = self.sheet("g")
        self.assert_header(sheet, "0", "+2", "12")
        self.assertIn("Core tests: all 10 passed", sheet)
        self.assertIn(
            "Challenges (extra credit): +2 received\n"
            "Tier 1: +1, earned (3 of 3 tests passed)\n"
            "Tier 2: +1, earned (3 of 3 tests passed)\n",
            sheet,
        )
        self.assertNotIn("not earned", sheet)

    def test_one_tier_earned_lists_what_failed_in_the_other(self):
        self.student_zip("i", submission(pa1_app(challenge={"tier1", "upvote"})))
        self.grade()
        sheet = self.sheet("i")
        self.assert_header(sheet, "0", "+1", "11")
        self.assertIn(
            "Challenges (extra credit): +1 received\n"
            "Tier 1: +1, earned (3 of 3 tests passed)\n"
            "Tier 2: +0, not earned (2 of 3 tests passed). Failed:\n- test_extra_sorting_posts: ",
            sheet,
        )

    def test_no_extra_option(self):
        self.student_zip("h", submission(pa1_app(challenge=ALL_CHALLENGE)))
        self.grade("--no-extra")
        sheet = self.sheet("h")
        self.assert_header(sheet, "0", "0", "10")
        self.assertIn("Challenges (extra credit): not checked for this run\n", sheet)
        self.assertNotIn("Tier 1", sheet)

    def test_no_tiers_in_test_file(self):
        self.student_zip("j", submission(pa1_app(challenge=ALL_CHALLENGE)))
        source, count = re.subn(r"(?m)^TIERS = .*\n", "", PA1.read_text())
        self.assertEqual(count, 1)
        out = self.grade(test=self.write_test_file("pa1_test.py", source))
        self.assertEqual(out.count("Warning:"), 1)
        sheet = self.sheet("j")
        self.assert_header(sheet, "0", "0", "10")
        self.assertIn("Challenges (extra credit): not graded, because the test file defines no tiers", sheet)

    def test_empty_tiers_give_no_credit_when_extra_tests_would_pass(self):
        self.student_zip("m", submission(PA2_APP))
        source, count = re.subn(r"(?m)^TIERS = .*\n", "TIERS = {}\n", PA2.read_text())
        self.assertEqual(count, 1)
        self.grade(test=self.write_test_file("pa2_test.py", source))
        sheet = self.sheet("m")
        self.assert_header(sheet, "0", "0", "10")
        self.assertIn("Core tests: all 8 passed", sheet)
        self.assertIn("Challenges (extra credit): not graded, because the test file defines no tiers", sheet)

    def test_tier_bonus(self):
        apps = {"both": "A B", "only1": "A", "only2": "B", "none": ""}
        for name, flags in apps.items():
            settings = "".join(f"app.config['{flag}'] = True\n" for flag in flags.split())
            self.student_zip(name, submission("from flask import Flask\napp = Flask(__name__)\n" + settings))
        self.grade(test=self.write_test_file("bonus_test.py", BONUS_TEST_FILE))
        both = self.sheet("both")
        self.assert_header(both, "0", "+3", "13")
        self.assertIn(
            "Challenges (extra credit): +3 received\n"
            "Tier 1: +1, earned (1 of 1 test passed)\n"
            "Tier 2: +1, earned (1 of 1 test passed)\n"
            "Bonus: +1, earned for completing tiers 1 and 2\n",
            both,
        )
        self.assert_header(self.sheet("only1"), "0", "+1", "11")
        only2 = self.sheet("only2")
        self.assert_header(only2, "0", "+1", "11")
        self.assertIn("Bonus: +0, not earned (worth +1 when tiers 1 and 2 are all earned)", only2)
        self.assert_header(self.sheet("none"), "0", "0", "10")


if __name__ == "__main__":
    unittest.main()
