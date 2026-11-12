# Flask Assignment Grader

Grades PA1–PA6 submissions and writes a grade sheet for each student, plus a scores file for CMS.

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

Then run the tool with that folder and the assignment's test file (`pa1_test.py` to `pa6_test.py`):

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

## Regrade one student

To regrade a single student, download their zip and run the tool on it with their NetID:

```bash
python3 grade.py ~/Downloads/pa3.zip --test pa3_test.py --student abc123
```

This replaces only that student's sheet, their row in the scores CSV, and their file in the feedback zip. Everyone else's results stay exactly as they are, including any edits you made to other rows in the CSV.

If a zip has more than one `app.py`, the tool uses the one in a `src` folder, as the handouts lay it out. Otherwise it uses the shallowest.

Grade the whole folder for that test first. If the zip is invalid, the NetID is not in the scores file, or port 5000 is busy, the tool stops and changes nothing.

## PA5 (Docker)

PA5 needs Docker Desktop running. Instead of importing `app.py`, the tool grades each student the way the handout says:

1. It runs `docker compose up -d` in the student's `src` folder, which pulls their image from Docker Hub.
2. It runs the tests against the container.
3. It removes the containers and any images it pulled.

```bash
python3 grade.py ~/Downloads/Submissions --test pa5_test.py
```

PA5 is scored by this rubric instead of −0.5 per failed test. Each line is worth its own points, and the sheet lists every line:

| Section | Points | Check |
|---|---|---|
| Dockerfile | 1 | `Dockerfile` is in `src/` |
| | 1 | It runs `pip install -r requirements.txt` |
| | 1 | It has a `CMD` or `ENTRYPOINT` that starts the app |
| docker-compose.yml | 1 | `docker-compose.yml` is in `src/` |
| | 1 | It uses a Docker Hub image named `username/repo` |
| | 1 | It publishes a port |
| Container works | 2 | `docker compose up -d` starts the container |
| | 2 | A GET route named in the README, or `/api/courses/`, returns JSON |

The README, Postman, and venv deductions apply as for the other assignments. Each README template field or question left blank is −0.5 (see below). Extra credit counts only when the container runs:

| Tier | Points | Checks |
|---|---|---|
| Tier 1 | +1 | The Dockerfile uses a Python image other than the basic one, such as `python:3.11-slim` |
| Tier 2 | +1, +1 more with Tier 1 | gunicorn is in `requirements.txt`; `start_server.sh` starts it with 4 workers; the Dockerfile runs `sh start_server.sh`; the container is served by gunicorn |

If the container cannot start, the sheet gives the reason, such as a missing image on Docker Hub. The tool does not run a compose file that mounts folders outside the submission or uses privileged mode.

The feedback form and the README questions are not checked.

## PA6 (deployment)

PA6 calls each student's deployed server at the address in their README ("Your Server Address:"). It doesn't run `app.py` or Docker, so the servers need to be up when you grade.

```bash
python3 grade.py ~/Downloads/Submissions --test pa6_test.py --column "EXACT CMS COLUMN NAME"
```

| Section | Points | Check |
|---|---|---|
| Deployed server | 3 | The server address in the README answers |
| | 2 | `GET /` returns `"<netid> was here!"` with status 200, using the student's folder name as the NetID |
| | 2 | The working endpoint from the README, or `/api/courses/`, returns JSON |
| Environment variables | 1 | `src/.env` exists and contains the NetID |
| | 1 | `app.py` reads an environment variable and doesn't hardcode `"<netid> was here"` |
| Files | 1 | `Dockerfile`, `docker-compose.yml`, and `.dockerignore` are in `src/` |

The README, Postman, and venv deductions apply as for the other assignments. PA6 has no extra credit. The feedback form is not checked.

### README answers (PA5 and PA6)

Each field (`Name`, `NetID`, `Working Endpoint`, and `Your Docker Hub Repository Link` or `Your Server Address`) and each template question left blank is −0.5. An answer is blank when nothing follows it, only a placeholder such as `<Your answer here>` is there, or the question was removed. The sheet names each one:

```
-1  README has 2 blank answers
    Blank: NetID, "What are environment variables?"
```

PA5's `Challenges Attempted` field is not required. The tool checks that an answer is there, not that it is correct.

## Grade sheet format

Each `.txt` sheet starts with the score, then shows only the sections that apply. Every point lost has its own line with the amount and the reason. A full sheet looks like this:

