"""Unscored style feedback."""
import unittest

from fixture_apps import pa1_app
from helpers import GraderTestCase, submission


class StyleTests(GraderTestCase):
    def test_style_feedback(self):
        messy = pa1_app() + (
            "\n\n\n\n"
            "def noDocs(userName):\n"
            "    resultValue = userName\n"
            "    return resultValue\n"
            "# x = 1\n"
            "# print(x)\n"
            "# Get all users\n"
            "# Note: this is prose\n"
            "# return the user\n"
            "def has_docstring():\n"
            '    """Docs."""\n'
            '    return """\n\n\n\nSQL\n"""\n\n'
            "class MyClass:\n"
            "    def __init__(self):\n"
            "        self.camelAttr = 1\n\n"
            "    def method_with_comment(self):\n"
            "        # A comment counts.\n"
            "        return 1\n\n"
            '"""A note above the function."""\n'
            "def string_above():\n"
            "    return 1\n\n"
            "CONSTANT_VALUE = 1\n"
            "long_line = '" + "x" * 130 + "'\n"
        )
        self.student_zip("messy", submission(messy, extra={
            "proj/helper.py": "def fine_helper():\n    # ok\n    return 1\n",
            "proj/pa1_test.py": "def badTestName(): pass\n",
            "proj/other_test.py": "def badOtherName(): pass\n",
            "proj/broken.py": "def (:\n",
        }))
        self.grade("--no-extra")
        sheet = self.sheet("messy")
        self.assert_header(sheet, "0", "0", "10")
        style = sheet.split("Style feedback (no points lost):\n")[1]
        self.assertIn("app.py: add a comment or docstring to", style)
        self.assertIn("noDocs", style)
        for name in ("userName", "resultValue", "camelAttr"):
            self.assertIn(name, style)
        self.assertNotIn("MyClass (", style)
        self.assertNotIn("CONSTANT_VALUE", style)
        self.assertNotIn("has_docstring", style)
        self.assertNotIn("method_with_comment", style)
        self.assertNotIn("string_above", style)
        self.assertRegex(style, r"app\.py: remove commented-out code at lines \d+-\d+\.")
        self.assertNotRegex(style, r"commented-out code at .*,")
        self.assertIn("shorten lines over 120", style)
        self.assertIn("use at most 2 blank lines in a row near line", style)
        self.assertEqual(style.count("use at most 2 blank lines"), 1)
        self.assertIn("broken.py: could not be read", style)
        self.assertNotIn("badTestName", style)
        self.assertNotIn("badOtherName", style)
        self.assertNotIn("helper.py", style)

    def test_starter_code_and_venv_are_not_flagged(self):
        app = (
            "import flask\n\n"
            "app = flask.Flask(__name__)\n\n"
            "def hello_world():\n    return 'starter code'\n\n\n\n"
            "# Starter block below\n"
            "if __name__ == '__main__':\n    app.run()\n"
        )
        self.student_zip("clean", submission(app, extra={
            "proj/db.py": (
                "def singleton(cls):\n    return cls\n\n"
                "class DatabaseDriver:\n    pass\n\n\n\n"
                "DatabaseDriver = singleton(DatabaseDriver)\n"
            ),
            "proj/venv/bad.py": "def camelName(): pass\n",
        }))
        self.grade("--no-extra")
        sheet = self.sheet("clean")
        self.assertNotIn("Style feedback", sheet)
        self.assertNotIn("camelName", sheet)


if __name__ == "__main__":
    unittest.main()
