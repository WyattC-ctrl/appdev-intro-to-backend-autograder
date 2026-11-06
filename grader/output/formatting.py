"""Small text helpers shared by the output code."""


def number(value):
    """Print whole numbers without ".0"."""
    return str(int(value)) if float(value).is_integer() else str(value)
