"""Find a student's zip files and extract them, including zips inside zips."""
import os
import zipfile
from pathlib import Path

MAX_NESTED_ZIP_DEPTH = 3
SEARCH_SKIPPED_DIRS = {"venv", ".venv", "__MACOSX"}


def find_zips(root, skipped_dirs):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skipped_dirs)
        for name in sorted(filenames):
            if name.lower().endswith(".zip") and not name.startswith("._"):
                found.append(Path(dirpath) / name)
    return found


def extract_zip(zip_path, dest, notes, depth=0):
    """Extract a zip and any zips inside it. Return False if this zip is unreadable."""
    try:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(dest)
    except Exception:
        notes.append(f"Could not open {zip_path.name}; it is not a valid zip.")
        return False
    if depth < MAX_NESTED_ZIP_DEPTH:
        for nested in find_zips(dest, SEARCH_SKIPPED_DIRS):
            # The suffix stops a zip named venv.zip from looking like a venv folder.
            extract_zip(nested, nested.with_name(nested.name + "_extracted"), notes, depth + 1)
    return True
