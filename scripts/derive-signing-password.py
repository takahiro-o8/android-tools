#!/usr/bin/env python3
"""Derive an ASCII PKCS12 password from a strong per-app Actions Secret.

Used exclusively for new keys created by bootstrap-signing.sh.
Never enable this conversion for existing fixed keystores.
"""
import hashlib
import os
import sys

if len(sys.argv) != 2 or sys.argv[1] not in ("APP_SIGNING_PASSWORD", "KEYSTORE_PASSWORD"):
    raise SystemExit("Expected APP_SIGNING_PASSWORD or KEYSTORE_PASSWORD environment name")
secret = os.environ.get(sys.argv[1], "")
repo = os.environ.get("GITHUB_REPOSITORY", "")
if not secret or not repo or "/" not in repo:
    raise SystemExit("Signing Secret and GITHUB_REPOSITORY are required")
if len(secret) < 32:
    raise SystemExit("Signing Secret must contain at least 32 characters")
salt = ("android-tools:pkcs12:v1:" + repo).encode("utf-8")
derived = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, 300_000)
print(derived.hex())
