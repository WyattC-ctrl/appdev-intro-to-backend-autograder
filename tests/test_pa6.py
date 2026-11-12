"""PA6, which calls each student's deployed server instead of running app.py."""
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import ASSIGNMENT_TESTS, POSTMAN, GraderTestCase, filled_readme

PA6 = ASSIGNMENT_TESTS / "pa6_test.py"
ENV_APP = 'import os\nfrom flask import Flask\n\napp = Flask(__name__)\n\n\n@app.route("/")\ndef base():\n    return f"{os.environ.get(\'NETID\')} was here!"\n'


def load_pa6():
    spec = importlib.util.spec_from_file_location("pa6_checks", PA6)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Pa6CheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pa6 = load_pa6()

    def with_readme(self, text):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "src").mkdir()
        (root / "README.txt").write_text(text)
        previous = os.getcwd()
        os.chdir(root / "src")
        self.addCleanup(os.chdir, previous)

    def test_server_address_line(self):
        for written, url in (
            ("34.86.1.2", "http://34.86.1.2"),
            ("34.86.1.2:8000", "http://34.86.1.2:8000"),
            ("http://34.86.1.2/", "http://34.86.1.2"),
            ("https://pa6.example.org/api/courses/", "https://pa6.example.org"),
        ):
            self.with_readme(f"Working Endpoint: GET /api/courses/\nYour Server Address: {written}\n")
            self.assertEqual(self.pa6.server_url(), url, written)

    def test_address_elsewhere_in_readme(self):
        self.with_readme("Your Server Address:\nDocker Hub: https://hub.docker.com/r/abc/pa6\nI deployed to 35.1.2.3:80\n")
        self.assertEqual(self.pa6.server_url(), "http://35.1.2.3:80")

    def test_no_address(self):
        self.with_readme("Your Server Address: <fill this in>\nhttp://localhost:5000/\n")
        self.assertIsNone(self.pa6.server_url())


class Pa6CommandTests(GraderTestCase):
    def test_list_tests(self):
        listing = self.list_tests(PA6)
        self.assertIn("Core tests: 6", listing)
        self.assertIn("Deployed server (7 points)", listing)
        self.assertIn("Warnings: 0", listing)

    def test_no_server_address(self):
        self.student_zip("abc123", {
            "pa6/src/app.py": ENV_APP, "pa6/src/.env": "NETID=abc123\n", "pa6/src/Dockerfile": "",
            "pa6/src/docker-compose.yml": "", "pa6/src/.dockerignore": "", "pa6/README.txt": filled_readme(load_pa6(), {"Your Server Address": ""}),
            "pa6/postman_collection.json": POSTMAN,
        })
        self.grade(test=PA6)
        sheet = self.sheet("abc123")
        self.assert_header(sheet, "-7.5", "0", "2.5")
        self.assertIn(
            "-0.5  README has 1 blank answer\n"
            "      Blank: Your Server Address\n"
            "-3    The server address in the README could not be reached\n"
            "      The README has no server address. Fill in \"Your Server Address:\".\n"
            "-2    GET / does not return \"<netid> was here!\"\n"
            "      Same reason as above.\n",
            sheet,
        )
        self.assertIn("Environment variables 2/2\n", sheet)
        self.assertIn("Challenges (extra credit): none for this assignment", sheet)
