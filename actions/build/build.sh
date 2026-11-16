#!/usr/bin/env bash
# Build one signed production APK, verify identity, retain only last 3 releases.
set -euo pipefail
umask 077
MODULE="${MODULE:-app}"
APP_NAME="${APP_NAME:?}"
KEY_ALIAS="${KEY_ALIAS:?}"
test -n "${KEYSTORE_PASSWORD:-}" || {
  echo "::error::Production signing password is required"; exit 1;
}
ks="${RUNNER_TEMP}/production-keystore"
trap 'rm -f "$ks" keystore.properties "$RUNNER_TEMP/signing.der"' EXIT
if [ -n "${KEYSTORE_FILE_PATH:-}" ]; then
  test -s "$KEYSTORE_FILE_PATH" || { echo "::error::Pinned signing keystore is missing"; exit 1; }
  cp "$KEYSTORE_FILE_PATH" "$ks"
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
details=$("$tools/aapt" dump badging "$apk" | head -1)
case "$details" in *"versionCode='$CI_VERSION_CODE'"*"versionName='$CI_VERSION_NAME'"*) ;; *) echo "::error::APK version does not match CI version"; exit 1;; esac
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
name="$APP_NAME-$CI_VERSION_NAME.apk"
cp "$apk" "$name"
tag="build-$GITHUB_RUN_NUMBER"
if gh release view "$tag" >/dev/null 2>&1; then echo "::error::Release already exists"; exit 1; fi
gh release create "$tag" "$name" --target "$source_sha" --title "$APP_NAME $CI_VERSION_NAME" --notes "Signed production APK from $source_sha" --latest
echo "Published https://github.com/$GH_REPO/releases/tag/$tag"
python3 .android-tools/scripts/retain-apk-versions.py --keep 3 --apply --remove-aux
