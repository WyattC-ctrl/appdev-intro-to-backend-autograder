"""PA5 (Containerization) tests.

The grader starts the submission with `docker compose up -d` before these tests
run and removes the containers afterward, so this file does not import app.py.

To run it by hand, start the containers from the submission's src folder, then
run this file from that folder:

    docker compose up -d
    python3 pa5_test.py --extra
    docker compose down
"""
import os
import re
import sys
import unittest

import requests

# Flag to run extra credit tests (if applicable)
EXTRA_CREDIT = False

# The grader runs the app with docker compose instead of importing app.py.
DOCKER = True

# Extra-credit tiers. Each tier is +1.
TIERS = {
    1: ["test_extra_python_distribution"],
    2: ["test_extra_gunicorn_requirement", "test_extra_start_server_script", "test_extra_dockerfile_runs_script", "test_extra_gunicorn_serves_app"],
}
TIER_BONUS = {2: 1}  # Tier II is worth +1 more when Tier I is also earned.

# Each core test is worth its own points, out of 10: (test, points, rubric line, line when lost).
RUBRIC = [
    ("Dockerfile", [
        ("test_dockerfile_in_src", 1, "Dockerfile is in src/", "No Dockerfile in src/"),
        ("test_dockerfile_installs_requirements", 1, "Installs requirements.txt", "The Dockerfile does not install requirements.txt"),
        ("test_dockerfile_starts_app", 1, "CMD starts the app", "The Dockerfile has no CMD that starts the app"),
    ]),
    ("docker-compose.yml", [
        ("test_compose_in_src", 1, "docker-compose.yml is in src/", "No docker-compose.yml in src/"),
        ("test_compose_uses_docker_hub_image", 1, "Uses a Docker Hub image (username/repo)", "docker-compose.yml does not use a Docker Hub image named username/repo"),
        ("test_compose_publishes_port", 1, "Publishes a port", "docker-compose.yml does not publish a port"),
    ]),
    ("Container works", [
        ("test_container_starts", 2, "Container starts", "The container did not start with docker compose up -d"),
        ("test_route_returns_json", 2, "Route returns JSON", "No route returned JSON"),
    ]),
]
# The README template's fields and questions. Each one left blank is -0.5.
# "Challenges Attempted" is left out: a student who tried none may leave it blank.
README_FIELDS = ["Name", "NetID", "Working Endpoint", "Your Docker Hub Repository Link"]
README_QUESTIONS = [
    "Explain the concept of containerization in your own words.",
    "What is the difference between a Docker image and a Docker container?",
    "What is the command to list all Docker images?",
    "What is the command to list all Docker containers?",
    "What is a Docker tag and what is it used for?",
    "What is Docker Hub and what is it used for?",
    "What is Docker compose used for?",
    "What is the difference between the RUN and CMD commands?",
]

# Extra credit only counts when the container runs.
EXTRA_CREDIT_NEEDS = ("test_container_starts", "the container did not run")

# The grader sets these for the port in the student's docker-compose.yml.
LOCAL_URL = os.environ.get("GRADER_URL", "http://localhost:5000")
DOCKER_PROBLEM = os.environ.get("GRADER_DOCKER_ERROR", "")

# Tried when the README names no GET route. Every PA4 app has it.
DEFAULT_ROUTE = "/api/courses/"
COMPOSE_NAMES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
# The handout's "basic version": python, python:3.11, python:latest, python:3.11-bookworm, ...
DEBIAN_RELEASES = {"bookworm", "bullseye", "buster", "stretch", "jessie", "trixie"}
# <username>/<repository>[:tag]. A username has no dots, so ghcr.io/repo is not Docker Hub.
HUB_IMAGE = re.compile(r"(?:docker\.io/)?[a-z0-9]+(?:[_-][a-z0-9]+)*/[a-z0-9]+(?:[._-][a-z0-9]+)*(?::[\w][\w.-]*)?")


# Finding the student's files. The handout puts them in src, next to app.py.
def find_file(*names, folders=(".", "..")):
    """Return the path of the first file with one of these names, ignoring case."""
    wanted = [name.lower() for name in names]
    for folder in folders:
        try:
            entries = {entry.lower(): entry for entry in os.listdir(folder)}
        except OSError:
            continue
        for name in wanted:
            if name in entries and os.path.isfile(os.path.join(folder, entries[name])):
                return os.path.join(folder, entries[name])
    return None


