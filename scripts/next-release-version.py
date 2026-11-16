#!/usr/bin/env python3
"""Choose the next APK version from published APK history; never a CI run number."""
import argparse
from pathlib import Path
import re
import sys
from release_versions import next_version, published_apks


def base_version(root, module):
    properties = root / "version.properties"
    if properties.exists():
        values = {}
        for line in properties.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith(("#", "!")):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        return values["VERSION_NAME"], int(values["VERSION_CODE"])
    source = (root / module / "build.gradle.kts").read_text()
    name = re.search(r'^\s*versionName\s*=\s*"([^"\r\n]+)"\s*$', source, re.M)
    code = re.search(r'^\s*versionCode\s*=\s*([0-9]+)\s*$', source, re.M)
    if not name or not code:
        raise ValueError("Define VERSION_NAME=x.y.z and VERSION_CODE in version.properties")
    return name.group(1), int(code.group(1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--expected-package", required=True)
    parser.add_argument("--aapt", required=True)
    parser.add_argument("--module", default="app")
    args = parser.parse_args()
    name, code = base_version(Path.cwd(), args.module)
    history = published_apks(args.repo, args.expected_package, args.aapt)
    code, name = next_version(name, code, history)
    # The caller reads these two data lines; never eval external metadata.
    print(code)
    print(name)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("::error::" + str(exc), file=sys.stderr)
        sys.exit(1)
