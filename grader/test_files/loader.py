"""Read a test file: its core and extra-credit tests, tiers, and warnings."""
import importlib.util
import inspect
import sys
import types
from unittest import mock

from grader.running.run_one import split_tests


class TestFileError(Exception):
    """The test file cannot be imported or has no TestRoutes class."""


class StubModule(types.ModuleType):
    """Stands in for a module that is not needed to read a test file's source."""

    __path__ = []  # lets submodules such as requests.api be imported and stubbed too

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return mock.MagicMock()


class TestFileInfo:
    def __init__(self, path, core, extra, tiers, bonuses, warnings):
        self.path = path
        self.core = core
        self.extra = extra
        self.tiers = tiers
        self.bonuses = bonuses
        self.warnings = warnings


def import_with_stubs(path):
    """Import the test file for inspection, without any student's app.

    `app` is always a stub. A missing third-party module such as requests is
    stubbed too, because only the source of the tests is needed here.
    """
    stubbed = {"app": StubModule("app")}
    saved = sys.modules.get("app")
    sys.modules["app"] = stubbed["app"]
    try:
        while True:
            spec = importlib.util.spec_from_file_location("graded_tests_info", path)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                return module
            except ModuleNotFoundError as error:
                if not error.name or error.name in stubbed:
                    raise
                stub = StubModule(error.name)
                stubbed[error.name] = stub
                sys.modules[error.name] = stub
    finally:
        for name in stubbed:
            sys.modules.pop(name, None)
        if saved is not None:
            sys.modules["app"] = saved


def functions_defined_in(module):
    """Yield the module's own functions and the methods of its own classes."""
    for obj in vars(module).values():
        if inspect.isfunction(obj) and obj.__module__ == module.__name__:
            yield obj
        elif inspect.isclass(obj) and obj.__module__ == module.__name__:
            for member in vars(obj).values():
                if inspect.isfunction(member):
                    yield member


def load_test_file(path):
    """Return a TestFileInfo. Raises TestFileError if the file cannot be used."""
    try:
        module = import_with_stubs(path)
    except Exception as error:
        raise TestFileError(f"could not read test file {path}: {error}") from error
    if not inspect.isclass(getattr(module, "TestRoutes", None)):
        raise TestFileError(f"test file {path} does not define a TestRoutes class.")

    core, extra = split_tests(module.TestRoutes)
    raw_tiers = getattr(module, "TIERS", None)
    tiers = raw_tiers if isinstance(raw_tiers, dict) else {}
    raw_bonuses = getattr(module, "TIER_BONUS", None)
    bonuses = raw_bonuses if isinstance(raw_bonuses, dict) else {}

    warnings = []
    if not tiers:
        warnings.append(
            f"TIERS is missing or empty in {path.name}; no extra credit will be graded."
        )
    for function in functions_defined_in(module):
        name = function.__name__
        if "extra" in name.lower() and not name.startswith("test"):
            warnings.append(
                f'Function "{name}" contains "extra" but does not start with "test", so it will never run.'
            )
    if tiers:
        listed = {name for names in tiers.values() for name in names}
        for name in extra:
            if name not in listed:
                warnings.append(f'Extra-credit test "{name}" is not listed in any tier.')
    return TestFileInfo(path, core, extra, tiers, bonuses, warnings)
