"""PA5, which runs each submission with Docker Compose.

The checks of the PA5 test file and the Docker helpers need no Docker. The
end-to-end test builds a small image and runs it, so it only runs when
RUN_DOCKER_TESTS=1 is set and Docker is running.
"""
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from grader.running.docker import PROJECT, docker_available, published_port, unsafe_setting
from helpers import ASSIGNMENT_TESTS, POSTMAN, GraderTestCase, filled_readme, write_zip

PA5 = ASSIGNMENT_TESTS / "pa5_test.py"
IMAGE = "flask-grader-test/pa5:latest"

PA5_APP = '''import json
from flask import Flask

app = Flask(__name__)


@app.route("/api/courses/")
def get_courses():
    return json.dumps({"courses": []}), 200
'''
DOCKERFILE = "FROM python:3.11-slim\nWORKDIR /usr/app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD sh start_server.sh\n"
START_SERVER = "gunicorn -w 4 -b 0.0.0.0:5000 app:app\n"
COMPOSE = f'services:\n  web:\n    image: {IMAGE}\n    ports:\n      - "5000:5000"\n'


def load_pa5():
    spec = importlib.util.spec_from_file_location("pa5_checks", PA5)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Pa5CheckTests(unittest.TestCase):
    """The rules inside pa5_test.py."""

    @classmethod
    def setUpClass(cls):
        cls.pa5 = load_pa5()

    def in_folder(self, files):
        """Write these files to a temp src folder and work from it, as the grader does."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for name, content in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(content)
        previous = os.getcwd()
        os.chdir(root / "src")
        self.addCleanup(os.chdir, previous)

    def test_basic_python_image(self):
        for image in ("python", "python:3.9", "python:latest", "python:3.11-bookworm", "docker.io/library/python:3.10.4"):
            self.assertTrue(self.pa5.is_basic_python(image), image)
        for image in ("python:3.11-slim", "python:3.12-alpine", "python:3.11-slim-bookworm", "pypy:3", "continuumio/miniconda3"):
            self.assertFalse(self.pa5.is_basic_python(image), image)

    def test_docker_hub_image_names(self):
        for image in ("abc123/pa5", "abc123/pa5:latest", "docker.io/abc123/pa5", "abc-123/my_app.v2:1.0"):
            self.assertTrue(self.pa5.HUB_IMAGE.fullmatch(image), image)
        for image in ("pa5", "pa5:latest", "localhost:5000/pa5", "ghcr.io/pa5", "ghcr.io/abc/pa5"):
            self.assertFalse(self.pa5.HUB_IMAGE.fullmatch(image), image)

    def test_base_image_is_the_final_stage(self):
        self.in_folder({"src/Dockerfile": (
            "ARG VERSION=3.11-slim\n"
            "FROM python:3.9 AS build\n"
            "RUN pip wheel .\n"
            "FROM --platform=linux/amd64 python:${VERSION}\n"
        )})
        self.assertEqual(self.pa5.base_image("Dockerfile"), "python:3.11-slim")

    def test_readme_routes(self):
        self.in_folder({"README.txt": (
            "Working endpoint: GET http://localhost:5000/api/users/<user_id>/\n"
            "POST /api/courses/ needs a body.\n"
            "Also try `/api/courses/{id}/`.\n"
        ), "src/app.py": ""})
        self.assertEqual(self.pa5.readme_routes(), ["/api/users/1/", "/api/courses/1/"])

    def test_requirements_names(self):
        self.in_folder({"src/requirements.txt": "Flask==3.0.0\ngunicorn>=21\nflask_sqlalchemy\n"})
        self.assertTrue(self.pa5.lists_package("requirements.txt", "flask"))
        self.assertTrue(self.pa5.lists_package("requirements.txt", "gunicorn"))
        self.assertTrue(self.pa5.lists_package("requirements.txt", "flask-sqlalchemy"))
        self.assertFalse(self.pa5.lists_package("requirements.txt", "requests"))


class DockerHelperTests(unittest.TestCase):
    def test_published_port_prefers_the_hub_image(self):
        config = {"services": {
            "db": {"image": "postgres", "ports": [{"target": 5432, "published": "5432"}]},
            "web": {"image": "abc123/pa5", "ports": [{"target": 5000, "published": "8000"}]},
        }}
        self.assertEqual(published_port(config), 8000)
        self.assertIsNone(published_port({"services": {"web": {"image": "abc123/pa5"}}}))

    def test_unsafe_settings(self):
        root = "/tmp/submission"
        inside = {"type": "bind", "source": "/tmp/submission/src"}
        outside = {"type": "bind", "source": "/Users"}
        self.assertIsNone(unsafe_setting({"services": {"web": {"volumes": [inside]}}}, root))
        self.assertIn("outside the submission", unsafe_setting({"services": {"web": {"volumes": [outside]}}}, root))
        self.assertIn("privileged", unsafe_setting({"services": {"web": {"privileged": True}}}, root))
        self.assertIn("network_mode: host", unsafe_setting({"services": {"web": {"network_mode": "host"}}}, root))


class Pa5CommandTests(GraderTestCase):
    def test_list_tests(self):
        listing = self.list_tests(PA5)
        self.assertIn("Core tests: 8", listing)
        self.assertIn("Container works (4 points)", listing)
        self.assertIn("Extra-credit tests: 5", listing)
        self.assertIn("Warnings: 0", listing)

    def test_needs_docker(self):
        self.student_zip("abc123", {"pa5/src/app.py": PA5_APP})
        result = self.run_grade(
            self.students, "--test", PA5, "--out", self.out, env=dict(os.environ, PATH="/usr/bin:/bin"),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pa5_test.py needs Docker. Start Docker Desktop", result.stderr)
        self.assertFalse(self.out.exists())


@unittest.skipUnless(os.environ.get("RUN_DOCKER_TESTS") == "1", "set RUN_DOCKER_TESTS=1 to run tests that use Docker")
class Pa5DockerTests(GraderTestCase):
    def setUp(self):
        super().setUp()
        if not docker_available():
            self.skipTest("Docker is not running")
        source = self.tmp / "image"
        files = {"app.py": PA5_APP, "requirements.txt": "flask\ngunicorn\n",
                 "start_server.sh": START_SERVER, "Dockerfile": DOCKERFILE}
        source.mkdir()
        for name, content in files.items():
            (source / name).write_text(content)
        subprocess.run(["docker", "build", "-q", "-t", IMAGE, str(source)], check=True, capture_output=True)
        self.addCleanup(subprocess.run, ["docker", "image", "rm", "-f", IMAGE], capture_output=True)
        self.files = {f"pa5/src/{name}": content for name, content in files.items()}
        self.files.update({"pa5/src/docker-compose.yml": COMPOSE, "pa5/README.txt": filled_readme(load_pa5(), {"Working Endpoint": "GET /api/courses/"}),
                           "pa5/postman_collection.json": POSTMAN})

    def containers_left(self):
        result = subprocess.run(
            ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}"],
            capture_output=True, text=True,
        )
        return result.stdout.split()

    def test_full_submission(self):
        self.student_zip("abc123", self.files)
        self.grade(test=PA5)
        sheet = self.sheet("abc123")
        self.assert_header(sheet, "0", "+3", "13")
        self.assertIn("Points lost: none", sheet)
        self.assertIn("Container works 4/4\n  +2  Container starts\n  +2  Route returns JSON\n", sheet)
        self.assertEqual(self.containers_left(), [])

    def test_missing_image(self):
        self.files["pa5/src/docker-compose.yml"] = COMPOSE.replace(IMAGE, "flask-grader-test/missing-image")
        self.student_zip("abc123", self.files)
        self.grade(test=PA5)
        sheet = self.sheet("abc123")
        self.assert_header(sheet, "-4", "0", "6")
        self.assertIn("-2  The container did not start with docker compose up -d\n    docker compose up -d failed:", sheet)
        self.assertIn("Container works 0/4\n  +0  Container starts (worth 2)\n", sheet)
        self.assertIn("Challenges (extra credit): +0, not given because the container did not run", sheet)
        self.assertEqual(self.containers_left(), [])


if __name__ == "__main__":
    unittest.main()
