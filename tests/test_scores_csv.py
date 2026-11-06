"""The scores CSV uploaded to CMS."""
import unittest

from fixture_apps import ALL_CHALLENGE, pa1_app
from fixture_test_files import TWENTY_FIVE_FAILING
from helpers import GraderTestCase, submission


class ScoresCsvTests(GraderTestCase):
    def test_rows_scores_and_comments(self):
        s = self.students
        (s / "empty").mkdir()
        (s / "broken").mkdir()
        (s / "broken" / "bad.zip").write_bytes(b"not a zip")
        self.student_zip("half", submission(pa1_app(broken={"get_posts", "edit"})))
        self.student_zip("noapp", {"README": "x"})
        self.student_zip("top", submission(pa1_app(challenge=ALL_CHALLENGE)))
        self.grade()
        self.assertEqual(
            (self.out / "PA1" / "CS_1998_S603_PA1_scores.csv").read_bytes().decode(),
            "NetID,PA1 - Reddit,Total,Adjustments,Add Comments\n"
            "broken,0.0,0.0,,\n"
            "empty,0.0,0.0,,No submission\n"
            "half,8.5,8.5,,\n"
            "noapp,0.0,0.0,,\n"
            "top,12.0,12.0,,\n",
        )

    def test_column_option_and_unknown_column_warning(self):
        (self.students / "stu").mkdir()
        test_file = self.write_test_file("pa9_test.py", TWENTY_FIVE_FAILING)
        out = self.grade("--column", "Custom, Name", test=test_file)
        self.assertIn('NetID,"Custom, Name",Total', (self.out / "PA9" / "CS_1998_S603_PA9_scores.csv").read_text())
        self.assertNotIn("no known CMS column", out)
        out = self.grade(test=test_file)
        self.assertIn("no known CMS column name for PA9", out)


if __name__ == "__main__":
    unittest.main()
