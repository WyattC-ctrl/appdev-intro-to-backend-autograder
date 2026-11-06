"""Where the project's files live, and how a test file maps to its grades folder."""
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSIGNMENT_TESTS = PROJECT_ROOT / "assignment_tests"
DEFAULT_GRADES = PROJECT_ROOT / "grades"
FILE_PREFIX = "CS_1998_S603"  # the course and section in CMS file names
SHEETS_FOLDER = "sheets"  # holds the .txt sheets inside each test's grades folder


def assignment_id(test_path):
    """The assignment a test file belongs to: pa2_test.py becomes PA2."""
    match = re.search(r"pa\d+", test_path.stem, re.IGNORECASE)
    return match.group().upper() if match else test_path.stem
