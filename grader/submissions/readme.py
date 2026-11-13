"""Check that a README template's fields and questions are filled in.

A test file lists them in README_FIELDS (such as "NetID") and README_QUESTIONS
(the question text). An answer is blank when nothing follows it, or only a
placeholder such as <Your answer here>, or when the student removed it.
"""
import re

PLACEHOLDER = re.compile(r"<[^<>]*>")


def find_readme(app_dir):
    """The README next to app.py or in the folder above, preferring README.txt."""
    found = []
    for folder in (app_dir.parent, app_dir):
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.name.lower().startswith("readme"):
                found.append(path)
    found.sort(key=lambda path: path.suffix.lower() != ".txt")
    return found[0] if found else None


def simplify(text):
    """Lowercase, with spaces and punctuation collapsed, so small edits still match."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def is_blank(text):
    return not PLACEHOLDER.sub("", text).strip()


def field_line(lines, label):
    """Index of the line that starts with "label:", or None."""
    wanted = simplify(label)
    for index, line in enumerate(lines):
        before, colon, _ = line.partition(":")
        if colon and simplify(before) == wanted:
            return index
    return None


def question_line(lines, question):
    """Index of the line holding this question, or None."""
    wanted = simplify(question)
    for index, line in enumerate(lines):
        if wanted and simplify(line).startswith(wanted):
            return index
    return None


def blank_answers(readme_path, fields, questions):
    """Return the fields and questions that are left blank, in template order."""
    lines = readme_path.read_text(errors="replace").splitlines()
    starts = {}
    for label in fields:
        starts[("field", label)] = field_line(lines, label)
    for question in questions:
        starts[("question", question)] = question_line(lines, question)
    taken = sorted(index for index in starts.values() if index is not None)

    blank = []
    for (kind, text), index in starts.items():
        if index is None:
            blank.append(text if kind == "field" else f'"{text}"')
            continue
        following = [i for i in taken if i > index]
        end = following[0] if following else len(lines)
        if kind == "field":
            answer = lines[index].partition(":")[2]
            if is_blank(answer) and index + 1 < end:
                # The value may be on the next line instead, as long as it is not a heading.
                next_line = lines[index + 1]
                answer = "" if simplify(next_line) == "questions" else next_line
            if is_blank(answer):
                blank.append(text)
        else:
            # Some students answer on the same line as the question.
            same_line = simplify(lines[index])[len(simplify(text)):]
            if not same_line.strip() and is_blank("\n".join(lines[index + 1:end])):
                blank.append(f'"{text}"')
    return blank
