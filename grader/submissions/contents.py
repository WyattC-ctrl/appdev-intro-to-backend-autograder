"""Check what a submission contains: app.py, README, Postman collection, and more."""
import json
import os
from pathlib import Path

from grader.submissions.extract import SEARCH_SKIPPED_DIRS, extract_zip, find_zips

MAX_POSTMAN_BYTES = 5 * 1024 * 1024
ARTIFACT_DIRS = {"venv", ".venv", "__pycache__"}


class Submission:
    def __init__(self):
        self.app_dir = None
        self.has_venv_db_pycache = False
        self.has_readme = False
        self.readme_blanks = []  # template fields and questions left blank
        self.has_postman = False
        self.has_postman_folder = False
        self.has_test_file = False
        self.has_zip = True
        self.style = None  # feedback lines; None when there is no code to check
        self.notes = []


def is_postman_collection(path):
    try:
        if path.stat().st_size >= MAX_POSTMAN_BYTES:
            return False
        with open(path, encoding="utf-8-sig") as source:
            data = json.load(source)
    except (OSError, ValueError, RecursionError):
        return False
    if not isinstance(data, dict) or not isinstance(data.get("info"), dict) or "item" not in data:
        return False
    # Some real exports have the Postman schema URL but no _postman_id.
    info = data["info"]
    return "_postman_id" in info or "schema.getpostman.com" in str(info.get("schema", ""))


def is_postman_folder(dirpath, dirnames, filenames):
    """True for the folder formats Postman saves, as opposed to an exported JSON."""
    if ".postman" in dirnames or os.path.isdir(os.path.join(dirpath, "postman", "collections")):
        return True
    if any(name.endswith(".request.yaml") for name in filenames):
        return True
    return os.path.basename(dirpath) == ".resources" and "definition.yaml" in filenames


def choose_app(app_paths):
    """Use the app.py in a src folder, as the handouts lay it out. Otherwise the shallowest."""
    in_src = [p for p in app_paths if p.parent.name == "src" and "site-packages" not in p.parts]
    return min(in_src or app_paths, key=lambda p: (len(p.parts), str(p)))


def scan_tree(root, test_file_name, submission):
    app_paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__MACOSX")
        relative = Path(dirpath).relative_to(root)
        searchable = not SEARCH_SKIPPED_DIRS.intersection(relative.parts)
        if ARTIFACT_DIRS.intersection(dirnames):
            submission.has_venv_db_pycache = True
        if searchable and is_postman_folder(dirpath, dirnames, filenames):
            submission.has_postman_folder = True
        for name in filenames:
            if name.startswith("._"):
                continue
            lower = name.lower()
            if lower.endswith((".db", ".pyc")):
                submission.has_venv_db_pycache = True
            if lower.endswith(".json") and not submission.has_postman:
                submission.has_postman = is_postman_collection(Path(dirpath) / name)
            if searchable:
                if name == "app.py":
                    app_paths.append(Path(dirpath) / name)
                if lower.startswith("readme"):
                    submission.has_readme = True
                if name == test_file_name:
                    submission.has_test_file = True
    if app_paths:
        submission.app_dir = choose_app(app_paths).parent


def inspect_submission(student_dir, extract_dir, test_file_name):
    submission = Submission()
    zips = find_zips(student_dir, {"__MACOSX"})
    if not zips:
        submission.has_zip = False
        submission.notes.append("No zip file was found in this student's folder.")
        return submission
    chosen = max(zips, key=lambda p: p.stat().st_size)
    if len(zips) > 1:
        submission.notes.append(
            f"{len(zips)} zip files were found; graded the largest, {chosen.name}."
        )
    if extract_zip(chosen, extract_dir, submission.notes):
        scan_tree(extract_dir, test_file_name, submission)
    return submission
