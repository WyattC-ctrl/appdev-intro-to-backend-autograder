"""Behavior of the real PA test files against sample student apps."""
import unittest

from fixture_apps import ALL_CHALLENGE, PA2_APP, pa1_app
from helpers import PA2, GraderTestCase, submission


class Pa1Tests(GraderTestCase):
    def test_link_validators_and_default_upvote(self):
        self.student_zip("strict", submission(pa1_app(challenge=ALL_CHALLENGE | {"strict_url"})))
        self.student_zip("loose", submission(pa1_app(challenge=ALL_CHALLENGE | {"loose_url"})))
        self.student_zip("bare", submission(pa1_app(challenge=ALL_CHALLENGE | {"bare_domain_only"})))
        self.student_zip("nodefault", submission(pa1_app(challenge=ALL_CHALLENGE | {"no_default"})))
        self.grade()
        self.assert_header(self.sheet("strict"), "0", "+2", "12")
        self.assert_header(self.sheet("loose"), "0", "+2", "12")
        bare = self.sheet("bare")
        self.assertIn("Core tests: all 10 passed", bare)
        self.assertIn("Tier 1: +0, not earned (0 of 3 tests passed)\n", bare)
        nodefault = self.sheet("nodefault")
        self.assert_header(nodefault, "0", "+1", "11")
        self.assertIn(
            "Tier 2: +0, not earned (2 of 3 tests passed). Failed:\n"
            "- test_extra_upvote_default: POST request to route '/api/extra/posts/",
            nodefault,
        )


class Pa2Tests(GraderTestCase):
    def test_hashed_password_earns_tier(self):
        # The app stores a hash and never returns the password.
        self.student_zip("hash", submission(PA2_APP))
        self.grade(test=PA2)
        sheet = self.sheet("hash")
        self.assert_header(sheet, "0", "+1", "11")
        self.assertIn("Challenges (extra credit): +1 received\nTier 1: +1, earned (5 of 5 tests passed)", sheet)

    def test_no_password_must_be_rejected(self):
        app = PA2_APP.replace('if keep_password and body.get("password") is None:', "if False:")
        self.assertNotEqual(app, PA2_APP)
        self.student_zip("open", submission(app))
        self.grade(test=PA2)
        sheet = self.sheet("open")
        self.assert_header(sheet, "0", "0", "10")
        self.assertIn("test_extra_create_user", sheet)


if __name__ == "__main__":
    unittest.main()