def find_readme():
    for folder in (".", ".."):
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in names:
            if name.lower().startswith("readme") and os.path.isfile(os.path.join(folder, name)):
                return os.path.join(folder, name)
    return None


def read(path):
    with open(path, errors="replace") as source:
        return source.read()


def lists_package(requirements_path, package):
    for line in read(requirements_path).splitlines():
        name = re.split(r"[\s<>=!~\[;@]", line.strip(), maxsplit=1)[0]
        if name.lower().replace("_", "-") == package:
            return True
    return False


# Reading the Dockerfile and docker-compose.yml.
def dockerfile_lines(path):
    """The Dockerfile's instructions, with continued lines joined and comments removed."""
    text = re.sub(r"\\\s*\n", " ", read(path))
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


def base_image(path):
    """The image the final stage of the Dockerfile is built from."""
    args, stages, image = {}, {}, None
    for line in dockerfile_lines(path):
        parts = line.split()
        instruction = parts[0].upper()
        if instruction == "ARG" and len(parts) > 1 and "=" in parts[1]:
            key, value = parts[1].split("=", 1)
            args.setdefault(key, value.strip("'\""))
        elif instruction == "FROM":
            words = [word for word in parts[1:] if not word.startswith("--")]
            if not words:
                continue
            image = re.sub(r"\$\{?(\w+)\}?", lambda match: args.get(match.group(1), match.group(0)), words[0])
            image = stages.get(image.lower(), image)
            if len(words) >= 3 and words[1].lower() == "as":
                stages[words[2].lower()] = image
    return image


