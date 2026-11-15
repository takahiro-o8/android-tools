#!/usr/bin/env python3
"""Keep the latest 3 distinct published APK versions; remove older Releases and release tags.

Only official Releases with recognizable versioned APK assets are candidates.
No Git commits, branches, source files, draft releases or diagnostic prereleases are deleted.
Requires GH_TOKEN with contents:write and GH_REPO=owner/name.
"""
import argparse
import json
import os
import re
import subprocess
import sys

VERSION_RE = re.compile(r"(?:^|[-_])v?(\d+)\.(\d+)\.(\d+)(?:[-_]|\.apk$)", re.I)


def gh(*args):
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {proc.stderr.strip()}")
    return proc.stdout


def releases_for(repo):
    raw = json.loads(gh("api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100"))
    if raw and isinstance(raw[0], list):
        return [release for page in raw for release in page]
    return raw


def version_from_release(release):
    if release.get("draft") or release.get("prerelease"):
        return None
    assets = [a.get("name", "") for a in release.get("assets", []) if a.get("name", "").lower().endswith(".apk")]
    versions = set()
    for name in assets:
        match = VERSION_RE.search(name)
        if match:
            versions.add(tuple(map(int, match.groups())))
    return next(iter(versions)) if len(versions) == 1 else None


def newest(release):
    return release.get("published_at") or release.get("created_at") or ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=int, default=3)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.keep < 1:
        parser.error("--keep must be >= 1")
    repo = os.getenv("GH_REPO") or os.getenv("GITHUB_REPOSITORY")
    if not repo or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise SystemExit("GH_REPO must be owner/repository")
    versions = {}
    for release in releases_for(repo):
        version = version_from_release(release)
        if version is not None:
            versions.setdefault(version, []).append(release)
    ordered = sorted(versions, reverse=True)
    if len(ordered) < args.keep:
        print(f"{repo}: only {len(ordered)} recognizable published APK versions; skipping deletion")
        return
    preserved = set(ordered[:args.keep])
    doomed = []
    for version, matches in versions.items():
        matches.sort(key=newest, reverse=True)
        for index, release in enumerate(matches):
            if version not in preserved or index:
                doomed.append((version, release))
    print(f"{repo}: keep {args.keep} versions: " + ", ".join(".".join(map(str,v)) for v in ordered[:args.keep]))
    for version, release in sorted(doomed, key=lambda x: x[0], reverse=True):
        tag = release["tag_name"]
        print(f"{'DELETE' if args.apply else 'WOULD DELETE'}: {tag} v{'.'.join(map(str,version))}")
        if args.apply:
            gh("release", "delete", tag, "--repo", repo, "--yes", "--cleanup-tag")
    print(f"{repo}: removed {len(doomed) if args.apply else 0}, planned {len(doomed)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)
