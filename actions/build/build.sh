#!/usr/bin/env bash
# Build one signed production APK, verify identity, retain only last 3 releases.
set -euo pipefail
umask 077
MODULE="${MODULE:-app}"
APP_NAME="${APP_NAME:?}"
KEY_ALIAS="${KEY_ALIAS:?}"
EXPECTED_APP_ID="${EXPECTED_APP_ID:?An expected Android applicationId is required for production releases}"
test -n "${KEYSTORE_PASSWORD:-}" || {
  echo "::error::Production signing password is required"; exit 1;
}
ks="${RUNNER_TEMP}/production-keystore"
trap 'rm -f "$ks" keystore.properties "$RUNNER_TEMP/signing.der"; rm -rf "$RUNNER_TEMP/release-signer-reference"' EXIT
if [ -n "${KEYSTORE_FILE_PATH:-}" ]; then
  test -s "$KEYSTORE_FILE_PATH" || { echo "::error::Pinned signing keystore is missing"; exit 1; }
  cp "$KEYSTORE_FILE_PATH" "$ks"
  # Password-file mode is reserved for keys created by bootstrap-signing.sh.
  # Match its Unicode-safe PBKDF2 derivation; existing Base64 keystores are untouched.
  KEYSTORE_PASSWORD="$(python3 .android-tools/scripts/derive-signing-password.py KEYSTORE_PASSWORD)"
  export KEYSTORE_PASSWORD
else
  test -n "${KEYSTORE_BASE64:-}" || { echo "::error::Production signing key is missing"; exit 1; }
  printf '%s' "$KEYSTORE_BASE64" | base64 --decode > "$ks"
fi
keytool -list -keystore "$ks" -storepass:env KEYSTORE_PASSWORD -alias "$KEY_ALIAS" >/dev/null
keytool -exportcert -keystore "$ks" -storepass:env KEYSTORE_PASSWORD -alias "$KEY_ALIAS" -file "$RUNNER_TEMP/signing.der" >/dev/null
approved=$(sha256sum "$RUNNER_TEMP/signing.der" | cut -d' ' -f1)
if [ -n "${EXPECTED_CERT_FILE:-}" ]; then
  test -s "$EXPECTED_CERT_FILE" || { echo "::error::Pinned signing certificate digest is missing"; exit 1; }
  EXPECTED_CERT=$(tr -d '[:space:]:' < "$EXPECTED_CERT_FILE")
fi
if [ -n "${EXPECTED_CERT:-}" ] && [ "${approved,,}" != "${EXPECTED_CERT,,}" ]; then
  echo "::error::Certificate differs from approved signing identity"; exit 1
fi
# Legacy apps without a pinned fingerprint must match the certificate embedded
# in their most recent *published APK*, not merely the configured secret.
# Once pinned, this one-time historical APK download is no longer needed.
if [ -z "${EXPECTED_CERT:-}" ]; then
  prior_tag="$(gh api "repos/$GH_REPO/releases?per_page=100" --jq '[.[] | select(.draft == false and .prerelease == false) | select(any(.assets[]?; .name | ascii_downcase | endswith(".apk")))] | sort_by(.published_at // .created_at) | last | .tag_name // empty')"
  if [ -z "$prior_tag" ]; then
    echo "::error::No previous production APK or pinned signing certificate; refusing unverified signing identity."
    exit 1
  fi
  previous_dir="$RUNNER_TEMP/release-signer-reference"
  mkdir -p "$previous_dir"
  gh release download "$prior_tag" --repo "$GH_REPO" --pattern '*.apk' --dir "$previous_dir"
  mapfile -t previous_apks < <(find "$previous_dir" -maxdepth 1 -type f -iname '*.apk')
  if [ "${#previous_apks[@]}" -ne 1 ]; then
    echo "::error::Expected exactly one previous APK to verify signing lineage."
    exit 1
  fi
  old_cert="$("$ANDROID_HOME/build-tools/37.0.0/apksigner" verify --print-certs "${previous_apks[0]}" | python3 -c 'import re,sys; text=sys.stdin.read(); lines=[x for x in text.splitlines() if "certificate" in x.lower() and "sha-256" in x.lower()]; m=next((re.search(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])",x) for x in lines if re.search(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])",x)),None); print(m.group(0) if m else "")')"
  if [ -z "$old_cert" ]; then
    echo "::error::Could not parse SHA-256 certificate fingerprint from the published APK. Do not infer a signing mismatch."
    exit 1
  fi
  if [ "${old_cert,,}" != "${approved,,}" ]; then
    echo "::error::Signing identity mismatch: published APK fingerprint=$old_cert; configured keystore fingerprint=$approved."
    exit 1
  fi
  echo "::notice::Legacy release certificate verified against $prior_tag. Pin certificate SHA-256 in the app workflow: $approved"
fi
if [ "${SIGNING_MODE:-properties}" = env ]; then
  export AI_USAGE_KEYSTORE_FILE="$ks"
  export ANDROID_KEYSTORE_PASSWORD="$KEYSTORE_PASSWORD"
  export ANDROID_KEY_ALIAS="$KEY_ALIAS"
  export ANDROID_KEY_PASSWORD="${KEY_PASSWORD:-$KEYSTORE_PASSWORD}"
