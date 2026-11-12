"""Shared tools for the grader's tests.

Each test builds a temporary students folder, runs grade.py as a real command,
and checks the output. Port 5000 must be free.
"""
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRADE = ROOT / "grade.py"
ASSIGNMENT_TESTS = ROOT / "assignment_tests"
PA1 = ASSIGNMENT_TESTS / "pa1_test.py"
PA2 = ASSIGNMENT_TESTS / "pa2_test.py"
POSTMAN = json.dumps({"info": {"_postman_id": "abc", "name": "x"}, "item": []})


def write_zip(path, files):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def submission(app, readme=True, postman=True, extra=None):
    """The files of a zip with app.py and, by default, a README and Postman collection."""
    files = {"proj/app.py": app}
    if readme:
        files["proj/README.md"] = "readme"
    if postman:
        files["proj/postman_collection.json"] = POSTMAN
    files.update(extra or {})
    return files


def tree_digest(root):
    digest = hashlib.sha256()
    for dirpath, _, filenames in sorted(os.walk(root)):
        digest.update(dirpath.encode())
        for name in sorted(filenames):
            digest.update(name.encode() + (Path(dirpath) / name).read_bytes())
    return digest.hexdigest()


class GraderTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="grade_tool_test_")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.students = self.tmp / "students"
        self.students.mkdir()
        self.out = self.tmp / "out"
        # Temp folders made by grade.py land here so that cleanup can be checked.
        self.child_tmp = self.tmp / "child_tmp"
        self.child_tmp.mkdir()

    def student_zip(self, name, files):
        write_zip(self.students / name / "sub.zip", files)

    def run_grade(self, *args, **kwargs):
        """Run grade.py with these arguments and return the finished process."""
        return subprocess.run(
            [sys.executable, str(GRADE), *map(str, args)], capture_output=True, text=True, **kwargs
        )

    def grade(self, *args, test=PA1):
        """Grade the students folder, check nothing was left behind, and return stdout."""
        before = tree_digest(self.students)
        result = self.run_grade(
            self.students, "--test", test, "--out", self.out, *args,
            env=dict(os.environ, TMPDIR=str(self.child_tmp)), timeout=300,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, tree_digest(self.students), "students folder changed")
        self.assertEqual(list(self.child_tmp.iterdir()), [], "temp folder left behind")
        self.assert_port_free()
        return result.stdout

    def list_tests(self, test):
        result = self.run_grade("--list-tests", "--test", test)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def assert_port_free(self):
        with socket.socket() as sock:
            self.assertNotEqual(sock.connect_ex(("127.0.0.1", 5000)), 0, "server left running")

    def sheet(self, name):
        # Each run writes to a subfolder named for its test file.
        return next(self.out.glob(f"*/sheets/{name}.txt")).read_text()

    def write_test_file(self, name, source):
        path = self.tmp / name
        path.write_text(source)
        return path

    def assert_header(self, sheet, deductions, extra, score):
        self.assertIn(f"Deductions:   {deductions}\n", sheet)
        self.assertIn(f"\nExtra Credit: {extra}\n", sheet)
        self.assertIn(f"\nScore:         {score}\n", sheet)


def filled_readme(test_module, values):
    """A README that fills in every field and question the test file checks."""
    lines = [f"{field}: {values.get(field, 'answer')}" for field in test_module.README_FIELDS]
    lines.append("Questions:")
    for question in test_module.README_QUESTIONS:
        lines += [question, "An answer.", ""]
    return "\n".join(lines)
