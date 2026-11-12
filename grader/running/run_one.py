"""Run one student's Flask app against a test file and write the results as JSON.

Usage: python -I run_one.py APP_DIR TEST_PATH RESULTS_JSON extra|core [external]

With "external", the app is already running somewhere else, in the student's
containers (PA5) or on their deployed server (PA6), so this only runs the tests.

Runs in its own process with -I, so it can only import the standard library, not
the rest of this package.
"""
import importlib.util
import inspect
import json
import os
import re
import socket
import sys
import threading
import time
import traceback
import unittest

# -I ignores PYTHONDONTWRITEBYTECODE, so stop __pycache__ being created here.
sys.dont_write_bytecode = True

PORT = 5000
SERVER_WAIT_SECONDS = 5
EXTRA_GUARD = "if not EXTRA_CREDIT:"
MAX_REASON_LENGTH = 200
PORT_BUSY_HINT = (
    f"Port {PORT} is already in use. On macOS this is often AirPlay Receiver: "
    "turn it off in System Settings > General > AirDrop & Handoff."
)


def is_extra_test(method):
    """A test is extra credit when its source contains the guard line."""
    source = inspect.getsource(method)
    return any(line.strip() == EXTRA_GUARD for line in source.splitlines())


def split_tests(test_class):
    """Return (core names, extra-credit names) for a TestCase class."""
    core, extra = [], []
    for name in unittest.TestLoader().getTestCaseNames(test_class):
        (extra if is_extra_test(getattr(test_class, name)) else core).append(name)
    return core, extra


def port_is_busy(port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            return True
    # A listener on one specific address can survive the wildcard bind above,
    # and the tests call "localhost", which may resolve to either address.
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                if sock.connect_ex((host, port)) == 0:
                    return True
        except OSError:
            pass
    return False


def wait_for_server():
    deadline = time.monotonic() + SERVER_WAIT_SECONDS
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                return True
        time.sleep(0.05)
    return False


def failure_reason(error_type, error):
    """Turn a test failure into one short line for the student's sheet."""
    text = str(error)
    if issubclass(error_type, AssertionError):
        # unittest writes "<comparison> : <the test's own message>".
        text = text.split(" : ", 1)[-1]
    else:
        text = f"{error_type.__name__}: {text}"
    text = " ".join(re.sub(r"\x1b\[\d+m", "", text).split())
    # The rest of this message is troubleshooting hints and the request body.
    match = re.match(r".*?did not return a \w+ response\.", text)
    if match:
        text = match.group()
    if len(text) > MAX_REASON_LENGTH:
        text = text[:MAX_REASON_LENGTH].rstrip() + "..."
    return text


class PassRecorder(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.passed = set()
        self.reasons = {}

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.add(test._testMethodName)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.reasons[test._testMethodName] = failure_reason(err[0], err[1])

    def addError(self, test, err):
        super().addError(test, err)
        name = getattr(test, "_testMethodName", None)
        if name:
            self.reasons[name] = failure_reason(err[0], err[1])


def run_tests(test_class, mode):
    core, extra = split_tests(test_class)
    # Core tests go first so that extra tests cannot change their results.
    names = core + extra if mode == "extra" else core
    recorder = PassRecorder()
    unittest.TestSuite(test_class(name) for name in names).run(recorder)
    tests = {name: "pass" if name in recorder.passed else "fail" for name in names}
    return tests, recorder.reasons


def load_env_file(app_dir):
    """Load the student's .env, which the PA2 handout asks them to submit.

    Runs before the import because student code may read these values at import.
    Existing variables keep their values.
    """
    for folder in (app_dir, os.path.dirname(app_dir)):
        path = os.path.join(folder, ".env")
        if not os.path.isfile(path):
            continue
        with open(path, errors="replace") as source:
            for line in source:
                line = line.strip()
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip():
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))
        return


def write_results(path, status, error=None, tests=None, reasons=None):
    with open(path, "w") as out:
        json.dump({"status": status, "error": error, "tests": tests or {}, "reasons": reasons or {}}, out)


def import_test_file(test_path):
    spec = importlib.util.spec_from_file_location("graded_tests", test_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_against_containers(test_path, results_path, mode):
    try:
        module = import_test_file(test_path)
    except BaseException:
        write_results(results_path, "import_error", traceback.format_exc())
        return
    module.EXTRA_CREDIT = mode == "extra"
    tests, reasons = run_tests(module.TestRoutes, mode)
    write_results(results_path, "ok", None, tests, reasons)


def run(app_dir, test_path, results_path, mode, external=False):
    if external:
        run_against_containers(test_path, results_path, mode)
        return
    if port_is_busy():
        write_results(results_path, "port_busy", PORT_BUSY_HINT)
        return

    # Append, not insert, so the standard library wins over student files.
    sys.path.append(app_dir)
    try:
        load_env_file(app_dir)
        module = import_test_file(test_path)
    except BaseException:
        write_results(results_path, "import_error", traceback.format_exc())
        return

    module.EXTRA_CREDIT = mode == "extra"
    threading.Thread(
        target=module.app.run,
        kwargs={
            "host": "0.0.0.0",
            "port": PORT,
            "debug": False,
            "use_reloader": False,
        },
        daemon=True,
    ).start()
    if not wait_for_server():
        write_results(
            results_path,
            "runner_error",
            f"The server did not accept connections within {SERVER_WAIT_SECONDS} seconds.",
        )
        return

    tests, reasons = run_tests(module.TestRoutes, mode)
    write_results(results_path, "ok", None, tests, reasons)


def main():
    results_path = sys.argv[3] if len(sys.argv) > 3 else None
    try:
        external = len(sys.argv) > 5 and sys.argv[5] == "external"
        run(sys.argv[1], sys.argv[2], results_path, sys.argv[4], external)
    except BaseException:
        if results_path:
            try:
                write_results(results_path, "runner_error", traceback.format_exc())
            except OSError:
                pass
    finally:
        # The server thread never returns, so exit without waiting for it.
        os._exit(0)


if __name__ == "__main__":
    main()