```
Total:         10
Deductions:   -2.5
Extra Credit: +1
Score:         8.5

Points lost:
-1    Included files that should not be submitted (venv, .db, __pycache__, or the test file)
-1.5  3 core tests failed, -0.5 each (listed below)

Core tests failed (3 of 10, -0.5 each):
- test_create_post: POST request to route '/api/posts/' returned a status code of 500, but 201 was expected.
- test_delete_post: Creation of a post failed. See `test_create_post` results.
- test_get_invalid_post: Using an invalid post id of 10000, GET request to route '/api/posts/10000/' did not return a JSON response.

Challenges (extra credit): +1 received
Tier 1: +1, earned (3 of 3 tests passed)
Tier 2: +0, not earned (2 of 3 tests passed). Failed:
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
| Points lost | One line per deduction with its amount, and the reason under it when there is one. `Points lost: none` when nothing was lost |
| Core tests | Each failed test with a short reason, or `Core tests: all 10 passed`. PA5 and PA6 show their rubric here instead, with the points earned on each line |
| Challenges | The extra credit received, then one line per tier (and bonus) saying `+1, earned` or `+0, not earned` with how many of its tests passed. Failed tests are listed only if at least one test in that tier passed |
| Notes | Anything else about the run, such as multiple zips or tests that could not run |
| Style feedback | Suggestions that cost no points. Left out when there are none |

When there is no challenge credit, the challenges line says why: `+0, no challenge points received`, `not checked for this run` (with `--no-extra`), `+0, not checked because the tests could not run`, `+0, not given because the container did not run` (PA5), or `none for this assignment` (PA6).

A tier bonus (PA3 to PA5) has its own line:

```
Challenges (extra credit): +3 received
Tier 1: +1, earned (2 of 2 tests passed)
Tier 2: +1, earned (1 of 1 test passed)
Bonus: +1, earned for completing tiers 1 and 2
```

A student who lost no points and did not try the challenges:

```
Total:         10
Deductions:   0
Extra Credit: 0
Score:         10

Points lost: none

Core tests: all 10 passed

Challenges (extra credit): +0, no challenge points received
Tier 1: +0, not earned (0 of 3 tests passed)
Tier 2: +0, not earned (0 of 3 tests passed)
```

A student with no zip:

```
Total:         10
Deductions:   -12
Extra Credit: 0
Score:         0

Points lost:
-10  No app.py was found, so nothing could be graded
-1   No README file
-1   No exported Postman collection (.json)

Challenges (extra credit): +0, not checked because no app.py was found

Notes:
- No zip file was found in this student's folder.
```

When the tests cannot run, every core test counts as failed and the note gives the reason:

```
Points lost:
-5  All 10 core tests counted as failed because the tests could not run, -0.5 each (see Notes)

Challenges (extra credit): +0, not checked because the tests could not run (see Notes)

Notes:
- The tests could not run (import_error): ModuleNotFoundError: No module named 'db'
```

A PA5 student whose image is not on Docker Hub:

```
Points lost:
-2  The container did not start with docker compose up -d
    docker compose up -d failed: pull access denied for abc123/pa5, repository does not exist or may require 'docker login'
-2  No route returned JSON
    The container was not running, so no route could be called.

Rubric (points earned):
Dockerfile 3/3
  +1  Dockerfile is in src/
  +1  Installs requirements.txt
  +1  CMD starts the app
docker-compose.yml 3/3
  +1  docker-compose.yml is in src/
  +1  Uses a Docker Hub image (username/repo)
  +1  Publishes a port
Container works 0/4
  +0  Container starts (worth 2)
  +0  Route returns JSON (worth 2)

Challenges (extra credit): +0, not given because the container did not run
```

### Deductions

| Deduction | Points |
|---|---|
| No `app.py` was found | -10 |
| Zipped venv, `.db`, pycache, or test file (-1 in total, even with several) | -1 |
| No README | -1 |
| Each blank README field or question (PA5 and PA6) | -0.5 |
| No exported Postman collection (a `.json` export with any name counts) | -1 |
| Included a Postman folder, even alongside a `.json` export (replaces the deduction above) | -1 |
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
| PA5 says Docker is not running | Open Docker Desktop and wait until it says it is running |
| The scores column name is wrong (PA3, PA4, and PA6) | Add `--column "EXACT CMS COLUMN NAME"` to the command |

## Project layout

```
grade.py              starts the tool
grader/
  cli.py              command-line options
  paths.py            project folders and assignment names
  grading/            grades a folder and works out scores
  running/            runs each student's app and tests, or their containers for PA5
  submissions/        extracts zips and checks their contents
  test_files/         reads tests and tiers from a test file
  output/             grade sheets, scores CSV, feedback zip, and test listings
  style/              style feedback
assignment_tests/     pa1_test.py to pa6_test.py
tests/                tests for the tool
docs/CHANGES.md       every change made to the test files
grades/               results, one folder per test (not uploaded to GitHub)
```

## More

- Skip extra credit: `--no-extra`
- Show a test file's tests and tiers: `python3 grade.py --list-tests --test pa2_test.py`
- Run the tool's own tests: `.venv/bin/python -B -m unittest discover -s tests`
- Also run the tests that use Docker: `RUN_DOCKER_TESTS=1 .venv/bin/python -B -m unittest discover -s tests`
- See every change made to the test files: `docs/CHANGES.md`
