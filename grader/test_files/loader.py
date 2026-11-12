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
    def __init__(self, path, core, extra, tiers, bonuses, warnings, docker=False, rubric=None, extra_needs=None,
                 remote=False, no_challenges=False, readme_fields=(), readme_questions=()):
        self.path = path
        self.readme_fields = list(readme_fields)  # README template fields that must be filled in
        self.readme_questions = list(readme_questions)  # README template questions that must be answered
        self.remote = remote  # the tests call the student's deployed server
        self.no_challenges = no_challenges  # the assignment has no extra credit
        self.rubric = rubric or []  # [(section, [(test, points, label, lost label)])]
        self.extra_needs = extra_needs  # (test, why) that must pass before extra credit counts
        self.docker = docker  # the app runs with docker compose instead of being imported
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

    no_challenges = getattr(module, "NO_CHALLENGES", False) is True
    warnings = []
    if not tiers and not no_challenges:
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
    docker = getattr(module, "DOCKER", False) is True
    rubric = getattr(module, "RUBRIC", None) or []
    if rubric:
        listed = {item[0] for _, items in rubric for item in items}
        for name in sorted(listed - set(core)):
            warnings.append(f'Rubric test "{name}" is not a core test, so it can never pass.')
        for name in core:
            if name not in listed:
                warnings.append(f'Core test "{name}" is not in the rubric, so it is worth no points.')
    extra_needs = getattr(module, "EXTRA_CREDIT_NEEDS", None)
    remote = getattr(module, "REMOTE", False) is True
    readme_fields = getattr(module, "README_FIELDS", None) or ()
    readme_questions = getattr(module, "README_QUESTIONS", None) or ()
    return TestFileInfo(
        path, core, extra, tiers, bonuses, warnings, docker, rubric, extra_needs, remote, no_challenges,
        readme_fields, readme_questions,
    )
