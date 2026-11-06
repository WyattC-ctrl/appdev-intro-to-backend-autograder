"""Command-line options, errors, and where results go."""
import fcntl
import os
import unittest

from fixture_apps import PA2_APP
from helpers import PA1, PA2, ROOT, GraderTestCase, submission


class CliTests(GraderTestCase):
    def test_missing_test_option(self):
        result = self.run_grade(self.students)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--test PATH is required", result.stderr)

    def test_missing_students_folder(self):
        result = self.run_grade(self.tmp / "nope", "--test", PA1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("students folder not found", result.stderr)

    def test_unusable_test_file(self):
        bad = self.write_test_file("bad_test.py", "class Other:\n    pass\n")
        result = self.run_grade("--list-tests", "--test", bad)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not define a TestRoutes class", result.stderr)
        broken = self.write_test_file("broken_test.py", "def (:\n")
        result = self.run_grade("--list-tests", "--test", broken)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not read test file", result.stderr)

    def test_test_file_name_works_from_any_folder(self):
        result = self.run_grade("--list-tests", "--test", "pa2_test.py", cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Core tests: 8", result.stdout)
        result = self.run_grade("--list-tests", "--test", "nope_test.py", cwd=self.tmp)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("test file not found", result.stderr)

    def test_output_folder_inside_students_is_refused(self):
        result = self.run_grade(self.students, "--test", PA1, "--out", self.students / "grades")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be inside the students folder", result.stderr)

    def test_grader_options_are_gone(self):
        result = self.run_grade(self.students, "--test", PA1, "--grader", "Sam")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_each_test_has_its_own_grades_folder(self):
        self.student_zip("stu", submission(PA2_APP))
        pa1_copy = self.write_test_file("pa1_test.py", PA1.read_text())
        self.grade(test=PA2)
        pa2_sheet = (self.out / "PA2" / "sheets" / "stu.txt").read_text()
        self.grade(test=pa1_copy)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["PA1", "PA2"])
        self.assertEqual((self.out / "PA2" / "sheets" / "stu.txt").read_text(), pa2_sheet)
        self.assertNotEqual((self.out / "PA1" / "sheets" / "stu.txt").read_text(), pa2_sheet)
        self.assertTrue((self.out / "PA1" / "CS_1998_S603_PA1_scores.csv").is_file())
        self.assertTrue((self.out / "PA2" / "CS_1998_S603_PA2_scores.csv").is_file())
        # Rerunning the same test replaces that test's sheet.
        (self.out / "PA2" / "sheets" / "stu.txt").write_text("old")
        self.grade(test=PA2)
        self.assertEqual((self.out / "PA2" / "sheets" / "stu.txt").read_text(), pa2_sheet)

    def test_only_one_run_at_a_time(self):
        (self.students / "stu").mkdir()
        handle = os.open(ROOT, os.O_RDONLY)
        self.addCleanup(os.close, handle)
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = self.run_grade(self.students, "--test", PA1, "--out", self.out)
        # --list-tests needs no port, so it is not blocked.
        listing = self.run_grade("--list-tests", "--test", PA1)
        fcntl.flock(handle, fcntl.LOCK_UN)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("another grading run is in progress", result.stderr)
        self.assertFalse(self.out.exists())
        self.assertEqual(listing.returncode, 0)


if __name__ == "__main__":
    unittest.main()
