"""The individual style checks. Each one reads source and never runs it.

Only clear-cut patterns are checked, because the sheets are uploaded without review.
"""
import ast
import re
import tokenize

MAX_LINE_LENGTH = 120
MAX_BLANK_LINES = 2
MAX_NAMES_PER_LINE = 5
CAMEL_CASE = re.compile(r"^[a-z_].*[a-z0-9][A-Z]")  # capitalized names are class-style
STARTER_FUNCTIONS = {"hello_world", "singleton", "getinstance"}  # from the course starter code
STARTER_BLOCK = re.compile(r"^(if __name__\b|\w+\s*=\s*singleton\()")
CODE_STATEMENTS = (
    ast.Assign, ast.AugAssign, ast.Import, ast.ImportFrom, ast.Return,
    ast.FunctionDef, ast.ClassDef, ast.For, ast.While, ast.If, ast.With, ast.Try,
)


def first_line(node):
    """The node's first line, counting decorators."""
    decorators = getattr(node, "decorator_list", [])
    return decorators[0].lineno if decorators else node.lineno


def join_limited(items):
    shown = ", ".join(items[:MAX_NAMES_PER_LINE])
    extra = len(items) - MAX_NAMES_PER_LINE
    return f"{shown}, and {extra} more" if extra > 0 else shown


def documented_functions(tree):
    """Yield top-level functions and class methods, skipping __dunder__ methods."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and not member.name.startswith("__"):
                    yield member


def string_note_lines(tree):
    """Last lines of bare strings, which some students put above a function as its docs."""
    return {
        node.end_lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }


def undocumented(tree, comment_lines):
    names = []
    comment_lines = comment_lines | string_note_lines(tree)
    for node in documented_functions(tree):
        has_comment = any(line in comment_lines for line in range(first_line(node) - 1, node.end_lineno + 1))
        if not ast.get_docstring(node) and not has_comment and node.name not in STARTER_FUNCTIONS:
            names.append(node.name)
    return names


def camel_case_names(tree):
    """Return {name: first line} for names the student defined. Classes are exempt."""
    found = {}

    def add(name, line):
        if CAMEL_CASE.search(name):
            found.setdefault(name, line)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add(node.name, node.lineno)
        elif isinstance(node, ast.arg):
            add(node.arg, node.lineno)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            add(node.id, node.lineno)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Store)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
        ):
            add(node.attr, node.lineno)
    return found


def looks_like_code(comment):
    text = comment.lstrip("#").strip()
    if not text:
        return False
    try:
        body = ast.parse(text).body
    except (SyntaxError, ValueError):
        return False
    if len(body) != 1:
        return False
    statement = body[0]
    return isinstance(statement, CODE_STATEMENTS) or (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
    )


def line_ranges(numbers):
    """Turn sorted line numbers into text such as 'lines 3-5, line 9'."""
    groups = []
    for number in numbers:
        if groups and number == groups[-1][1] + 1:
            groups[-1][1] = number
        else:
            groups.append([number, number])
    return [f"line {a}" if a == b else f"lines {a}-{b}" for a, b in groups]


def before_starter_block(lines, index):
    """True when only comments separate this blank line from a starter-code block."""
    for text in lines[index:]:
        stripped = text.strip()
        if stripped and not stripped.startswith("#"):
            return bool(STARTER_BLOCK.match(text))
    return False


def commented_out_lines(tokens, lines):
    full_line_comments = [
        t.start[0] for t in tokens
        if t.type == tokenize.COMMENT and not t.line[:t.start[1]].strip()
    ]
    return [n for n in full_line_comments if looks_like_code(lines[n - 1])]


def multiline_string_lines(tokens):
    """Lines inside multi-line strings, such as SQL, which are not code spacing."""
    string_lines = set()
    for token in tokens:
        if token.start[0] != token.end[0]:
            string_lines.update(range(token.start[0], token.end[0] + 1))
    return string_lines


def long_lines(lines, string_lines):
    return [
        n for n, text in enumerate(lines, 1)
        if len(text) > MAX_LINE_LENGTH and n not in string_lines
    ]


def extra_blank_runs(lines, string_lines):
    """First line of each run of too many blank lines."""
    starts = []
    run = 0
    for n, text in enumerate(lines, 1):
        run = run + 1 if not text.strip() and n not in string_lines else 0
        if run == MAX_BLANK_LINES + 1 and not before_starter_block(lines, n):
            starts.append(n - MAX_BLANK_LINES)
    return starts


def crowded_definitions(tree, lines, comment_lines):
    """Top-level definitions with code directly above them."""
    notes = comment_lines | string_note_lines(tree)
    crowded = []
    for index, node in enumerate(tree.body):
        start = first_line(node)
        is_definition = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        if is_definition and index and lines[start - 2].strip() and start - 1 not in notes:
            crowded.append(f"{node.name} (line {start})")
    return crowded
