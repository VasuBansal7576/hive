#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

import requests
from jsonschema import Draft7Validator, FormatChecker


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "manifest.schema.json"
SERVERS_DIR = REPO_ROOT / "registry" / "servers"
ALLOWED_TAGS = {
    "project-management",
    "communication",
    "crm",
    "finance",
    "developer-tools",
    "productivity",
    "data",
    "atlassian",
    "google",
    "microsoft",
    "aws",
    "github",
    "issue-tracking",
    "calendar",
    "email",
    "database",
    "search",
    "ai",
    "analytics",
    "storage",
    "monitoring",
    "security",
    "ecommerce",
    "hr",
    "marketing",
}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ENV_VAR_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
REQUIRED_FIELDS = ("name", "version", "description", "status")


class ValidationError(Exception):
    def __init__(self, check_name: str, message: str) -> None:
        super().__init__(message)
        self.check_name = check_name
        self.message = message


def fail(check_name: str, message: str) -> None:
    raise ValidationError(check_name, message)


def manifest_targets(path_arg: str) -> list[Path]:
    candidate = Path(path_arg).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()

    if not candidate.exists():
        fail("PATH", f"{candidate} does not exist. Pass a manifest.json file or a directory.")

    if candidate.is_file():
        return [candidate]

    direct_manifest = candidate / "manifest.json"
    if direct_manifest.is_file():
        return [direct_manifest]

    manifests = sorted(candidate.rglob("manifest.json"))
    if not manifests:
        fail("PATH", f"No manifest.json files found under {candidate}. Add a manifest or point to a valid directory.")
    return manifests


def load_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        fail(
            "JSON",
            f"{path} is not valid JSON (line {exc.lineno}, column {exc.colno}). Fix the syntax and try again.",
        )
    except OSError as exc:
        fail("FILE", f"Could not read {path}: {exc}. Check the file path and permissions.")
    return {}


def validate_schema(path: Path, manifest: dict, schema: dict) -> None:
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(manifest), key=lambda err: list(err.absolute_path))
    if not errors:
        return

    first = errors[0]
    location = ".".join(str(part) for part in first.absolute_path) or "root"
    fail(
        "SCHEMA",
        f"{path} failed schema validation at '{location}': {first.message}. Update the manifest to match schema/manifest.schema.json.",
    )


def validate_name_format(path: Path, manifest: dict) -> None:
    name = manifest.get("name", "")
    if not NAME_RE.fullmatch(name):
        fail(
            "NAME FORMAT",
            f"{path} has name '{name}'. Use only lowercase letters, numbers, and hyphens, for example 'my-server'.",
        )


def server_manifests() -> Iterable[Path]:
    return sorted(SERVERS_DIR.glob("*/manifest.json"))


def validate_name_uniqueness(path: Path, manifest: dict) -> None:
    name = manifest["name"]
    for other_path in server_manifests():
        if other_path.resolve() == path.resolve():
            continue
        other_manifest = load_json(other_path)
        if other_manifest.get("name") == name:
            fail(
                "NAME UNIQUENESS",
                f"{path} reuses name '{name}', which is already claimed by {other_path}. Choose a globally unique registry name.",
            )


def validate_pypi_package(path: Path, manifest: dict) -> None:
    package = manifest.get("install", {}).get("pip")
    if package is None:
        return

    url = f"https://pypi.org/pypi/{package}/json"
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException as exc:
        fail(
            "PYPI",
            f"Could not verify PyPI package '{package}' for {path}: {exc}. Check your network connection or use install.pip = null.",
        )

    if response.status_code != 200:
        fail(
            "PYPI",
            f"install.pip references '{package}', but {url} returned HTTP {response.status_code}. Publish the package first or set install.pip to null.",
        )


def validate_tool_names(path: Path, manifest: dict) -> None:
    for tool in manifest.get("tools", []):
        tool_name = tool.get("name", "")
        if not TOOL_NAME_RE.fullmatch(tool_name):
            fail(
                "TOOL NAMES",
                f"{path} has tool name '{tool_name}'. Use snake_case names like 'jira_create_issue'.",
            )


def validate_credential_env_vars(path: Path, manifest: dict) -> None:
    for credential in manifest.get("credentials", []):
        env_var = credential.get("env_var", "")
        if not ENV_VAR_RE.fullmatch(env_var):
            fail(
                "ENV VAR",
                f"{path} has env_var '{env_var}'. Use UPPER_SNAKE_CASE names like 'JIRA_API_TOKEN'.",
            )


def validate_tags(path: Path, manifest: dict) -> None:
    invalid_tags = sorted(tag for tag in manifest.get("tags", []) if tag not in ALLOWED_TAGS)
    if invalid_tags:
        fail(
            "TAGS",
            f"{path} uses unsupported tags {invalid_tags}. Pick only from the documented registry taxonomy in CONTRIBUTING.md.",
        )


def validate_readme(path: Path) -> None:
    readme_path = path.with_name("README.md")
    if not readme_path.is_file():
        fail(
            "README",
            f"{readme_path} is missing. Add a non-empty README.md alongside the manifest explaining installation and usage.",
        )

    if not readme_path.read_text(encoding="utf-8").strip():
        fail(
            "README",
            f"{readme_path} is empty. Add installation and usage guidance before opening a PR.",
        )


def validate_required_fields(path: Path, manifest: dict) -> None:
    for field_name in REQUIRED_FIELDS:
        value = manifest.get(field_name)
        if value in (None, "", []):
            fail(
                "REQUIRED FIELDS",
                f"{path} is missing '{field_name}' or it is empty. Fill in all required metadata before submitting.",
            )


def validate_manifest(path: Path, schema: dict) -> None:
    if not path.is_file():
        fail("FILE", f"{path} does not exist. Create the manifest file and try again.")

    manifest = load_json(path)
    validate_schema(path, manifest, schema)
    validate_name_format(path, manifest)
    validate_name_uniqueness(path, manifest)
    validate_pypi_package(path, manifest)
    validate_tool_names(path, manifest)
    validate_credential_env_vars(path, manifest)
    validate_tags(path, manifest)
    validate_readme(path)
    validate_required_fields(path, manifest)
    print("✓ manifest.json is valid")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate.py <path_to_manifest_or_directory>")
        return 1

    try:
        schema = load_schema()
        manifests = manifest_targets(sys.argv[1])
        for manifest_path in manifests:
            validate_manifest(manifest_path, schema)
    except ValidationError as exc:
        print(f"✗ [{exc.check_name}] {exc.message}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
