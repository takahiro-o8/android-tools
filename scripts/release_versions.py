#!/usr/bin/env python3
"""Shared production APK history and numeric x.y.z version policy.

Only verified APK metadata (or the APK itself) supplies history. GitHub run
numbers, release titles, tag spellings and publication dates never supply versions.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import NamedTuple

MAX_CODE = 2_100_000_000
NUMBER = r"(?:0|[1-9][0-9]*)"
VERSION = rf"({NUMBER})\.({NUMBER})\.({NUMBER})"
PROVEN_RE = re.compile(
    r"(?m)^Verified-APK: package=([A-Za-z0-9_.]+); versionCode=([0-9]+); versionName=([^\r\n;]*)$"
)
PACKAGE_RE = re.compile(r"^package:\s+name='([^']+)'\s+versionCode='([0-9]+)'\s+versionName='([^']*)'")


class ApkVersion(NamedTuple):
    package: str
    code: int
    name: str


def semantic(name, *, legacy=False):
    suffix = r"(?:\.b[0-9]+)?" if legacy else ""
    match = re.fullmatch(VERSION + suffix, name)
    if not match:
        raise ValueError(f"Expected numeric x.y.z version{' (or historical .bN)' if legacy else ''}: {name}")
    return tuple(int(part) for part in match.groups())


def command(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise ValueError("Verification command failed: " + " ".join(args[:2]))
    return result.stdout


def validate_identity(repo, package):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid repository identity")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", package):
        raise ValueError("Invalid Android applicationId")


def manifest(aapt, path):
    text = command([aapt, "dump", "badging", str(path)])
    first = next((line for line in text.splitlines() if line.startswith("package:")), "")
    match = PACKAGE_RE.match(first)
    if match is None:
        raise ValueError("Cannot determine actual APK package/versionCode/versionName")
    return ApkVersion(match.group(1), int(match.group(2)), match.group(3))


def published_apks(repo, package, aapt):
    validate_identity(repo, package)
    releases = json.loads(command(["gh", "api", f"repos/{repo}/releases?per_page=100"]))
    # The retention policy keeps three formal releases. Fail closed at the API
    # page boundary rather than overlooking a version on a subsequent page.
    if not isinstance(releases, list) or len(releases) >= 100:
        raise ValueError("Cannot exhaustively verify existing releases; stop publication")
    result = []
    with tempfile.TemporaryDirectory(prefix="published-apks-", dir=os.environ.get("RUNNER_TEMP")) as d:
        for release in releases:
            if release.get("draft") or release.get("prerelease"):
                continue
            assets = [a for a in release.get("assets", []) if a.get("name", "").lower().endswith(".apk")]
            if not assets:
                continue
            metadata = list(PROVEN_RE.finditer(release.get("body") or ""))
            if len(metadata) == 1 and len(assets) == 1:
                m = metadata[0]
                versions = [ApkVersion(m.group(1), int(m.group(2)), m.group(3))]
            else:
                versions = []
                # Never guess from a release title or tag, even during migration.
                for asset in assets:
                    filename = asset["name"]
                    if Path(filename).name != filename or "\\" in filename:
                        raise ValueError("Invalid APK asset filename")
                    directory = Path(d) / str(release["id"]) / str(asset["id"])
                    directory.mkdir(parents=True, exist_ok=True)
                    command(["gh", "release", "download", release["tag_name"], "--repo", repo,
                             "--pattern", filename, "--dir", str(directory)])
                    target = directory / filename
                    if not target.is_file() or target.stat().st_size < 100:
                        raise ValueError("Unable to inspect a published APK")
                    versions.append(manifest(aapt, target))
            for version in versions:
                if version.package != package:
                    raise ValueError("Published APK has another applicationId: " + version.package)
                if not 1 <= version.code <= MAX_CODE:
                    raise ValueError("Invalid published Android versionCode")
                semantic(version.name, legacy=True)
                result.append(version)
    return result


def next_version(base_name, base_code, history):
    requested = semantic(base_name)
    if not 1 <= base_code <= MAX_CODE:
        raise ValueError("Invalid base Android versionCode")
    highest_name = max((semantic(v.name, legacy=True) for v in history), default=None)
    if highest_name is not None and requested <= highest_name:
        requested = highest_name[0], highest_name[1], highest_name[2] + 1
    code = max(base_code, max((v.code for v in history), default=0) + 1)
    if code > MAX_CODE:
        raise ValueError("Android versionCode space exhausted")
    return code, ".".join(map(str, requested))


def verify_candidate(actual, expected, history):
    semantic(expected.name)
    if not 1 <= expected.code <= MAX_CODE:
        raise ValueError("Invalid expected Android versionCode")
    if actual != expected:
        raise ValueError(f"APK does not match expected identity/version: expected={expected}, got={actual}")
    for old in history:
        if old.package != actual.package:
            raise ValueError("Published APK has another applicationId")
        if actual.code <= old.code:
            raise ValueError(f"Release BLOCKED: versionCode {actual.code} must exceed {old.code}")
        if semantic(actual.name) <= semantic(old.name, legacy=True):
            raise ValueError(f"Release BLOCKED: versionName {actual.name} must exceed {old.name}")
