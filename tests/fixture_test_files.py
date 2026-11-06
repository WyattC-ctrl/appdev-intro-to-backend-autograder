"""Small test files, for cases the real assignment tests do not cover."""

# A test file with 25 failing core tests and no extra credit.
TWENTY_FIVE_FAILING = (
    "import unittest\nfrom app import app\nEXTRA_CREDIT = False\nTIERS = {}\n"
    "class TestRoutes(unittest.TestCase):\n"
    + "".join(f"    def test_{i}(self):\n        self.fail('no')\n" for i in range(25))
)


# Each extra test passes when the app sets the matching config value.
BONUS_TEST_FILE = """import unittest
from app import app
EXTRA_CREDIT = False
TIERS = {1: ["test_extra_a"], 2: ["test_extra_b"]}
TIER_BONUS = {2: 1}
class TestRoutes(unittest.TestCase):
    def test_core(self):
        pass
    def test_extra_a(self):
        if not EXTRA_CREDIT:
            return
        self.assertTrue(app.config.get("A"))
    def test_extra_b(self):
        if not EXTRA_CREDIT:
            return
        self.assertTrue(app.config.get("B"))
"""

# One failure of each kind, to check the reasons on the sheet.
REASON_TEST_FILE = """import unittest
from app import app
EXTRA_CREDIT = False
TIERS = {}
class TestRoutes(unittest.TestCase):
    def test_a_status(self):
        self.assertEqual(500, 201, "\\033[91m\\nGET request to route '/x/' returned a status code of 500, but 201 was expected.\\033[0m")
    def test_b_no_message(self):
        self.assertEqual(1, 2)
    def test_c_crash(self):
        raise KeyError("id")
    def test_d_hints(self):
        self.fail("\\nPOST request to route '/y/' did not return a JSON response.    \\nAre you sure?\\n\\nRequest Body:\\n{}")
    def test_e_long(self):
        self.fail("z" * 500)
    def test_f_pass(self):
        pass
"""
