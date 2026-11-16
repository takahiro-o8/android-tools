#!/usr/bin/env python3
"""Check the signed APK's identity and strictly increasing numeric x.y.z/code.

History comes from verified APK metadata, falling back to actual older APKs.
Fetch history again just before publication to catch changes since version selection.
"""
import argparse
import sys
from release_versions import ApkVersion, manifest, published_apks, validate_identity, verify_candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--aapt", required=True)
    parser.add_argument("--expected-package", required=True)
    parser.add_argument("--expected-code", type=int, required=True)
    parser.add_argument("--expected-name", required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    validate_identity(args.repo, args.expected_package)
    actual = manifest(args.aapt, args.candidate)
    expected = ApkVersion(args.expected_package, args.expected_code, args.expected_name)
    history = published_apks(args.repo, args.expected_package, args.aapt)
    verify_candidate(actual, expected, history)
    print(f"Verified release lineage: package={actual.package} versionCode={actual.code} "
          f"versionName={actual.name}, inspected={len(history)}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("::error::" + str(exc), file=sys.stderr)
        sys.exit(1)
