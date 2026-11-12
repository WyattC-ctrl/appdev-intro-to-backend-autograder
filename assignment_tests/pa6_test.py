"""PA6 (Deployment) tests.

The student's server is already deployed on Google Cloud, so these tests call
the server address from their README instead of running app.py. The grader
runs them from the submission's src folder and sets GRADER_NETID.

To run this file by hand from a submission's src folder:

    GRADER_NETID=abc123 python3 pa6_test.py
"""
import os
import re
import sys
import unittest

import requests

# Flag to run extra credit tests (if applicable)
EXTRA_CREDIT = False

# The grader calls the deployed server instead of running app.py.
REMOTE = True

# PA6 has no challenges.
TIERS = {}
NO_CHALLENGES = True

# Each core test is worth its own points, out of 10: (test, points, rubric line, line when lost).
RUBRIC = [
    ("Deployed server", [
        ("test_server_is_reachable", 3, "Server address in the README is publicly reachable", "The server address in the README could not be reached"),
        ("test_base_endpoint", 2, 'GET / returns "<netid> was here!"', 'GET / does not return "<netid> was here!"'),
        ("test_working_endpoint", 2, "Working endpoint from the README returns JSON", "The working endpoint from the README did not return JSON"),
    ]),
    ("Environment variables", [
        ("test_env_file", 1, ".env in src/ contains the NetID", "No .env in src/ with the NetID"),
        ("test_netid_read_from_env", 1, "app.py reads the NetID from the environment", "app.py does not read the NetID from the environment"),
    ]),
    ("Files", [
        ("test_deployment_files", 1, "Dockerfile, docker-compose.yml, and .dockerignore are in src/", "Missing Dockerfile, docker-compose.yml, or .dockerignore in src/"),
    ]),
]

# The README template's fields and questions. Each one left blank is -0.5.
README_FIELDS = ["Name", "NetID", "Working Endpoint", "Your Server Address"]
README_QUESTIONS = [
    "Explain the concept of deployment in your own words.",
    "What are environment variables?",
    "What is the filename of the file where environment variables are traditionally stored?",
    "What is the network protocol we use to access servers?",
    "Explain the concept of clustering in your own words.",
    "Explain the concept of load balancing in your own words.",
]

NETID = os.environ.get("GRADER_NETID", "")
TIMEOUT_SECONDS = 15
# Tried when the README names no GET route. Every PA4 app has it.
DEFAULT_ROUTE = "/api/courses/"
# Links a README may contain that are not the student's server.
NOT_SERVER_HOSTS = ("hub.docker.com", "docker.com", "github.com", "google.com", "cornellappdev.com", "localhost", "127.0.0.1", "0.0.0.0")


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


def readme_text():
    path = find_readme()
    return read(path) if path else ""


def base_url(address):
    """http://host[:port] from an address such as 34.1.2.3, 34.1.2.3:8000, or http://34.1.2.3/."""
    address = address.strip().strip("<>()[]'\"`.,")
    if not re.match(r"https?://", address):
        address = "http://" + address
    match = re.match(r"(https?://[^/\s?#]+)", address)
    return match.group(1) if match else None


def is_server(url):
    host = re.sub(r"^https?://", "", url).split(":")[0].lower()
    return bool(host) and not any(host == bad or host.endswith("." + bad) for bad in NOT_SERVER_HOSTS)


def server_url():
    """The server address from the README's "Your Server Address" line, or the first other address in it."""
    text = readme_text()
    match = re.search(r"(?im)server\s+address\s*:[ \t]*(\S+)", text)
    if match and not match.group(1).startswith("<"):
        url = base_url(match.group(1))
        if url and is_server(url):
            return url
    candidates = re.findall(r"https?://[^\s<>'\"`)]+|\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b", text)
    for candidate in candidates:
        url = base_url(candidate)
        if url and is_server(url):
            return url
    return None


def readme_routes():
    """GET routes named in the README, with placeholders such as <id> filled in with 1."""
    routes = []
    for match in re.finditer(r"(?:\b([A-Za-z]+)\s+)?(?:https?://[^/\s]+)?(/api/\S*)", readme_text()):
        method = (match.group(1) or "GET").upper()
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            continue
        route = re.sub(r"<[^>]*>|\{[^}]*\}|(?<=/):\w+", "1", match.group(2))
        route = route.rstrip(".,;:!?)]}'\"`*")
        if route not in routes:
            routes.append(route)
    return routes


def find_in_src(name):
    path = os.path.join(".", name)
    return path if os.path.isfile(path) else None


def require_server(test):
    url = server_url()
    test.assertIsNotNone(url, 'The README has no server address. Fill in "Your Server Address:".')
    return url


def get(test, url):
    try:
        return requests.get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as error:
        test.fail(f"GET {url} could not connect ({type(error).__name__}).")


def body_text(res):
    try:
        data = res.json()
        if isinstance(data, str):
            return data.strip()
    except ValueError:
        pass
    return res.text.strip().strip('"').strip()


class TestRoutes(unittest.TestCase):
    def test_server_is_reachable(self):
        url = require_server(self)
        get(self, url + "/")

    def test_base_endpoint(self):
        url = require_server(self)
        res = get(self, url + "/")
        self.assertEqual(res.status_code, 200, f"GET {url}/ returned {res.status_code}, but 200 was expected.")
        expected = f"{NETID} was here!" if NETID else "was here!"
        body = body_text(res)
        self.assertTrue(
            body.lower() == expected.lower() if NETID else body.lower().endswith(expected),
            f'GET {url}/ returned "{body[:80]}", but "{expected}" was expected.',
        )

    def test_working_endpoint(self):
        url = require_server(self)
        attempts = []
        routes = readme_routes()
        for route in routes + [DEFAULT_ROUTE] * (DEFAULT_ROUTE not in routes):
            try:
                res = requests.get(url + route, timeout=TIMEOUT_SECONDS)
            except requests.RequestException as error:
                attempts.append(f"GET {route} could not connect ({type(error).__name__})")
                continue
            try:
                res.json()
                if res.status_code < 500:
                    return
                attempts.append(f"GET {route} returned {res.status_code}")
            except ValueError:
                attempts.append(f"GET {route} returned {res.status_code} without JSON")
        self.fail("No route returned JSON: " + "; ".join(attempts) + ".")

    def test_env_file(self):
        path = find_in_src(".env")
        if path is None and os.path.isfile(os.path.join("..", ".env")):
            self.fail(".env is in the folder above src/ instead.")
        self.assertIsNotNone(path, "There is no .env file in src/.")
        if NETID:
            self.assertIn(NETID.lower(), read(path).lower(), f".env does not contain the NetID {NETID}.")

    def test_netid_read_from_env(self):
        path = find_in_src("app.py")
        self.assertIsNotNone(path, "There is no app.py in src/.")
        source = read(path)
        if NETID:
            self.assertNotRegex(
                source.lower(), re.escape(NETID.lower()) + r"\s+was here",
                f'app.py hardcodes "{NETID} was here!" instead of reading the NetID from .env.',
            )
        self.assertRegex(source, r"\bgetenv\b|\benviron\b|dotenv", "app.py never reads an environment variable.")

    def test_deployment_files(self):
        missing = [name for name in ("Dockerfile", "docker-compose.yml", ".dockerignore") if not find_in_src(name)]
        if "docker-compose.yml" in missing and find_in_src("docker-compose.yaml"):
            missing.remove("docker-compose.yml")
        self.assertFalse(missing, f"Missing from src/: {', '.join(missing)}.")


if __name__ == "__main__":
    sys.argv = sys.argv[:1]
    unittest.main()
