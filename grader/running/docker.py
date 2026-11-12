"""Start and stop a student's containers with Docker Compose.

Used for test files that set DOCKER = True, such as PA5. The grader runs
`docker compose up -d` as the handout describes, waits for the app to answer,
and always removes the containers and any images it pulled afterward.
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from http.client import HTTPException
from pathlib import Path

PROJECT = "flask-grader"
COMPOSE_NAMES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
DEFAULT_PORT = 5000
UP_TIMEOUT_SECONDS = 600  # includes pulling the student's image
RESPONSE_WAIT_SECONDS = 60
COMMAND_TIMEOUT_SECONDS = 120


def docker(*args, timeout=COMMAND_TIMEOUT_SECONDS, cwd=None, env=None):
    """Run a docker command and return the finished process."""
    return subprocess.run(
        ["docker", *args], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=timeout,
    )


def docker_available():
    """True when the docker command exists and Docker is running."""
    try:
        return docker("info", "--format", "{{.ServerVersion}}", timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def last_line(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[-1] if lines else "no details"


def find_compose_file(app_dir):
    """The handout puts docker-compose.yml in src, next to app.py. Also accept the folder above."""
    for folder in (app_dir, app_dir.parent):
        for name in COMPOSE_NAMES:
            if (folder / name).is_file():
                return folder / name
    return None


def unsafe_setting(config, allowed_root):
    """Describe a setting that could reach outside the container, or return None."""
    allowed_root = os.path.realpath(allowed_root)
    for name, service in (config.get("services") or {}).items():
        if service.get("privileged"):
            return f"service {name} uses privileged mode"
        for key in ("network_mode", "pid", "ipc"):
            if service.get(key) == "host":
                return f"service {name} uses {key}: host"
        for volume in service.get("volumes") or []:
            if not isinstance(volume, dict) or volume.get("type") != "bind":
                continue
            source = os.path.realpath(volume.get("source", ""))
            if os.path.commonpath([allowed_root, source]) != allowed_root:
                return f"service {name} mounts {volume.get('source')}, which is outside the submission"
    return None


def published_port(config):
    """The host port of the app, preferring a service whose image is named username/repo."""
    services = list((config.get("services") or {}).values())
    services.sort(key=lambda service: "/" not in str(service.get("image", "")))
    for service in services:
        for port in service.get("ports") or []:
            if isinstance(port, dict) and port.get("published"):
                return int(str(port["published"]).split("-")[0])
    return None


def image_ids():
    result = docker("image", "ls", "-q", "--no-trunc")
    return set(result.stdout.split()) if result.returncode == 0 else set()


def remove_project_containers():
    """Remove containers left by an earlier run that was stopped partway."""
    result = docker("ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}")
    ids = result.stdout.split()
    if ids:
        docker("rm", "-f", *ids)


def other_platform():
    """The platform to retry with when an image was built only for the other one."""
    result = docker("info", "--format", "{{.Architecture}}")
    return "linux/arm64" if result.stdout.strip() in ("x86_64", "amd64") else "linux/amd64"


def responds(url):
    try:
        with urllib.request.urlopen(url + "/", timeout=3):
            return True
    except urllib.error.HTTPError:
        return True  # any HTTP answer, even 404, means the app is up
    except (OSError, HTTPException):
        return False


class Containers:
    """One student's containers. Use start(), then always stop()."""

    def __init__(self, app_dir):
        self.app_dir = Path(app_dir)
        self.compose_file = find_compose_file(self.app_dir)
        self.images_before = None

    def compose(self, *args, timeout=COMMAND_TIMEOUT_SECONDS, env=None):
        return docker(
            "compose", "-p", PROJECT, "-f", str(self.compose_file), *args,
            cwd=self.compose_file.parent, timeout=timeout, env=env,
        )

    def read_config(self):
        """Return (config, problem)."""
        result = self.compose("config", "--format", "json")
        if result.returncode != 0:
            return None, f"{self.compose_file.name} is not valid: {last_line(result.stderr)}"
        try:
            return json.loads(result.stdout), None
        except ValueError:
            return None, f"{self.compose_file.name} could not be read."

    def port(self):
        """Return (host port, problem) without starting anything, or (None, problem)."""
        if self.compose_file is None:
            return None, "No docker-compose.yml was found in src."
        config, problem = self.read_config()
        if problem:
            return None, problem
        unsafe = unsafe_setting(config, self.compose_file.parent.parent)
        if unsafe:
            return None, f"{self.compose_file.name} was not run because {unsafe}."
        return published_port(config) or DEFAULT_PORT, None

    def up(self):
        """Run docker compose up -d. Return a problem, or None when it worked."""
        try:
            result = self.compose("up", "-d", timeout=UP_TIMEOUT_SECONDS)
            if result.returncode != 0 and "no matching manifest" in result.stderr:
                # An image built on an Apple Silicon Mac may exist only for arm64, or the reverse.
                env = dict(os.environ, DOCKER_DEFAULT_PLATFORM=other_platform())
                result = self.compose("up", "-d", timeout=UP_TIMEOUT_SECONDS, env=env)
        except subprocess.TimeoutExpired:
            return f"docker compose up -d did not finish within {UP_TIMEOUT_SECONDS} seconds."
        if result.returncode != 0:
            return f"docker compose up -d failed: {last_line(result.stderr)}"
        return None

    def running(self):
        result = self.compose("ps", "--services", "--status", "running")
        return result.returncode == 0 and bool(result.stdout.strip())

    def wait_for_app(self, url):
        """Return a problem, or None once the app answers."""
        deadline = time.monotonic() + RESPONSE_WAIT_SECONDS
        checks = 0
        while time.monotonic() < deadline:
            if responds(url):
                return None
            checks += 1
            if checks % 5 == 0 and not self.running():
                break  # the container stopped, so waiting longer will not help
            time.sleep(1)
        logs = self.compose("logs", "--no-color", "--tail", "30").stdout
        return (
            f"The app did not respond at {url} after docker compose up -d. "
            f"Container log: {last_line(logs)}"
        )

    def start(self, port):
        """Start the containers. Return a problem, or None when the app answers."""
        remove_project_containers()
        self.images_before = image_ids()
        problem = self.up()
        if problem:
            return problem
        return self.wait_for_app(f"http://localhost:{port}")

    def stop(self):
        """Remove the containers, their volumes, and any images this run pulled or built."""
        if self.compose_file is None or self.images_before is None:
            return
        for step in (
            lambda: self.compose("down", "--volumes", "--remove-orphans"),
            remove_project_containers,
            self.remove_new_images,
        ):
            try:
                step()
            except (OSError, subprocess.SubprocessError):
                pass  # keep going so the other steps still clean up

    def remove_new_images(self):
        new_images = image_ids() - self.images_before
        if new_images:
            docker("image", "rm", "-f", *new_images)
