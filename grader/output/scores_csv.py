"""Write the scores CSV uploaded to CMS."""
import csv

from grader.paths import FILE_PREFIX, assignment_id

SCORE_COLUMNS = {"PA1": "PA1 - Reddit", "PA2": "PA2 - Venmo (BASIC)"}


def write_scores_csv(out_dir, test_path, column, rows):
    """Write the CMS upload file. A score of None leaves that student blank."""
    assignment = assignment_id(test_path)
    path = out_dir / f"{FILE_PREFIX}_{assignment}_scores.csv"
    with open(path, "w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        column_name = column or SCORE_COLUMNS.get(assignment, assignment)
        writer.writerow(["NetID", column_name, "Total", "Adjustments", "Add Comments"])
        for student, score, comment in rows:
            value = "" if score is None else f"{float(score):.1f}"
            writer.writerow([student, value, value, "", comment])
    return path
