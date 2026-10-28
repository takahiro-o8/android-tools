#!/usr/bin/env bash
# Called by actions/build/action.yml. Environment: APP_NAME MODULE KEY_ALIAS KEYSTORE_BASE64
# KEYSTORE_PASSWORD VERSION_FILE CHANGELOG EVENT_NAME GH_TOKEN (+ the usual GITHUB_*).
set -uo pipefail

fail() {  # upload the log to the "ci-logs" pre-release so AI sessions can read it, then stop
  echo "::error::$1"
  log="build-log-${GITHUB_RUN_ID}.txt"
  { echo "$1"; echo; tail -c 900000 build.log 2>/dev/null; } > "$log"
  gh release view ci-logs >/dev/null 2>&1 || \
    gh release create ci-logs --prerelease --title "CI failure logs" --notes "Failed build logs (latest first). Safe to delete."
  gh release upload ci-logs "$log" --clobber
  exit 1
}

name=$(grep '^VERSION_NAME=' "$VERSION_FILE" | cut -d= -f2 | tr -d '[:space:]')
code=$(grep '^VERSION_CODE=' "$VERSION_FILE" | cut -d= -f2 | tr -d '[:space:]')
[ -n "$name" ] && [ -n "$code" ] || fail "$VERSION_FILE needs VERSION_NAME and VERSION_CODE"

# --- signing: only a keystore that contains KEY_ALIAS counts as the release key
signed=false
ks="$RUNNER_TEMP/release.jks"
if [ -n "$KEYSTORE_BASE64" ] && [ -n "$KEYSTORE_PASSWORD" ] \
   && echo "$KEYSTORE_BASE64" | base64 --decode > "$ks" \
   && keytool -list -keystore "$ks" -storepass "$KEYSTORE_PASSWORD" -alias "$KEY_ALIAS" >/dev/null 2>&1; then
  printf 'storeFile=%s\nstorePassword=%s\nkeyAlias=%s\nkeyPassword=%s\n' \
    "$ks" "$KEYSTORE_PASSWORD" "$KEY_ALIAS" "$KEYSTORE_PASSWORD" > keystore.properties
  signed=true
else
  echo "::warning::Release keystore missing or without alias '$KEY_ALIAS' - the APK is debug-signed and cannot update an installed copy."
fi

# --- build
./gradlew ":$MODULE:assembleRelease" --stacktrace 2>&1 | tee build.log
[ "${PIPESTATUS[0]}" -eq 0 ] || fail "Gradle build failed"
apk=$(find "$MODULE/build/outputs/apk/release" -name '*.apk' | head -1)
[ -n "$apk" ] || fail "No APK produced"
rm -f keystore.properties

[ "$EVENT_NAME" = push ] && [ "$GITHUB_REF" = refs/heads/main ] || { echo "Not a main push - nothing to publish."; exit 0; }

# --- rolling "dev" pre-release
dev="$APP_NAME-$name-dev-${GITHUB_SHA::7}.apk"
cp "$apk" "$dev"
note="署名: 本番鍵(上書き更新できます)"
[ "$signed" = true ] || note="署名: 一時的なデバッグ鍵(上書き更新できません。リリース用の Secrets が必要)"
gh release delete dev --yes --cleanup-tag 2>/dev/null || true
gh release create dev --prerelease --target "$GITHUB_SHA" --title "開発版 (main @ ${GITHUB_SHA::7})" \
  --notes "$(printf '開発版(main の最新ビルド)\n\n- コミット: %s\n- バージョン: %s (versionCode %s)\n- %s\n' "$GITHUB_SHA" "$name" "$code" "$note")" \
  "$dev" || fail "Could not publish the dev pre-release"

# --- new version -> tag + release (sessions cannot push tags, so releasing = bump the version)
tag="v$name"
if [ "$signed" != true ]; then echo "Unsigned - no release."; exit 0; fi
if gh release view "$tag" >/dev/null 2>&1; then echo "$tag already released."; exit 0; fi
final="$APP_NAME-$name.apk"
cp "$apk" "$final"
notes=$(awk -v v="## $name" '$0==v{f=1;next} /^## /{f=0} f' "$CHANGELOG" 2>/dev/null)
[ -n "$notes" ] || notes="$APP_NAME $name"
gh release create "$tag" --target "$GITHUB_SHA" --latest --title "$APP_NAME $name" --notes "$notes" "$final" \
  || fail "Could not create release $tag"
