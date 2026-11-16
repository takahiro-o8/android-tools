#!/usr/bin/env python3
"""Fail closed unless a signed production APK has the expected package identity and
a strictly greater Android versionCode than EVERY currently published APK.

Reads older APKs when a release lacks this tool's verified version metadata.
New releases include metadata, so subsequent checks avoid repeated APK downloads.
No emulator, E2E, or unit tests are launched.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


PACKAGE_RE = re.compile(r"^package:\s+name='([^']+)'\s+versionCode='([0-9]+)'\s+versionName='([^']*)'")
PROVEN_RE = re.compile(
    r"(?m)^Verified-APK: package=([A-Za-z0-9_.]+); versionCode=([0-9]+); versionName=([^\r\n;]*)$"
)


def run(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise ValueError("Verification command failed: " + args[0] + " " + args[1])
    return result.stdout


def manifest(aapt, path):
    text = run([aapt, "dump", "badging", str(path)])
    first = next((line for line in text.splitlines() if line.startswith("package:")), "")
    match = PACKAGE_RE.match(first)
    if match is None:
        raise ValueError("Cannot determine actual APK package/versionCode/versionName")
    return match.group(1), int(match.group(2)), match.group(3)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", required=True)
    p.add_argument("--aapt", required=True)
    p.add_argument("--expected-package", required=True)
    p.add_argument("--expected-code", type=int, required=True)
    p.add_argument("--expected-name", required=True)
    p.add_argument("--repo", required=True)
    args = p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        raise ValueError("Invalid repository identity")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", args.expected_package):
        raise ValueError("Invalid expected Android applicationId")
    if args.expected_code < 1:
        raise ValueError("Expected Android versionCode must be positive")

    actual_package, actual_code, actual_name = manifest(args.aapt, args.candidate)
    if (actual_package, actual_code, actual_name) != (
        args.expected_package, args.expected_code, args.expected_name
    ):
        raise ValueError(
            "Candidate APK does not match pinned applicationId and CI version; "
            f"expected {args.expected_package} / {args.expected_code} / {args.expected_name}, "
            f"got {actual_package} / {actual_code} / {actual_name}"
        )
    print(f"Verified candidate APK package={actual_package} versionCode={actual_code}")

    releases = json.loads(run(["gh", "api", f"repos/{args.repo}/releases?per_page=100"]))
    if not isinstance(releases, list) or len(releases) >= 100:
        raise ValueError("Cannot exhaustively verify existing releases; stop publication")
    highest = 0
    verified = 0
    with tempfile.TemporaryDirectory(prefix="verify-previous-apks-", dir=os.environ.get("RUNNER_TEMP")) as d:
        work = Path(d)
        for release in releases:
            if release.get("draft") or release.get("prerelease"):
                continue
            tag = release.get("tag_name", "")
            assets = [x for x in release.get("assets", []) if x.get("name", "").lower().endswith(".apk")]
            if not assets:
                continue
            metadata = PROVEN_RE.search(release.get("body") or "")
            if metadata and len(assets) == 1:
                old_package, old_code = metadata.group(1), int(metadata.group(2))
                if old_package != args.expected_package:
                    raise ValueError(f"Published release {tag} declares another package: {old_package}")
                print(f"Verified previous release {tag}: versionCode={old_code} (verified metadata)")
                highest = max(highest, old_code)
                verified += 1
                continue

            # Legacy release: never infer versionCode from a tag/title. Inspect its real APK.
            for asset in assets:
                filename = asset["name"]
                directory = work / str(release["id"]) / str(asset["id"])
                directory.mkdir(parents=True, exist_ok=True)
                run(["gh", "release", "download", tag, "-R", args.repo,
                     "--pattern", filename, "--dir", str(directory)])
                target = directory / filename
                if not target.is_file() or target.stat().st_size < 100:
                    raise ValueError(f"Unable to inspect published APK for {tag}")
                old_package, old_code, _ = manifest(args.aapt, target)
                if old_package != args.expected_package:
                    raise ValueError(f"Published APK in {tag} has a different package: {old_package}")
                print(f"Verified previous release {tag}: versionCode={old_code} (APK examined)")
                highest = max(highest, old_code)
                verified += 1

    if actual_code <= highest:
        raise ValueError(
            f"Release BLOCKED: versionCode {actual_code} must exceed "
            f"highest published versionCode {highest}"
        )
    print(
        f"Verified release lineage: versionCode {actual_code} > "
        f"highest published versionCode {highest}, inspected={verified}"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("::error::" + str(exc), file=sys.stderr)
        sys.exit(1)
