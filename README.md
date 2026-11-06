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
  CS_1998_S603_PA2_scores.csv    upload to CMS as the scores
  CS_1998_S603_PA2_feedback.zip  upload to CMS as the feedback files
  sheets/
    abc123.txt                   one grade sheet per student
```

Rerunning a test replaces that test's results and leaves other tests alone.

The feedback zip has one folder per NetID, with that student's sheet inside as `PA2_feedback.txt`:

```
feedback_template/
  abc123/PA2_feedback.txt
  def456/PA2_feedback.txt
```

## Grade sheet format

Each `.txt` sheet starts with the score, then shows only the sections that apply. A full sheet looks like this:

```
Total:         10
Deductions:   -3.5
Extra Credit: +1
Score:         7.5

Points lost:
-1  Zipped venv, .db, or pycache
-1  Included the test file
-1.5  3 tests fail

Core tests failed (3 of 10):
- test_create_post: POST request to route '/api/posts/' returned a status code of 500, but 201 was expected.
- test_delete_post: Creation of a post failed. See `test_create_post` results.
- test_get_invalid_post: Using an invalid post id of 10000, GET request to route '/api/posts/10000/' did not return a JSON response.

Extra credit:
+1  Implemented tier 1 challenge
Tier 2 not earned (2 of 3 tests passed). Failed:
- test_extra_sorting_posts: The list is not in increasing order.

Notes:
- 2 zip files were found; graded the largest, pa1.zip.

Style feedback (no points lost):
- app.py: add a comment or docstring to get_posts, create_post.
- app.py: use snake_case for postId (line 42).
```

| Section | What it shows |
|---|---|
| Header | The total, deductions, extra credit, and score. The score never goes below 0 |
| Points lost | Each deduction, or `Points lost: none` |
| Core tests | Each failed test with a short reason, or `Core tests: all 10 passed` |
| Extra credit | Tiers earned, then tiers not earned. Failed tests are listed only if at least one test in that tier passed |
| Notes | Anything else about the run, such as multiple zips or tests that could not run |
| Style feedback | Suggestions that cost no points. Left out when there are none |

A student who lost no points and did not try the extra credit:

```
Total:         10
Deductions:   0
Extra Credit: 0
Score:         10

Points lost: none

Core tests: all 10 passed

Extra credit:
Tier 1 not earned (0 of 3 tests passed).
Tier 2 not earned (0 of 3 tests passed).
```

A student with no zip:

```
Total:         10
Deductions:   -12
Extra Credit: 0
Score:         0

Points lost:
-10  Cannot find source code
-1  No README
-1  No exported Postman collection

Notes:
- No zip file was found in this student's folder.
```

When the tests cannot run, every core test counts as failed and the note gives the reason:

```
Total:         10
Deductions:   -5
Extra Credit: 0
Score:         5

Points lost:
-5  10 tests fail

Notes:
- The tests could not run (import_error): ModuleNotFoundError: No module named 'db'
```

### Deductions

| Deduction | Points |
|---|---|
| Cannot find source code (no `app.py`) | -10 |
| Zipped venv, .db, or pycache | -1 |
| Included the test file | -1 |
| No README | -1 |
| No exported Postman collection | -1 |
| Each failing core test | -0.5, up to -10 |

## Before you upload

Check that no student's tests failed to run:

```bash
grep -l "could not run" grades/PA2/sheets/*.txt
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
  output/             grade sheets, scores CSV, feedback zip, and test listings
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
