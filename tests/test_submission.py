"""Finding the zip and checking what is inside it."""
import json
import unittest

from fixture_apps import pa1_app
from helpers import POSTMAN, GraderTestCase, submission, write_zip


class SubmissionTests(GraderTestCase):
    def test_no_zip(self):
        (self.students / "d").mkdir()
        self.grade()
        sheet = self.sheet("d")
        self.assert_header(sheet, "-12", "0", "0")
        self.assertIn("-10  No app.py was found, so nothing could be graded\n-1   No README file\n", sheet)
        self.assertIn("Challenges (extra credit): +0, not checked because no app.py was found", sheet)
        self.assertIn("No zip file was found in this student's folder.", sheet)
        self.assertNotIn("Style feedback", sheet)
        self.assertNotIn("core tests", sheet)

    def test_corrupt_zip(self):
        (self.students / "corrupt").mkdir()
        (self.students / "corrupt" / "bad.zip").write_bytes(b"not a zip")
        self.grade()
        sheet = self.sheet("corrupt")
        self.assertIn("Could not open bad.zip; it is not a valid zip.", sheet)
        self.assert_header(sheet, "-12", "0", "0")

    def test_largest_of_two_zips_is_graded(self):
        write_zip(self.students / "two" / "small.zip", {"x": "y"})
        write_zip(self.students / "two" / "big.zip", submission(pa1_app()))
        self.grade("--no-extra")
        sheet = self.sheet("two")
        self.assertIn("graded the largest, big.zip", sheet)
        self.assert_header(sheet, "0", "0", "10")

    def test_mac_files_are_ignored(self):
        s = self.students
        write_zip(s / "mac" / "sub.zip", submission(pa1_app(), extra={"__MACOSX/._app.py": "x", "proj/._x.db": "x"}))
        write_zip(s / "mac" / "__MACOSX" / "ignored_big.zip", {"x": "y" * 100000})
        (s / "mac" / "._sub.zip").write_bytes(b"junk")
        self.grade("--no-extra")
        self.assert_header(self.sheet("mac"), "0", "0", "10")

    def test_zip_inside_a_zip(self):
        inner = self.tmp / "inner.zip"
        write_zip(inner, submission(pa1_app(), postman=False))
        write_zip(self.students / "c" / "outer.zip", {"inner.zip": inner.read_bytes()})
        self.grade()
        self.assert_header(self.sheet("c"), "-1", "0", "9")

    def test_three_levels_of_nested_zips(self):
        level = {"app.py": pa1_app(), "README": "x", "postman_collection.json": POSTMAN}
        for depth in range(3):
            path = self.tmp / f"level{depth}.zip"
            write_zip(path, level)
            level = {"next.zip": path.read_bytes()}
        self.student_zip("nested3", level)
        self.grade("--no-extra")
        self.assert_header(self.sheet("nested3"), "0", "0", "10")

    def test_nested_zip_named_venv_is_not_a_venv(self):
        inner = self.tmp / "venv.zip"
        write_zip(inner, {"notes.txt": "x"})
        self.student_zip("venvzip", submission(pa1_app(), extra={"proj/venv.zip": inner.read_bytes()}))
        self.grade("--no-extra")
        self.assert_header(self.sheet("venvzip"), "0", "0", "10")

    def test_app_and_readme_in_a_venv_do_not_count(self):
        self.student_zip("venvapp", {"venv/app.py": "x", "venv/README": "x", "postman_collection.json": POSTMAN})
        self.grade("--no-extra")
        sheet = self.sheet("venvapp")
        self.assertIn("No app.py was found", sheet)
        self.assertIn("Included files that should not be submitted (venv, .db, __pycache__, or the test file)", sheet)
        self.assertIn("No README file", sheet)
        self.assert_header(sheet, "-12", "0", "0")

    def test_shallowest_app_is_used(self):
        self.student_zip("depth", submission(pa1_app(), extra={"proj/deep/app.py": "raise RuntimeError('deep')"}))
        self.grade("--no-extra")
        self.assert_header(self.sheet("depth"), "0", "0", "10")

    def test_app_in_src_beats_a_shallower_copy(self):
        files = submission("raise RuntimeError('stray copy')")
        files["proj/src/app.py"] = pa1_app()
        self.student_zip("stray", files)
        self.grade("--no-extra")
        self.assert_header(self.sheet("stray"), "0", "0", "10")

    def test_test_file_in_zip_costs_a_point(self):
        self.student_zip("b", submission(pa1_app(), extra={"proj/pa1_test.py": "x"}))
        self.grade()
        sheet = self.sheet("b")
        self.assert_header(sheet, "-1", "0", "9")
        self.assertIn("Points lost:\n-1  Included files that should not be submitted (venv, .db, __pycache__, or the test file)\n", sheet)
        self.assertNotIn("Notes:", sheet)

    def test_test_file_and_venv_cost_one_point_together(self):
        self.student_zip("both", submission(pa1_app(), extra={"proj/pa1_test.py": "x", "venv/pyvenv.cfg": "x"}))
        self.grade()
        sheet = self.sheet("both")
        self.assert_header(sheet, "-1", "0", "9")
        self.assertEqual(sheet.count("should not be submitted"), 1)

    def test_json_that_is_not_a_collection(self):
        self.student_zip("notpostman", {"app.py": pa1_app(), "README": "x", "postman_collection.json": '{"info": {}, "item": []}'})
        self.grade("--no-extra")
        self.assertIn("-1  No exported Postman collection (.json)", self.sheet("notpostman"))

    def test_postman_schema_without_id_counts(self):
        def collection(info):
            return json.dumps({"info": info, "item": []})
        good = collection({"name": "x", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"})
        other = collection({"name": "x", "schema": "https://example.com/schema.json"})
        no_item = json.dumps({"info": {"_postman_id": "abc"}})
        for name, text in (("good", good), ("other", other), ("noitem", no_item)):
            self.student_zip(name, submission(pa1_app(), postman=False, extra={"proj/postman_collection.json": text}))
        self.student_zip("anyname", submission(pa1_app(), postman=False, extra={"proj/My Tests.postman_collection.json": POSTMAN}))
        self.student_zip("both", submission(pa1_app(), extra={"proj/Tests/Get Posts.request.yaml": "x"}))
        self.student_zip("workspace", submission(pa1_app(), extra={"proj/postman/collections/x.yaml": "x"}))
        self.student_zip("json_in_folder", submission(pa1_app(), postman=False, extra={"proj/postman/c.json": POSTMAN}))
        self.student_zip("folder", submission(pa1_app(), postman=False, extra={
            "proj/Tests/.resources/definition.yaml": "$kind: collection\n",
            "proj/Tests/Get Posts.request.yaml": "$kind: http-request\n",
        }))
        self.grade("--no-extra")
        self.assert_header(self.sheet("good"), "0", "0", "10")
        self.assert_header(self.sheet("anyname"), "0", "0", "10")
        self.assert_header(self.sheet("folder"), "-1", "0", "9")
        self.assertIn("-1  Included a Postman folder", self.sheet("folder"))
        self.assert_header(self.sheet("both"), "-1", "0", "9")
        self.assertIn("-1  Included a Postman folder", self.sheet("both"))
        self.assert_header(self.sheet("workspace"), "-1", "0", "9")
        self.assert_header(self.sheet("json_in_folder"), "0", "0", "10")
        self.assertIn("-1  No exported Postman collection (.json)", self.sheet("other"))
        self.assertIn("-1  No exported Postman collection (.json)", self.sheet("noitem"))


if __name__ == "__main__":
    unittest.main()
