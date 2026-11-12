"""Running a student's tests, and each way that can go wrong."""
import socket
import unittest

from fixture_apps import pa1_app
from fixture_test_files import REASON_TEST_FILE
from helpers import PA1, GraderTestCase, submission


class RunnerTests(GraderTestCase):
    def test_app_that_raises_on_import(self):
        self.student_zip("e", submission("raise RuntimeError('boom')"))
        self.grade()
        sheet = self.sheet("e")
        self.assert_header(sheet, "-5", "0", "5")
        self.assertIn("-5  All 10 core tests counted as failed because the tests could not run, -0.5 each (see Notes)", sheet)
        self.assertIn("Challenges (extra credit): +0, not checked because the tests could not run (see Notes)", sheet)
        self.assertNotIn("Core tests failed", sheet)
        self.assertNotIn("Core tests:", sheet)
        self.assertIn("could not run (import_error): RuntimeError: boom", sheet)

    def test_app_variable_is_not_a_flask_app(self):
        self.student_zip("noattr", submission("app = None"))
        self.grade("--no-extra")
        self.assertIn("could not run (runner_error)", self.sheet("noattr"))

    def test_runner_dies_without_results(self):
        self.student_zip("dead", submission("import os\nos._exit(3)\n"))
        self.grade()
        self.assertIn("could not run (runner_failed)", self.sheet("dead"))

    def test_port_busy_warns_and_does_not_stop_the_batch(self):
        self.student_zip("p", submission(pa1_app()))
        self.student_zip("q", submission(pa1_app()))
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("0.0.0.0", 5000))
            listener.listen()
            result = self.run_grade(self.students, "--test", PA1, "--out", self.out, check=True)
        self.assertIn("WARNING: port 5000 was busy for 2 students", result.stdout)
        for name in "pq":
            sheet = self.sheet(name)
            self.assertIn("could not run (port_busy)", sheet)
            self.assertIn("AirPlay", sheet)
            self.assert_header(sheet, "-5", "0", "5")

    def test_env_file_is_loaded_before_import(self):
        # Fails on import unless both values come from the student's .env.
        app = (
            "import os\n"
            "assert os.environ['SALT'] == 'abc def'\n"
            "assert int(os.environ['ROUNDS']) == 500\n"
        ) + pa1_app()
        env = "# secrets\nexport SALT='abc def'\n\nROUNDS=500\nnot a setting\n"
        self.student_zip("same", submission(app, extra={"proj/.env": env}))
        files = submission(app)
        files["proj/src/app.py"] = files.pop("proj/app.py")
        files["proj/.env"] = env
        self.student_zip("parent", files)
        self.student_zip("missing", submission(app))
        self.grade("--no-extra")
        self.assert_header(self.sheet("same"), "0", "0", "10")
        self.assert_header(self.sheet("parent"), "0", "0", "10")
        self.assertIn("could not run (import_error)", self.sheet("missing"))

    def test_failure_reasons_on_sheet(self):
        self.student_zip("stu", submission(pa1_app()))
        self.grade(test=self.write_test_file("reason_test.py", REASON_TEST_FILE))
        sheet = self.sheet("stu")
        self.assertIn("Core tests failed (5 of 6, -0.5 each):\n", sheet)
        self.assertIn("- test_a_status: GET request to route '/x/' returned a status code of 500, but 201 was expected.\n", sheet)
        self.assertIn("- test_b_no_message: 1 != 2\n", sheet)
        self.assertIn("- test_c_crash: KeyError: 'id'\n", sheet)
        self.assertIn("- test_d_hints: POST request to route '/y/' did not return a JSON response.\n", sheet)
        self.assertIn("- test_e_long: " + "z" * 200 + "...\n", sheet)
        self.assertNotIn("test_f_pass", sheet)
        self.assertNotIn("\x1b", sheet)
        self.assertNotIn("Are you sure", sheet)


if __name__ == "__main__":
    unittest.main()
