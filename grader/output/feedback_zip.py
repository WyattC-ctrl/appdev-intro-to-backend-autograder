"""Build and update the feedback zip uploaded to CMS.

CMS expects one folder per NetID inside a feedback_template folder, and each
feedback file must have "feedback" in its name.
"""
import os
import zipfile

from grader.paths import FILE_PREFIX, SHEETS_FOLDER, assignment_id

ROOT_FOLDER = "feedback_template"


def feedback_zip_path(out_dir, test_path):
    return out_dir / f"{FILE_PREFIX}_{assignment_id(test_path)}_feedback.zip"


def write_feedback_zip(out_dir, test_path, students):
    """Zip each student's sheet. A student with no sheet gets an empty folder."""
    assignment = assignment_id(test_path)
    path = feedback_zip_path(out_dir, test_path)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for student in students:
            folder = f"{ROOT_FOLDER}/{student}/"
            sheet = out_dir / SHEETS_FOLDER / f"{student}.txt"
            if sheet.is_file():
                archive.write(sheet, f"{folder}{assignment}_feedback.txt")
            else:
                archive.writestr(folder, "")
    return path


def update_feedback_zip(out_dir, test_path, student):
    """Replace one student's entry. Every other entry is copied across unchanged."""
    path = feedback_zip_path(out_dir, test_path)
    folder = f"{ROOT_FOLDER}/{student}/"
    sheet = out_dir / SHEETS_FOLDER / f"{student}.txt"
    new_name = f"{folder}{assignment_id(test_path)}_feedback.txt"
    temp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as old, zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as new:
        replaced = False
        for item in old.infolist():
            if not item.filename.startswith(folder):
                new.writestr(item, old.read(item.filename))
            elif not replaced:
                new.write(sheet, new_name)
                replaced = True
        if not replaced:
            new.write(sheet, new_name)
    os.replace(temp, path)
