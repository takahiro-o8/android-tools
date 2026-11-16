#!/usr/bin/env python3
"""Restore app-specific GitHub signing Secrets from a PC's age recovery key.

No signing passwords need to be remembered. The age identity MUST be backed up.
Default is DRY RUN; --apply is needed for GitHub mutations.
"""
import argparse
import base64
import io
import json
import pathlib
import re
import subprocess
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument("backup", type=pathlib.Path, help="Downloaded android-signing-backup.age")
parser.add_argument("--identity", type=pathlib.Path, required=True, help="Local private age key file")
parser.add_argument("--apply", action="store_true", help="Restore GitHub Secrets (requires gh auth login)")
parser.add_argument("--export-keystore", type=pathlib.Path, help="Optional local key file copy (keep private)")
args = parser.parse_args()
if not args.identity.is_file():
    raise SystemExit("The recovery identity private key file was not found")
encrypted = args.backup.read_bytes()
result = subprocess.run(["age", "-d", "-i", str(args.identity)], input=encrypted,
                        capture_output=True, check=False)
if result.returncode:
    raise SystemExit("Cannot decrypt backup. Check that this is the matching age identity.")
with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as arc:
    manifest = json.load(arc.extractfile("manifest.json"))
    keystore = arc.extractfile("keystore.bin").read()
repo = manifest.get("repository", "")
if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
    raise SystemExit("Invalid repository in recovered manifest")
if manifest.get("schema_version") != 1:
    raise SystemExit("Unsupported signing backup format")
names = manifest["secret_names"]
values = {}
if manifest["source"] == "base64":
    values[names["keystore"]] = base64.b64encode(keystore).decode("ascii")
values[names["password"]] = manifest["store_password"]
if names.get("key_password"):
    values[names["key_password"]] = manifest["key_password"] or manifest["store_password"]
if names.get("alias"):
    values[names["alias"]] = manifest["alias"]
if any(not re.fullmatch(r"[A-Z0-9_]+", k or "") for k in values):
    raise SystemExit("Invalid GitHub Secret name in recovered backup")
print("Repository:", repo)
print("Signing alias:", manifest["alias"])
print("Secrets:", ", ".join(sorted(values)))
print("Key type:", manifest["source"], "(keystore bytes: %d)" % len(keystore))
if args.export_keystore:
    if args.export_keystore.exists():
        raise SystemExit("Refusing to overwrite an existing key file")
    args.export_keystore.parent.mkdir(parents=True, exist_ok=True)
    args.export_keystore.write_bytes(keystore)
    args.export_keystore.chmod(0o600)
    print("Signing key copy saved to:", str(args.export_keystore))
if args.apply:
    for name, value in values.items():
        p = subprocess.run(["gh", "secret", "set", name, "-R", repo],
                           input=value.encode("utf-8"), capture_output=True)
        if p.returncode:
            raise SystemExit("Failed to restore Secret " + name +
                             ". Check gh auth status and repository access.")
    print("GitHub signing Secrets restored for", repo)
else:
    print("Dry run only. Add --apply to restore GitHub Secrets.")
