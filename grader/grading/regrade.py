"""Regrade one student from their zip, changing only that student's results."""
import shutil
import tempfile
import zipfile
from pathlib import Path

from grader.grading.batch import grade_student
from grader.output.feedback_zip import feedback_zip_path, update_feedback_zip
from grader.output.formatting import number
from grader.output.scores_csv import read_student_score, scores_csv_path, update_student_score
from grader.paths import SHEETS_FOLDER


class RegradeError(Exception):
    """The regrade could not happen. Nothing in the grades folder was changed."""


def check_can_regrade(zip_path, student, test_path, out_dir):
    if not zipfile.is_zipfile(zip_path):
        raise RegradeError(f"{zip_path.name} is not a valid zip.")
    if not (scores_csv_path(out_dir, test_path).is_file() and feedback_zip_path(out_dir, test_path).is_file()):
        raise RegradeError(f"No grades found in {out_dir}. Grade the whole folder for this test first.")
    if read_student_score(out_dir, test_path, student) is None:
        raise RegradeError(f"{student} is not in the scores file. Check the NetID.")


def regrade_student(zip_path, student, info, test_path, out_dir, no_extra):
    """Grade the zip, then replace this student's sheet, CSV row, and feedback zip entry."""
    check_can_regrade(zip_path, student, test_path, out_dir)
    previous = read_student_score(out_dir, test_path, student)
    # Grade in a temp folder so a failed run leaves the real grades alone.
    with tempfile.TemporaryDirectory(prefix="regrade_") as work:
        work = Path(work)
        student_dir = work / student
        student_dir.mkdir()
        shutil.copyfile(zip_path, student_dir / zip_path.name)
        temp_sheets = work / SHEETS_FOLDER
        temp_sheets.mkdir()
        score, status, _ = grade_student(student_dir, info, no_extra, temp_sheets)
        if status == "port_busy":
            raise RegradeError("Port 5000 is busy, so the tests could not run. Free the port and try again.")
        sheets_dir = out_dir / SHEETS_FOLDER
        sheets_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(temp_sheets / f"{student}.txt", sheets_dir / f"{student}.txt")
    update_student_score(out_dir, test_path, student, score)
    update_feedback_zip(out_dir, test_path, student)
    print(f"{student}: score {number(float(previous)) if previous else 'blank'} -> {number(score)} ({status})")
