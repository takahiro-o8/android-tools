#!/usr/bin/env python3
"""Exit 0 if latest formal APK already represents the same production inputs.
Exit 2 if another APK is warranted. Exit 1 on GitHub metadata errors.
"""
import argparse
import json
import re
import subprocess
import sys
from release_versions import MAX_CODE, PROVEN_RE, semantic


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--expected-package", required=True)
    args = p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        raise ValueError("Invalid repository")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.source_sha):
        raise ValueError("Invalid source commit SHA")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", args.expected_package):
        raise ValueError("Invalid applicationId")

    pages = json.loads(command("gh", "api", "--paginate", "--slurp",
                               f"repos/{args.repo}/releases?per_page=100"))
    releases = [item for page in pages for item in page]
    formal = [r for r in releases if not r.get("draft") and not r.get("prerelease")
              and any(a.get("name", "").lower().endswith(".apk")
                      for a in r.get("assets", []))]
    if not formal:
        return 2
    # The greatest verified Android versionCode identifies the newest update.
    # Publication dates can be reordered (e.g. a delayed older job).
    known = []
    for release in formal:
        assets = [a for a in release["assets"] if a.get("name", "").lower().endswith(".apk")]
        metadata = list(PROVEN_RE.finditer(release.get("body") or ""))
        if len(assets) != 1 or len(metadata) != 1:
            return 2  # Normal build performs actual-APK fallback verification.
        version = metadata[0]
        if version.group(1) != args.expected_package:
            raise ValueError("Published APK has another applicationId")
        semantic(version.group(3), legacy=True)
        code = int(version.group(2))
        if not 1 <= code <= MAX_CODE:
            raise ValueError("Invalid published Android versionCode")
        known.append((code, release))
    if len({item[0] for item in known}) != len(known):
        return 2  # Ambiguous duplicate codes require full lineage verification.
    latest = max(known, key=lambda item: item[0])[1]
    body = latest.get("body") or ""
    source = re.search(r"(?m)^Signed production APK from ([0-9a-fA-F]{40})$", body)
    if not source:
        return 2
    previous_sha = source.group(1).lower()
    current_sha = args.source_sha.lower()
    if previous_sha == current_sha:
        print(f"::notice::APK for {current_sha} already published ({latest['tag_name']}); skipping duplicate build.")
        return 0

    # Only human-readable Markdown and previously tracked distribution/test APKs
    # may change without altering the current production build inputs.
    try:
        command("git", "cat-file", "-e", f"{previous_sha}^{{commit}}")
    except subprocess.CalledProcessError:
        try:
            command("git", "fetch", "--no-tags", "--depth=1", "origin", previous_sha)
        except subprocess.CalledProcessError:
            print("::notice::Prior release commit unavailable; build normally.")
            return 2
    try:
        changed = command("git", "diff", "--name-only", "--no-renames",
                          previous_sha, current_sha).splitlines()
    except subprocess.CalledProcessError:
        print("::notice::Cannot compare prior source trees; build normally.")
        return 2
    significant = [path for path in changed
                   if path and not (path.endswith(".md") or
                                    path.startswith(("dist/", "validation/")))]
    if not significant:
        print(f"::notice::Only documentation or legacy APK files differ from {latest['tag_name']}; no new APK needed.")
        return 0
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as e:
        print(f"::error::Duplicate release check failed: {e}", file=sys.stderr)
        sys.exit(1)
