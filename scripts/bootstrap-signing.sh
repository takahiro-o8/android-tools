#!/usr/bin/env bash
# One-time signing-key bootstrap for an explicitly authorized NEW Android app.
# Encrypted PKCS12 is committed to the PRIVATE app repo; password stays in Actions Secrets.
set -euo pipefail
umask 077
: "${APP_SIGNING_PASSWORD:?Register one strong Actions signing-password Secret first}"
: "${SIGNING_ALIAS:?}"
: "${SIGNING_FILE_PATH:?}"
: "${SIGNING_CERT_PATH:?}"
: "${SIGNING_APP_LABEL:?}"
: "${GITHUB_REPOSITORY:?}"

# Explicit authorization is mandatory. A one-time approval marker permits
# automating the FIRST replacement key after a failed unpublished bootstrap.
approval_marker="${BOOTSTRAP_MARKER_FILE:-}"
approved_dispatch=false
approved_marker=false
if [[ "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" && "${BOOTSTRAP_APPROVED:-}" == "true" ]]; then
  approved_dispatch=true
elif [[ "${GITHUB_EVENT_NAME:-}" == "push" && "${BOOTSTRAP_APPROVED:-}" == "true" &&
        "$approval_marker" == "signing/bootstrap-once-approved" &&
        -f "$approval_marker" ]]; then
  approved_marker=true
fi
if [[ "${GITHUB_REF:-}" != "refs/heads/main" ||
      ( "$approved_dispatch" != "true" && "$approved_marker" != "true" ) ]]; then
  echo "::error::New signing identities require a one-time explicit main-branch authorization." >&2
  exit 1
fi
if [[ ${#APP_SIGNING_PASSWORD} -lt 32 ]]; then
  echo "::error::Use a randomly generated signing password containing at least 32 characters." >&2
  exit 1
fi
# keytool PKCS12 requires ASCII: derive a deterministic high-entropy hex password
# from any Unicode Actions Secret. Never log the derived password.
APP_SIGNING_PASSWORD="$(python3 .android-tools/scripts/derive-signing-password.py APP_SIGNING_PASSWORD)"
export APP_SIGNING_PASSWORD
if [[ ! "$SIGNING_ALIAS" =~ ^[a-zA-Z][a-zA-Z0-9_-]{1,49}$ ||
      ! "$SIGNING_FILE_PATH" =~ ^signing/[A-Za-z0-9._-]+\.p12$ ||
      ! "$SIGNING_CERT_PATH" =~ ^signing/[A-Za-z0-9._-]+\.sha256$ ||
      ! "$SIGNING_APP_LABEL" =~ ^[A-Za-z0-9._\ -]+$ ]]; then
  echo "::error::Invalid signing configuration." >&2
  exit 1
fi

if [[ "$(gh api "repos/$GITHUB_REPOSITORY" --jq '.private')" != "true" ]]; then
  echo "::error::The signing bootstrap requires a PRIVATE repository." >&2
  exit 1
fi
if [[ -e "$SIGNING_FILE_PATH" || -e "$SIGNING_CERT_PATH" ]] ||
   git ls-tree -r --name-only HEAD | grep -Fxq "$SIGNING_FILE_PATH" ||
   git ls-tree -r --name-only HEAD | grep -Fxq "$SIGNING_CERT_PATH"; then
  echo "::error::A signing identity already exists; refusing to rotate it." >&2
  exit 1
fi
mkdir -p signing
cert_temp="${RUNNER_TEMP:-/tmp}/bootstrap-signing-cert.der"
trap 'rm -f "$cert_temp"' EXIT
keytool -genkeypair -keystore "$SIGNING_FILE_PATH" -storetype PKCS12 \
  -alias "$SIGNING_ALIAS" -keyalg RSA -keysize 3072 -validity 36500 \
  -dname "CN=$SIGNING_APP_LABEL, O=Personal Android App" \
  -storepass:env APP_SIGNING_PASSWORD -keypass:env APP_SIGNING_PASSWORD -noprompt
keytool -exportcert -keystore "$SIGNING_FILE_PATH" -storetype PKCS12 \
  -alias "$SIGNING_ALIAS" -storepass:env APP_SIGNING_PASSWORD -file "$cert_temp" >/dev/null
sha256sum "$cert_temp" | awk '{print $1}' > "$SIGNING_CERT_PATH"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -f -- "$SIGNING_FILE_PATH"
git add -- "$SIGNING_CERT_PATH"
if [[ "$approved_marker" == "true" ]]; then
  git rm -- "$approval_marker"
fi
git commit -m "ci: initialize immutable Android signing identity once"
git push origin HEAD:main
echo "CI_SOURCE_SHA=$(git rev-parse HEAD)" >> "$GITHUB_ENV"
echo "::notice::Signing identity created and certificate pinned. Do not uninstall an existing app until the new APK is published."
