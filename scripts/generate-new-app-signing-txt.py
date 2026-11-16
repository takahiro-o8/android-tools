#!/usr/bin/env python3
"""Create one copy/paste-ready TXT file for a NEW app's GitHub signing Secret.

This script is for an AI assistant to execute when creating a NEW Android app.
Run it in the assistant's local working environment, never in GitHub Actions.
The file must be delivered directly to the owner, not committed/pushed.
The production keystore is subsequently generated once by the CI bootstrap.
"""
import argparse
import os
from pathlib import Path
import re
import secrets
import string


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/new-private-repository")
    parser.add_argument("--application-id", required=True)
    parser.add_argument("--secret-name", help="Optional explicit Actions Secret name")
    parser.add_argument("--output", required=True, help="A new local .txt file to send to the owner")
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("Repository must be owner/name")
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z_0-9]*(?:\.[a-zA-Z_][a-zA-Z_0-9]*)+", args.application_id):
        parser.error("Invalid Android applicationId")

    repo_name = args.repo.split("/", 1)[1]
    default_name = re.sub(r"[^A-Z0-9]", "_", repo_name.upper()).strip("_") + "_SIGNING_PASSWORD"
    secret_name = args.secret_name or default_name
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,99}", secret_name):
        parser.error("Secret name must be 3-100 characters: A-Z, 0-9 and underscore")

    target = Path(args.output).expanduser().resolve()
    if target.suffix.lower() != ".txt":
        parser.error("Output must end with .txt")
    if not target.parent.is_dir():
        parser.error("Output directory must already exist")
    # Refuse writing the password into any tracked or untracked repository tree.
    here = Path(__file__).resolve()
    roots = [Path.cwd().resolve(), here.parent.parent]
    for root in roots:
        if (root / ".git").exists() and target.is_relative_to(root):
            parser.error("Never write a signing-secret TXT inside a Git repository")

    chars = string.ascii_letters + string.digits
    password = "".join(secrets.choice(chars) for _ in range(48))

    content = f"""Android signing setup — NEW APP ONLY
=====================================
Repository: {args.repo}
applicationId (must stay fixed): {args.application_id}

GitHub repository Actions Secret
--------------------------------
Name (copy exactly):
{secret_name}

Value (copy exactly, single line, 48 ASCII alphanumeric characters):
{password}

Where to paste:
https://github.com/{args.repo}/settings/secrets/actions
Select "New repository secret". Name = above Name, Secret = above Value.

Then run ONE TIME:
https://github.com/{args.repo}/actions/workflows/build.yml
Branch: main
Run workflow → initialize_new_key: CHECKED

How this works:
The AI generates the GitHub Secret value, and gives it to you in this TXT.
GitHub Actions generates the app's fixed RSA/PKCS12 signing key exactly once.
The private keystore file is password-encrypted and kept in the PRIVATE repo.
You do NOT need to create, copy, or register a separate Base64 keystore secret.
After the first successful APK, leave initialize_new_key unchecked.
For normal main commits, GitHub Actions signs APKs automatically.

IMPORTANT:
* This TXT contains a secret. Do not commit it, add it to Issues, or share it.
* If you lose the key or Secret later, you accepted reinstalling this app.
* Do not edit the Secret after key generation: that would lock the signing key.
* Do not use these values for an existing app with an established signing key.
"""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(str(target), flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    print("Created signing setup TXT:", target)
    print("Secret Name:", secret_name)
    print("Deliver the TXT to the owner; do NOT paste its Value into a repo/log/chat.")


if __name__ == "__main__":
    main()
