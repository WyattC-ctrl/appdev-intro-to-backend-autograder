# Flask Assignment Grader

Grades PA1–PA4 submissions and writes a grade sheet for each student, plus a scores file for CMS.

Requires macOS and Python 3.9 or later.

## Setup

Do this once, from this folder:

```bash
python3 -m venv .venv
.venv/bin/pip install flask requests
```

## Grade an assignment

Put your submissions in a folder with one subfolder per student, named by NetID:

```
Submissions/
  abc123/pa2.zip
  def456/
  ghi789/pa2.zip
```

Then run the tool with that folder and the assignment's test file (`pa1_test.py` to `pa4_test.py`):

```bash
python3 grade.py ~/Downloads/Submissions --test pa2_test.py
```

## Results

Everything goes in `grades/`, with a separate folder for each test:

```
grades/PA2/
  abc123.txt                     one grade sheet per student
  CS_1998_S603_PA2_scores.csv    the file to upload to CMS
```

Rerunning a test replaces that test's results and leaves other tests alone.

## Before you upload

Check that no student's tests failed to run:

```bash
grep -l "could not run" grades/PA2/*.txt
```

A few names usually mean a problem with those students' code. If most students are listed, read the note on one of their sheets, fix the cause, and run the tool again.

## Common problems

| Problem | Fix |
|---|---|
| Port 5000 is busy | Turn off AirPlay Receiver in System Settings > General > AirDrop & Handoff |
| Most students show `No module named ...` | Install that package with `.venv/bin/pip install PACKAGE_NAME`, then run again |
| Another grading run is in progress | Wait for it to finish. Only one can run at a time |
| The scores column name is wrong (PA3 and PA4) | Add `--column "EXACT CMS COLUMN NAME"` to the command |

## Project layout

```
grade.py              starts the tool
grader/
  cli.py              command-line options
  paths.py            project folders and assignment names
  grading/            grades a folder and works out scores
  running/            runs each student's app and tests
  submissions/        extracts zips and checks their contents
  test_files/         reads tests and tiers from a test file
  output/             grade sheets, scores CSV, and test listings
  style/              style feedback
assignment_tests/     pa1_test.py to pa4_test.py
tests/                tests for the tool
docs/CHANGES.md       every change made to the test files
grades/               results, one folder per test (not uploaded to GitHub)
```

## More

- Skip extra credit: `--no-extra`
- Show a test file's tests and tiers: `python3 grade.py --list-tests --test pa2_test.py`
- Run the tool's own tests: `.venv/bin/python -B -m unittest discover -s tests`
- See every change made to the test files: `docs/CHANGES.md`
