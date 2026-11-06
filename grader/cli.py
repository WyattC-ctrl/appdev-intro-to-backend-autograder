"""Command-line interface."""
import argparse
import fcntl
import os
import sys
from pathlib import Path

from grader.grading.batch import grade_folder
from grader.output.test_listing import list_tests
from grader.paths import ASSIGNMENT_TESTS, DEFAULT_GRADES, PROJECT_ROOT, assignment_id
from grader.test_files.loader import TestFileError, load_test_file


def parse_args():
    parser = argparse.ArgumentParser(description="Grade Flask assignment submissions.")
    parser.add_argument("students", nargs="?", metavar="STUDENTS_FOLDER")
    parser.add_argument("--test", metavar="PATH")
    parser.add_argument("--no-extra", action="store_true")
    parser.add_argument("--list-tests", action="store_true")
    parser.add_argument("--out", default=str(DEFAULT_GRADES), metavar="DIR",
                        help="grades folder; each test gets its own subfolder, such as DIR/PA2")
    parser.add_argument("--column", metavar="NAME", help="assignment column name in the scores CSV")
    return parser.parse_args()


def find_test_file(given):
    """Accept a path, or just a name from the assignment_tests folder."""
    path = Path(given)
    if not path.is_file() and (ASSIGNMENT_TESTS / path.name).is_file():
        path = ASSIGNMENT_TESTS / path.name
    if not path.is_file():
        sys.exit(f"Error: test file not found: {given}")
    return path.resolve()


def read_test_file(path):
    try:
        return load_test_file(path)
    except TestFileError as error:
        sys.exit(f"Error: {error}")


def lock_project():
    """Allow one grading run at a time, because every run needs port 5000.

    Two runs at once would send one student's tests to another student's app.
    The descriptor stays open on purpose: the lock lasts until the process exits.
    """
    handle = os.open(PROJECT_ROOT, os.O_RDONLY)
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("Error: another grading run is in progress. Two at once give wrong scores, so wait for it to finish.")


def main():
    args = parse_args()
    if not args.test:
        sys.exit("Error: --test PATH is required.")
    test_path = find_test_file(args.test)

    if args.list_tests:
        list_tests(read_test_file(test_path))
        return

    if not args.students:
        sys.exit("Error: the students folder is required.")
    students = Path(args.students).resolve()
    if not students.is_dir():
        sys.exit(f"Error: students folder not found: {args.students}")
    out_dir = Path(args.out).resolve() / assignment_id(test_path)
    if out_dir == students or students in out_dir.parents:
        sys.exit("Error: the output folder must not be inside the students folder.")

    lock_project()
    info = read_test_file(test_path)
    for warning in info.warnings:
        print(f"Warning: {warning}")
    grade_folder(students, info, test_path, out_dir, args.no_extra, args.column)
    print(out_dir)
