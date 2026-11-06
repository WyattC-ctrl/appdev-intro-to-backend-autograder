#!/usr/bin/env python3
"""Grade Flask assignment submissions. See README.md.

python3 grade.py STUDENTS_FOLDER --test pa2_test.py [--no-extra] [--out DIR] [--column NAME]
python3 grade.py --list-tests --test pa2_test.py
"""
import sys

# Keep __pycache__ out of the project and the test file's folder.
sys.dont_write_bytecode = True

from grader.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
