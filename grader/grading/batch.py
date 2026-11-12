"""Grade one student, or every student in a folder."""
import shutil
import tempfile
from pathlib import Path

from grader.grading.scoring import score_submission
from grader.output.feedback_zip import write_feedback_zip
from grader.output.formatting import number
from grader.output.scores_csv import NO_SUBMISSION, SCORE_COLUMNS, write_scores_csv
from grader.output.sheet import build_sheet
from grader.paths import SHEETS_FOLDER, assignment_id
from grader.running.runner import run_student_tests
from grader.style.feedback import style_feedback
from grader.submissions.contents import inspect_submission
from grader.submissions.readme import blank_answers, find_readme


def grade_student(student_dir, info, no_extra, sheets_dir):
    """Write one student's sheet. Return (score, run status, whether a zip was found)."""
    # Extra tests only run when they can earn credit.
    run_extra_tests = not no_extra and bool(info.tiers)
    work = Path(tempfile.mkdtemp(prefix="grade_"))
    try:
        extract_dir = work / "extracted"
        extract_dir.mkdir()
        submission = inspect_submission(student_dir, extract_dir, info.path.name)
        run = None
        if submission.app_dir is not None and (info.readme_fields or info.readme_questions):
            readme = find_readme(submission.app_dir)
            if readme is not None:
                submission.readme_blanks = blank_answers(readme, info.readme_fields, info.readme_questions)
        if submission.app_dir is not None:
            try:
                submission.style = style_feedback(submission.app_dir, info.path.name)
            except Exception:  # feedback must never affect grading
                submission.style = None
            run = run_student_tests(
                submission.app_dir,
                info.path,
                work / "results.json",
                "extra" if run_extra_tests else "core",
                docker=info.docker,
                remote=info.remote,
                netid=student_dir.name,
            )
        result = score_submission(info, submission, run, not no_extra)
        sheet = build_sheet(info, submission, run, not no_extra, result)
        (sheets_dir / f"{student_dir.name}.txt").write_text(sheet, encoding="utf-8")
        return result.score, run["status"] if run else "no app", submission.has_zip
    finally:
        shutil.rmtree(work, ignore_errors=True)


def grade_folder(students, info, test_path, out_dir, no_extra, column):
    """Grade every student folder and write the sheets, scores CSV, and feedback zip."""
    sheets_dir = out_dir / SHEETS_FOLDER
    sheets_dir.mkdir(parents=True, exist_ok=True)
    folders = sorted(
        p for p in students.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name != "__MACOSX"
    )
    assignment = assignment_id(test_path)
    if not column and assignment not in SCORE_COLUMNS:
        print(f'Warning: no known CMS column name for {assignment}; using "{assignment}". Set it with --column.')
    rows = []
    port_busy = 0
    for student_dir in folders:
        try:
            score, status, has_zip = grade_student(student_dir, info, no_extra, sheets_dir)
            print(f"{student_dir.name}: score {number(score)} ({status})", flush=True)
            port_busy += status == "port_busy"
            rows.append((student_dir.name, score, "" if has_zip else NO_SUBMISSION))
        except Exception as error:  # one student must never stop the batch
            print(f"{student_dir.name}: could not grade ({error})", flush=True)
            rows.append((student_dir.name, None, ""))
    write_scores_csv(out_dir, test_path, column, rows)
    write_feedback_zip(out_dir, test_path, [folder.name for folder in folders])
    if port_busy:
        print(
            f"WARNING: port 5000 was busy for {port_busy} students, so their scores are wrong. "
            "Free the port and rerun before uploading."
        )
