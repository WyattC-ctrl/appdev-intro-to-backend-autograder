"""Build the feedback zip uploaded to CMS.

CMS expects one folder per NetID inside a feedback_template folder, and each
feedback file must have "feedback" in its name.
"""
import zipfile

from grader.paths import FILE_PREFIX, SHEETS_FOLDER, assignment_id

ROOT_FOLDER = "feedback_template"


def write_feedback_zip(out_dir, test_path, students):
    """Zip each student's sheet. A student with no sheet gets an empty folder."""
    assignment = assignment_id(test_path)
    path = out_dir / f"{FILE_PREFIX}_{assignment}_feedback.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for student in students:
            folder = f"{ROOT_FOLDER}/{student}/"
            sheet = out_dir / SHEETS_FOLDER / f"{student}.txt"
            if sheet.is_file():
                archive.write(sheet, f"{folder}{assignment}_feedback.txt")
            else:
                archive.writestr(folder, "")
    return path
