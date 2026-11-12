"""Regrading one student without touching anyone else's results."""
import os
import socket
import unittest
import zipfile

from fixture_apps import ALL_CHALLENGE, pa1_app
from helpers import PA1, GraderTestCase, submission, write_zip

CSV = "CS_1998_S603_PA1_scores.csv"
FEEDBACK = "CS_1998_S603_PA1_feedback.zip"


class RegradeTests(GraderTestCase):
    def setUp(self):
        super().setUp()
        self.student_zip("abc123", submission(pa1_app(broken={"get_posts"})))
        self.student_zip("def456", submission(pa1_app()))
        (self.students / "ghi789").mkdir()
        self.grade()
        self.results = self.out / "PA1"
        self.new_zip = self.tmp / "resubmitted.zip"
        write_zip(self.new_zip, submission(pa1_app(challenge=ALL_CHALLENGE)))

    def regrade(self, student="abc123", zip_path=None):
        return self.run_grade(
            zip_path or self.new_zip, "--test", PA1, "--student", student, "--out", self.out,
            env=dict(os.environ, TMPDIR=str(self.child_tmp)),
        )

    def snapshot(self):
        """Every file in the results folder, plus each entry inside the feedback zip."""
        files = {p: p.read_bytes() for p in self.results.rglob("*") if p.is_file()}
        with zipfile.ZipFile(self.results / FEEDBACK) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        return files, entries

    def test_changes_only_that_student(self):
        # An edit made by hand to someone else's row must survive.
        csv_path = self.results / CSV
        csv_path.write_text(csv_path.read_text().replace("def456,10.0,10.0,,", "def456,7.0,7.0,1,Late"))
        before_files, before_entries = self.snapshot()

        result = self.regrade()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"abc123: score [\d.]+ -> 12 \(ok\)")
        after_files, after_entries = self.snapshot()

        sheet = self.results / "sheets" / "abc123.txt"
        self.assert_header(after_files[sheet].decode(), "0", "+2", "12")
        for path, content in before_files.items():
            if path.name not in ("abc123.txt", CSV, FEEDBACK):
                self.assertEqual(after_files[path], content, path)

        self.assertEqual(csv_path.read_text(), (
            "NetID,PA1 - Reddit,Total,Adjustments,Add Comments\n"
            "abc123,12.0,12.0,,\n"
            "def456,7.0,7.0,1,Late\n"
            "ghi789,0.0,0.0,,No submission\n"
        ))

        self.assertEqual(sorted(after_entries), sorted(before_entries))
        name = "feedback_template/abc123/PA1_feedback.txt"
        self.assertEqual(after_entries[name], after_files[sheet])
        self.assertNotEqual(after_entries[name], before_entries[name])
        for other, content in before_entries.items():
            if other != name:
                self.assertEqual(after_entries[other], content, other)
        self.assertEqual(sorted(p.name for p in self.results.iterdir()), sorted([CSV, FEEDBACK, "sheets"]))
        self.assertEqual(list(self.child_tmp.iterdir()), [])
        self.assert_port_free()

    def test_no_submission_comment_is_cleared(self):
        self.assertEqual(self.regrade("ghi789").returncode, 0)
        self.assertIn("ghi789,12.0,12.0,,\n", (self.results / CSV).read_text())

    def assert_refused(self, result, message, before):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_unknown_netid_changes_nothing(self):
        before = self.snapshot()
        self.assert_refused(self.regrade("nobody1"), "not in the scores file", before)

    def test_unsafe_netid_changes_nothing(self):
        before = self.snapshot()
        self.assert_refused(self.regrade("../abc123"), "not a valid NetID", before)

    def test_invalid_zip_changes_nothing(self):
        bad = self.tmp / "bad.zip"
        bad.write_bytes(b"not a zip")
        before = self.snapshot()
        self.assert_refused(self.regrade(zip_path=bad), "not a valid zip", before)

    def test_port_busy_changes_nothing(self):
        before = self.snapshot()
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("0.0.0.0", 5000))
            listener.listen()
            result = self.regrade()
        self.assert_refused(result, "Port 5000 is busy", before)

    def test_needs_the_whole_folder_graded_first(self):
        result = self.run_grade(self.new_zip, "--test", PA1, "--student", "abc123", "--out", self.tmp / "empty")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Grade the whole folder", result.stderr)

    def test_zip_without_student_option_is_refused(self):
        result = self.run_grade(self.new_zip, "--test", PA1, "--out", self.out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("add --student NETID", result.stderr)

    def test_folder_with_student_option_is_refused(self):
        result = self.regrade(zip_path=self.students)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("needs the student's zip file", result.stderr)


if __name__ == "__main__":
    unittest.main()