def is_basic_python(image):
    name = image.split("@")[0]
    for prefix in ("docker.io/", "library/"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    name, _, tag = name.partition(":")
    if name != "python":
        return False
    variant = re.sub(r"^\d+(\.\d+)*-?", "", tag)
    return variant in ("", "latest") or variant in DEBIAN_RELEASES


def compose_images(path):
    return re.findall(r"^\s*image\s*:\s*[\"']?([^\"'\s#]+)", read(path), re.MULTILINE)


# Calling the app in the student's container.
def readme_routes():
    """GET routes named in the README, with placeholders such as <id> filled in with 1."""
    path = find_readme()
    if path is None:
        return []
    routes = []
    for match in re.finditer(r"(?:\b([A-Za-z]+)\s+)?(?:https?://[^/\s]+)?(/api/\S*)", read(path)):
        method = (match.group(1) or "GET").upper()
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            continue
        route = re.sub(r"<[^>]*>|\{[^}]*\}|(?<=/):\w+", "1", match.group(2))
        route = route.rstrip(".,;:!?)]}'\"`*")
        if route not in routes:
            routes.append(route)
    return routes


def call_routes():
    """Return (first working response, description of every attempt)."""
    attempts = []
    routes = readme_routes()
    for route in routes + [DEFAULT_ROUTE] * (DEFAULT_ROUTE not in routes):
        try:
            res = requests.get(LOCAL_URL + route, timeout=10)
        except requests.RequestException as error:
            attempts.append(f"GET {route} could not connect ({type(error).__name__})")
            continue
        try:
            res.json()
            is_json = True
        except ValueError:
            is_json = False
        if is_json and res.status_code < 500:
            return res, attempts
        attempts.append(f"GET {route} returned {res.status_code}{'' if is_json else ' without JSON'}")
    return None, attempts


def app_problem(attempts):
    if DOCKER_PROBLEM:
        return "The container was not running, so no route could be called."
    return "No route returned a JSON response: " + "; ".join(attempts) + "."


def not_in_src(*names):
    if find_file(*names, folders=("..",)):
        return f"{names[0]} is in the folder above src/ instead."
    return f"There is no {names[0]} anywhere in the submission."


def instructions(path, *names):
    return [line for line in dockerfile_lines(path) if line.split()[0].upper() in names]


class TestRoutes(unittest.TestCase):
    def test_dockerfile_in_src(self):
        self.assertIsNotNone(find_file("Dockerfile", folders=(".",)), not_in_src("Dockerfile"))

    def test_dockerfile_installs_requirements(self):
        path = find_file("Dockerfile")
        self.assertIsNotNone(path, "No Dockerfile was found.")
        self.assertTrue(
            any(re.search(r"pip3?\s+install\b.*-r\s*\S*requirements", line) for line in instructions(path, "RUN")),
            "The Dockerfile has no RUN pip install -r requirements.txt line.",
        )

    def test_dockerfile_starts_app(self):
        path = find_file("Dockerfile")
        self.assertIsNotNone(path, "No Dockerfile was found.")
        self.assertTrue(instructions(path, "CMD", "ENTRYPOINT"), "The Dockerfile has no CMD or ENTRYPOINT line.")

    def test_compose_in_src(self):
        self.assertIsNotNone(find_file(*COMPOSE_NAMES, folders=(".",)), not_in_src(*COMPOSE_NAMES))

    def test_compose_uses_docker_hub_image(self):
        path = find_file(*COMPOSE_NAMES)
        self.assertIsNotNone(path, "No docker-compose.yml was found.")
        images = compose_images(path)
        self.assertTrue(
            any(HUB_IMAGE.fullmatch(image) for image in images),
            f"It uses {', '.join(images) if images else 'no image'}, not <username>/<repository>.",
        )

    def test_compose_publishes_port(self):
        path = find_file(*COMPOSE_NAMES)
        self.assertIsNotNone(path, "No docker-compose.yml was found.")
        self.assertRegex(read(path), r"(?m)^\s*ports\s*:\s*(\n\s*-\s*\S|\[\s*\S)", "It has no ports: entry.")

    def test_container_starts(self):
        self.assertFalse(DOCKER_PROBLEM, DOCKER_PROBLEM)
        try:
            requests.get(LOCAL_URL + "/", timeout=10)
        except requests.RequestException as error:
            self.fail(f"Nothing answered at {LOCAL_URL} ({type(error).__name__}).")

    def test_route_returns_json(self):
        res, attempts = call_routes()
        self.assertIsNotNone(res, app_problem(attempts))

    def test_extra_python_distribution(self):
        if not EXTRA_CREDIT:
            return
        path = find_file("Dockerfile")
        self.assertIsNotNone(path, "No Dockerfile was found in src.")
        image = base_image(path)
        self.assertIsNotNone(image, "The Dockerfile has no FROM line.")
        self.assertFalse(
            is_basic_python(image),
            f"The Dockerfile uses {image}, the basic Python image. Use another distribution, such as python:3.11-slim.",
        )

    def test_extra_gunicorn_requirement(self):
        if not EXTRA_CREDIT:
            return
        path = find_file("requirements.txt")
        self.assertIsNotNone(path, "No requirements.txt was found in src.")
        self.assertTrue(lists_package(path, "gunicorn"), "requirements.txt does not list gunicorn.")

    def test_extra_start_server_script(self):
        if not EXTRA_CREDIT:
            return
        path = find_file("start_server.sh")
        self.assertIsNotNone(path, "No start_server.sh was found in src.")
        script = read(path)
        self.assertIn("gunicorn", script, "start_server.sh does not run gunicorn.")
        self.assertRegex(
            script,
            r"(?:-w|--workers)\s*=?\s*4\b|workers\s*=\s*4\b",
            "start_server.sh does not start gunicorn with 4 workers.",
        )

    def test_extra_dockerfile_runs_script(self):
        if not EXTRA_CREDIT:
            return
        dockerfile = find_file("Dockerfile")
        self.assertIsNotNone(dockerfile, "No Dockerfile was found in src.")
        runs_script = any(
            re.match(r"(?i)(CMD|ENTRYPOINT)\b.*start_server\.sh", line) for line in dockerfile_lines(dockerfile)
        )
        compose = find_file(*COMPOSE_NAMES)
        if compose and re.search(r"^\s*(command|entrypoint)\s*:.*start_server\.sh", read(compose), re.MULTILINE):
            runs_script = True
        self.assertTrue(runs_script, "The Dockerfile's CMD does not run sh start_server.sh.")

    def test_extra_gunicorn_serves_app(self):
        if not EXTRA_CREDIT:
            return
        res, attempts = call_routes()
        self.assertIsNotNone(res, app_problem(attempts))
        server = res.headers.get("Server", "")
        self.assertTrue(
            server.lower().startswith("gunicorn"),
            f"The app in the container is served by {server or 'an unknown server'}, not gunicorn.",
        )


if __name__ == "__main__":
    EXTRA_CREDIT = len(sys.argv) > 1 and sys.argv[1] == "--extra"
    sys.argv = sys.argv[:1]
    unittest.main()
