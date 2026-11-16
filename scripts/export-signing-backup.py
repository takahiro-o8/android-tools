#!/usr/bin/env python3
"""Create an age-encrypted, manually downloaded signing backup. NO plaintext disk output.

Only run this in a manually dispatched GitHub Actions job. Contains the exact
existing app keystore and required Secrets to restore it without remembering
or separately backing up each app signing password.
"""
import base64
import datetime
import io
import json
import os
import pathlib
import re
import subprocess
import tarfile

def env(name, required=True):
    value = os.environ.get(name, "")
    if required and not value:
        raise SystemExit("Missing required signing configuration: " + name)
    return value

if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
    raise SystemExit("Only manual workflow_dispatch signing backups are allowed")
repo = env("GITHUB_REPOSITORY")
if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
    raise SystemExit("Unexpected repository name")
recipient = env("AGE_RECIPIENT")
if not re.fullmatch(r"age1[0-9a-z]{40,110}", recipient):
    raise SystemExit("Enter an age X25519 recipient public key beginning age1")
source = env("BACKUP_SOURCE")
if source not in ("base64", "file"):
    raise SystemExit("BACKUP_SOURCE must be base64 or file")
alias = env("BACKUP_ALIAS")
password = env("BACKUP_STORE_PASSWORD")
key_password = env("BACKUP_KEY_PASSWORD", False)
file_path = env("BACKUP_KEY_FILE", False)
certificate_file = env("BACKUP_CERT_FILE", False)
if source == "base64":
    encoded = env("BACKUP_KEYSTORE_BASE64")
    try:
        key_data = base64.b64decode("".join(encoded.split()), validate=True)
    except (ValueError, base64.binascii.Error):
        raise SystemExit("Key Secret must be valid Base64")
else:
    if not file_path or not re.fullmatch(r"signing/[A-Za-z0-9._-]+\.p12", file_path):
        raise SystemExit("File signing source must be a checked-in PKCS12 file")
    key_data = pathlib.Path(file_path).read_bytes()
if not 100 <= len(key_data) <= 100000:
    raise SystemExit("Invalid signing keystore size")
pin = ""
if certificate_file:
    pin = pathlib.Path(certificate_file).read_text().strip()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", pin):
        raise SystemExit("Certificate pin must be a SHA256 digest")
secret_names = {
    "keystore": env("BACKUP_KEY_SECRET_NAME", False),
    "password": env("BACKUP_PASSWORD_SECRET_NAME"),
    "key_password": env("BACKUP_KEY_PASSWORD_SECRET_NAME", False),
    "alias": env("BACKUP_ALIAS_SECRET_NAME", False),
}
if source == "base64" and not secret_names["keystore"]:
    raise SystemExit("BACKUP_KEY_SECRET_NAME missing for Base64 signing")
metadata = {
    "schema_version": 1,
    "repository": repo,
    "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source": source,
    "alias": alias,
    "secret_names": secret_names,
    "store_password": password,
    "key_password": key_password,
    "certificate_sha256": pin,
    "keystore_filename": "keystore.bin",
    "original_file_path": file_path if source == "file" else "",
}
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w") as tar:
    for name, value in (
        ("keystore.bin", key_data),
        ("manifest.json", json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"))
    ):
        info = tarfile.TarInfo(name)
        info.size = len(value)
        info.mode = 0o600
        tar.addfile(info, io.BytesIO(value))
output = pathlib.Path(env("RUNNER_TEMP")) / "android-signing-backup.age"
output.unlink(missing_ok=True)
result = subprocess.run(
    ["age", "-r", recipient, "-o", str(output)],
    input=buf.getvalue(), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
)
if result.returncode or not output.is_file() or output.stat().st_size < 100:
    raise SystemExit("age backup encryption failed; no backup was uploaded")
output.chmod(0o600)
print("Encrypted signing backup created for", repo, "- download the artifact and store it separately.")
print("The recovery PRIVATE KEY on your PC is essential; never upload it to GitHub.")
