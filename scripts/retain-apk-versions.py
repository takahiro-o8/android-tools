#!/usr/bin/env python3
"""Keep the latest 3 official signed APK Releases. Delete all auxiliary/draft Releases.

The source history, branches and signing keys are untouched.
"""
import argparse
import json
import os
import re
import subprocess
import sys


def gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout


def fetch_releases(repo):
    raw = json.loads(gh("api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100"))
    return [r for page in raw for r in page] if raw and isinstance(raw[0], list) else raw


def is_production(release):
    return not release.get("draft") and not release.get("prerelease") and any(
        a.get("name", "").lower().endswith(".apk") for a in release.get("assets", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=int, default=3)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--remove-aux", action="store_true")
    args = parser.parse_args()
    if args.keep < 1:
        parser.error("--keep must be positive")
    repo = os.getenv("GH_REPO") or os.getenv("GITHUB_REPOSITORY")
    if not repo or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise SystemExit("GH_REPO must be owner/repository")
    releases = fetch_releases(repo)
    production = sorted((r for r in releases if is_production(r)),
                        key=lambda r:(r.get("published_at") or r.get("created_at") or "", r["id"]),
                        reverse=True)
    preserved = set(r["id"] for r in production[:args.keep])
    to_delete = [r for r in releases if (is_production(r) and r["id"] not in preserved)
                 or (args.remove_aux and not is_production(r))]
    print("Keep:", [r["tag_name"] for r in production[:args.keep]])
    for release in to_delete:
        tag = release["tag_name"]
        print(("Delete:" if args.apply else "Would delete:") + tag)
        if args.apply:
            gh("release", "delete", tag, "--repo", repo, "--yes", "--cleanup-tag")
    print("Deleted", len(to_delete) if args.apply else 0, "out of", len(releases), "Releases")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
