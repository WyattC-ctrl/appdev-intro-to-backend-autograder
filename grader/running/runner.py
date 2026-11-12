"""Start a student's test process and collect its results."""
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from grader.paths import PROJECT_ROOT
from grader.running.docker import Containers
from grader.running.run_one import PORT_BUSY_HINT, port_is_busy

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


def run_student_tests(app_dir, test_path, results_path, mode, docker=False, remote=False, netid=""):
    """Run one student's tests. The test file reads the student's NetID from GRADER_NETID."""
    extra_env = {"GRADER_NETID": netid}
    if docker:
        return run_in_docker(app_dir, test_path, results_path, mode, extra_env)
    if remote:
        # The student's server is already deployed, so the tests call it directly.
        return run_test_process(app_dir, test_path, results_path, mode, external=True, extra_env=extra_env)
    return run_test_process(app_dir, test_path, results_path, mode, extra_env=extra_env)


def run_in_docker(app_dir, test_path, results_path, mode, extra_env):
    """Start the student's containers, run the tests against them, then remove them.

    A problem starting the containers does not stop the tests: the file checks
    still run, and the test that calls the app reports the problem.
    """
    containers = Containers(app_dir)
    try:
        port, problem = containers.port()
        if port is not None and port_is_busy(port):
            return {"status": "port_busy", "error": PORT_BUSY_HINT.replace("5000", str(port)), "tests": {}}
        if problem is None:
            try:
                problem = containers.start(port)
            except (OSError, subprocess.SubprocessError) as error:
                problem = f"Docker could not start the containers: {error}"
        extra_env = dict(extra_env, GRADER_URL=f"http://localhost:{port or 5000}", GRADER_DOCKER_ERROR=problem or "")
        return run_test_process(app_dir, test_path, results_path, mode, external=True, extra_env=extra_env)
    finally:
        containers.stop()


def run_test_process(app_dir, test_path, results_path, mode, external=False, extra_env=None):
    env = dict(os.environ, NO_PROXY="localhost,127.0.0.1", no_proxy="localhost,127.0.0.1", **(extra_env or {}))
    command = [venv_python(), "-I", str(RUN_ONE), str(app_dir), str(test_path), str(results_path), mode]
    if external:
        command.append("external")
    process = subprocess.Popen(
        command,
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
