"""Reading tests, tiers, and warnings from a test file."""
import subprocess
import sys
import unittest

from helpers import ASSIGNMENT_TESTS, GRADE, PA1, GraderTestCase


class TestFileInfoTests(GraderTestCase):
    def test_assignment_test_counts(self):
        expected = {"pa1": (10, 6, 2), "pa2": (8, 5, 1), "pa3": (15, 3, 2), "pa4": (16, 14, 2)}
        for name, (core, extra, tiers) in expected.items():
            out = self.list_tests(ASSIGNMENT_TESTS / f"{name}_test.py")
            self.assertIn(f"Core tests: {core}\n", out, name)
            self.assertIn(f"Extra-credit tests: {extra}\n", out, name)
            self.assertIn(f"Tiers: {tiers}\n", out, name)
            self.assertIn("Warnings: 0\n", out, name)

    def test_works_without_flask_or_requests(self):
        # -S leaves out site-packages, like a system python with nothing installed.
        for name, core in (("pa1", 10), ("pa2", 8), ("pa3", 15), ("pa4", 16)):
            result = subprocess.run(
                [sys.executable, "-S", str(GRADE), "--list-tests", "--test", str(ASSIGNMENT_TESTS / f"{name}_test.py")],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Core tests: {core}\n", result.stdout, name)

    def test_misnamed_extra_function_warns(self):
        test_file = self.write_test_file("pa1_test.py", PA1.read_text() + "\n\ndef text_extra_x():\n    pass\n")
        out = self.list_tests(test_file)
        self.assertIn('"text_extra_x"', out)
        self.assertIn("Warnings: 1\n", out)

    def test_extra_test_missing_from_tiers_warns(self):
        source = PA1.read_text().replace('"test_extra_upvote_post", ', "")
        out = self.list_tests(self.write_test_file("pa1_test.py", source))
        self.assertIn('"test_extra_upvote_post" is not listed in any tier', out)


if __name__ == "__main__":
    unittest.main()
