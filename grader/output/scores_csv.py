"""Write and update the scores CSV uploaded to CMS."""
import csv
import os

from grader.paths import FILE_PREFIX, assignment_id

SCORE_COLUMNS = {"PA1": "PA1 - Reddit", "PA2": "PA2 - Venmo (BASIC)", "PA5": "PA5 Dockerize CMS"}


NO_SUBMISSION = "No submission"


def scores_csv_path(out_dir, test_path):
    return out_dir / f"{FILE_PREFIX}_{assignment_id(test_path)}_scores.csv"


def score_text(score):
    return f"{float(score):.1f}"


def write_scores_csv(out_dir, test_path, column, rows):
    """Write the CMS upload file. A score of None leaves that student blank."""
    assignment = assignment_id(test_path)
    path = scores_csv_path(out_dir, test_path)
    with open(path, "w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        column_name = column or SCORE_COLUMNS.get(assignment, assignment)
        writer.writerow(["NetID", column_name, "Total", "Adjustments", "Add Comments"])
        for student, score, comment in rows:
            value = "" if score is None else score_text(score)
            writer.writerow([student, value, value, "", comment])
    return path


def read_student_score(out_dir, test_path, student):
    """Return the student's current score text, or None if they are not in the file."""
    with open(scores_csv_path(out_dir, test_path), newline="") as source:
        for row in csv.reader(source):
            if row and row[0] == student:
                return row[1]
    return None


def update_student_score(out_dir, test_path, student, score):
    """Change one student's row. Every other row and the header stay exactly as they are."""
    path = scores_csv_path(out_dir, test_path)
    with open(path, newline="") as source:
        rows = list(csv.reader(source))
    for row in rows:
        if row and row[0] == student:
            row[1] = row[2] = score_text(score)
            # They have a submission now, but any comment of your own stays.
            if len(row) > 4 and row[4] == NO_SUBMISSION:
                row[4] = ""
    temp = path.with_suffix(".tmp")
    with open(temp, "w", newline="") as output:
        csv.writer(output, lineterminator="\n").writerows(rows)
    os.replace(temp, path)