else
  export SIGNING_FILE="$ks"
  python3 - <<'PY'
import os
from pathlib import Path
def esc(s):
    if '\n' in s or '\r' in s: raise ValueError("Newlines not permitted in signing properties")
    return ''.join('\\' + c if c in '\\ =:#!' else c for c in s)
p = {"storeFile": os.environ["SIGNING_FILE"],
     "storePassword": os.environ["KEYSTORE_PASSWORD"],
     "keyAlias": os.environ["KEY_ALIAS"],
     "keyPassword": os.environ.get("KEY_PASSWORD") or os.environ["KEYSTORE_PASSWORD"]}
Path("keystore.properties").write_text(''.join(k+'='+esc(v)+'\n' for k,v in p.items()))
PY
fi
export CI_VERSION_CODE="$((100000 + GITHUB_RUN_NUMBER))"
export AI_USAGE_VERSION_CODE="$CI_VERSION_CODE"
export CI_VERSION_NAME
CI_VERSION_NAME=$(python3 - <<'PY'
from pathlib import Path
import re, os
f = Path("version.properties")
s = f.read_text() if f.exists() else Path(os.environ.get("MODULE", "app")+"/build.gradle.kts").read_text()
m = re.search(r'(?:VERSION_NAME\s*=\s*|versionName\s*=\s*")(\d+\.\d+\.\d+)', s)
if not m: raise SystemExit("No base VERSION_NAME")
print(m.group(1) + ".b" + os.environ["GITHUB_RUN_NUMBER"])
PY
)
echo "Assembling $APP_NAME $CI_VERSION_NAME ($CI_VERSION_CODE)"
if [ -f gradlew ]; then bash ./gradlew ":$MODULE:assembleRelease" --no-daemon; else gradle ":$MODULE:assembleRelease" --no-daemon; fi
apk=$(find "$MODULE/build/outputs/apk/release" -name '*.apk' -type f | head -1)
test -n "$apk" && test -s "$apk" || { echo "::error::Release APK not found"; exit 1; }
tools="$ANDROID_HOME/build-tools/37.0.0"
"$tools/apksigner" verify --print-certs "$apk" > "$RUNNER_TEMP/apk-signature.txt"
grep -Fqi "$approved" "$RUNNER_TEMP/apk-signature.txt" || { echo "::error::APK signing certificate mismatch"; exit 1; }
# Verify the exact Android package name and CI version against the *actual APK*
# after signing. The lineage tool also compares the numeric versionCode against
# every retained published APK, downloading older assets only when needed.
source_sha="${CI_SOURCE_SHA:-$GITHUB_SHA}"
main_sha=$(git ls-remote origin refs/heads/main | cut -f1)
if [ -z "$main_sha" ]; then
  echo "::error::Cannot verify the latest main commit"; exit 1
fi
if [ "$main_sha" != "$source_sha" ]; then
  # Documentation-only follow-up commits must not prevent an already-built APK
  # from reaching production. Changes to code/workflows still supersede it.
  git fetch --no-tags --depth=1 origin main >/dev/null
  changed=$(git diff --name-only --no-renames "$source_sha" FETCH_HEAD) || {
    echo "::error::Could not compare current main to this build"; exit 1;
  }
  if printf '%s\n' "$changed" | grep -Ev '(^$|\.md$)' >/dev/null; then
    echo "::notice::Newer code/configuration commit exists; skip obsolete APK."
    exit 0
  fi
  echo "::notice::Only Markdown changed on main; publishing the verified APK from $GITHUB_SHA."
fi
# Final release gate. Existing formal APKs must have the same applicationId
# and strictly lower actual versionCodes. Legacy release APKs are inspected;
# subsequent releases record verified metadata to minimize redundant downloads.
python3 .android-tools/scripts/verify-release-lineage.py \
  --candidate "$apk" --aapt "$tools/aapt" \
  --expected-package "$EXPECTED_APP_ID" \
  --expected-code "$CI_VERSION_CODE" \
  --expected-name "$CI_VERSION_NAME" \
  --repo "$GH_REPO"
name="$APP_NAME-$CI_VERSION_NAME.apk"
cp "$apk" "$name"
tag="build-$GITHUB_RUN_NUMBER"
if gh release view "$tag" >/dev/null 2>&1; then echo "::error::Release already exists"; exit 1; fi
gh release create "$tag" "$name" --target "$source_sha" --title "$APP_NAME $CI_VERSION_NAME" \
  --notes "$(printf 'Signed production APK from %s\nVerified-APK: package=%s; versionCode=%s; versionName=%s' "$source_sha" "$EXPECTED_APP_ID" "$CI_VERSION_CODE" "$CI_VERSION_NAME")" --latest
echo "Published https://github.com/$GH_REPO/releases/tag/$tag"
python3 .android-tools/scripts/retain-apk-versions.py --keep 3 --apply --remove-aux
