"""The feedback zip uploaded to CMS."""
import sys
import unittest
import zipfile
from pathlib import Path

from fixture_apps import pa1_app
from helpers import ROOT, GraderTestCase, submission

sys.path.insert(0, str(ROOT))

from grader.output.feedback_zip import write_feedback_zip  # noqa: E402


class FeedbackZipTests(GraderTestCase):
    def read_zip(self, assignment="PA1"):
        path = self.out / assignment / f"CS_1998_S603_{assignment}_feedback.zip"
        return zipfile.ZipFile(path)

    def test_one_feedback_file_per_student(self):
        self.student_zip("abc123", submission(pa1_app()))
        (self.students / "def456").mkdir()
        self.grade()
        archive = self.read_zip()
        self.assertEqual(sorted(archive.namelist()), [
            "feedback_template/abc123/PA1_feedback.txt",
            "feedback_template/def456/PA1_feedback.txt",
        ])
        for student in ("abc123", "def456"):
            text = archive.read(f"feedback_template/{student}/PA1_feedback.txt").decode()
            self.assertEqual(text, self.sheet(student))

    def test_rerun_replaces_the_zip(self):
        (self.students / "abc123").mkdir()
        self.grade()
        (self.students / "abc123").rmdir()
        (self.students / "def456").mkdir()
        self.grade()
        self.assertEqual(self.read_zip().namelist(), ["feedback_template/def456/PA1_feedback.txt"])

    def test_student_without_a_sheet_gets_an_empty_folder(self):
        (self.tmp / "sheets").mkdir()
        (self.tmp / "sheets" / "abc123.txt").write_text("sheet")
        path = write_feedback_zip(self.tmp, Path("pa2_test.py"), ["abc123", "def456"])
        self.assertEqual(path.name, "CS_1998_S603_PA2_feedback.zip")
        self.assertEqual(zipfile.ZipFile(path).namelist(), [
            "feedback_template/abc123/PA2_feedback.txt",
            "feedback_template/def456/",
        ])


if __name__ == "__main__":
    unittest.main()
