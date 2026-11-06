"""Start a student's test process and collect its results."""
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from grader.paths import PROJECT_ROOT

RUN_ONE = Path(__file__).resolve().parent / "run_one.py"
TEST_TIMEOUT_SECONDS = 120


def venv_python():
    """The running venv's python, or the project's venv when run from outside one."""
    if sys.prefix == sys.base_prefix:
        for name in (".venv", "venv"):
            candidate = PROJECT_ROOT / name / "bin" / "python"
            if candidate.exists():
                return str(candidate)
    return sys.executable


def run_student_tests(app_dir, test_path, results_path, mode):
    env = dict(os.environ, NO_PROXY="localhost,127.0.0.1", no_proxy="localhost,127.0.0.1")
    process = subprocess.Popen(
        [venv_python(), "-I", str(RUN_ONE), str(app_dir), str(test_path), str(results_path), mode],
        cwd=app_dir,  # relative paths in student code, such as a .db, stay in the temp folder
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    timed_out = False
    try:
        process.wait(timeout=TEST_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
    finally:
        # Also removes anything the student's code started.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        process.wait()

    if timed_out:
        return {
            "status": "timeout",
            "error": f"The tests did not finish within {TEST_TIMEOUT_SECONDS} seconds.",
            "tests": {},
        }
    try:
        with open(results_path) as results:
            return json.load(results)
    except (OSError, ValueError):
        return {
            "status": "runner_failed",
            "error": "The test runner ended without writing results.",
            "tests": {},
        }
