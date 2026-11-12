"""Finding blank fields and questions in a README template."""
import shutil
import tempfile
import unittest
from pathlib import Path

from grader.submissions.readme import blank_answers, find_readme
from helpers import ASSIGNMENT_TESTS, POSTMAN, GraderTestCase

FIELDS = ["Name", "NetID", "Working Endpoint", "Your Server Address"]
QUESTIONS = ["What are environment variables?", "Explain the concept of clustering in your own words."]
TEMPLATE = """Name: 
NetID: 

Working Endpoint: <Put a working endpoint from PA 4 here (e.g. GET /api/courses/)>
Your Server Address: 

Questions:
What are environment variables?
<Your answer here>

Explain the concept of clustering in your own words.
<Your answer here>
"""


class BlankAnswerTests(unittest.TestCase):
    def blanks(self, text):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "README.txt").write_text(text)
        return blank_answers(root / "README.txt", FIELDS, QUESTIONS)

    def test_untouched_template_is_all_blank(self):
        self.assertEqual(self.blanks(TEMPLATE), [*FIELDS, *[f'"{q}"' for q in QUESTIONS]])

    def test_filled_in(self):
        text = (TEMPLATE.replace("Name: ", "Name: Ada").replace("NetID: ", "NetID: abc123")
                .replace("<Put a working endpoint from PA 4 here (e.g. GET /api/courses/)>", "GET /api/courses/")
                .replace("Your Server Address: \n", "Your Server Address:\n34.1.2.3\n")
                .replace("<Your answer here>", "Values set outside the code.", 1)
                .replace("in your own words.\n<Your answer here>", "in your own words. Many servers as one."))
        self.assertEqual(self.blanks(text), [])

    def test_removed_question_counts_as_blank(self):
        text = TEMPLATE.replace("Explain the concept of clustering in your own words.\n", "")
        self.assertIn('"Explain the concept of clustering in your own words."', self.blanks(text))

    def test_prefers_readme_txt(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "src").mkdir()
        (root / "README.md").write_text("")
        (root / "README.txt").write_text("")
        self.assertEqual(find_readme(root / "src").name, "README.txt")


class ReadmeSheetTests(GraderTestCase):
    def test_each_blank_costs_half_a_point(self):
        readme = TEMPLATE.replace("Name: ", "Name: Ada").replace("NetID: ", "NetID: abc123")
        self.student_zip("abc123", {
            "pa6/src/app.py": "", "pa6/README.txt": readme, "pa6/postman_collection.json": POSTMAN,
        })
        self.grade(test=ASSIGNMENT_TESTS / "pa6_test.py")
        sheet = self.sheet("abc123")
        self.assertIn(
            "-4  README has 8 blank answers\n"
            '    Blank: Working Endpoint, Your Server Address, "Explain the concept of deployment in your own words.", '
            '"What are environment variables?"',
            sheet,
        )
