"""Build the style feedback lines for a student's sheet."""
import ast
import io
import tokenize
from pathlib import Path

from grader.style.checks import (
    MAX_BLANK_LINES,
    MAX_LINE_LENGTH,
    camel_case_names,
    commented_out_lines,
    crowded_definitions,
    extra_blank_runs,
    join_limited,
    line_ranges,
    long_lines,
    multiline_string_lines,
    undocumented,
)

MAX_FEEDBACK_LINES = 8


def check_source(name, source):
    """Return feedback lines for one file's source text."""
    tree = ast.parse(source)
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    comment_lines = {t.start[0] for t in tokens if t.type == tokenize.COMMENT}
    lines = source.splitlines()
    string_lines = multiline_string_lines(tokens)

    feedback = []
    missing = undocumented(tree, comment_lines)
    if missing:
        feedback.append(f"{name}: add a comment or docstring to {join_limited(missing)}.")

    camel = camel_case_names(tree)
    if camel:
        items = [f"{n} (line {line})" for n, line in sorted(camel.items(), key=lambda item: item[1])]
        feedback.append(f"{name}: use snake_case for {join_limited(items)}.")

    commented_out = commented_out_lines(tokens, lines)
    if commented_out:
        feedback.append(f"{name}: remove commented-out code at {join_limited(line_ranges(commented_out))}.")

    too_long = long_lines(lines, string_lines)
    if too_long:
        feedback.append(
            f"{name}: shorten lines over {MAX_LINE_LENGTH} characters at {join_limited(line_ranges(too_long))}."
        )

    blank_runs = extra_blank_runs(lines, string_lines)
    if blank_runs:
        items = [f"line {n}" for n in blank_runs]
        feedback.append(f"{name}: use at most {MAX_BLANK_LINES} blank lines in a row near {join_limited(items)}.")

    crowded = crowded_definitions(tree, lines, comment_lines)
    if crowded:
        feedback.append(f"{name}: add a blank line before {join_limited(crowded)}.")
    return feedback


def is_student_file(path, test_file_name):
    name = path.name
    return not (
        name == test_file_name
        or name.startswith(("test_", "._"))
        or name.endswith("_test.py")
    )


def style_feedback(app_dir, test_file_name):
    """Return the sheet's feedback lines for the .py files beside app.py."""
    feedback = []
    for path in sorted(Path(app_dir).glob("*.py")):
        if not is_student_file(path, test_file_name):
            continue
        try:
            with tokenize.open(path) as source:
                text = source.read()
            feedback.extend(check_source(path.name, text))
        except (SyntaxError, ValueError, tokenize.TokenError, OSError, RecursionError):
            feedback.append(f"{path.name}: could not be read for style checks.")
    if len(feedback) > MAX_FEEDBACK_LINES:
        extra = len(feedback) - MAX_FEEDBACK_LINES
        feedback = feedback[:MAX_FEEDBACK_LINES] + [f"And {extra} more style notes."]
    return feedback
