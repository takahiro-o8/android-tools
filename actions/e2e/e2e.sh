#!/usr/bin/env bash
# Called by actions/e2e/action.yml. Environment: APP_ID MODULE TEST IMAGE DEVICE LIB GH_TOKEN.
set -uo pipefail
OUT="$PWD/e2e-out"
mkdir -p "$OUT"

publish() {  # replace the "e2e-report" pre-release with this run's report and screenshots
  [ -f "$OUT/report.md" ] || printf '# E2E レポート\n\n**テストを実行できませんでした:** %s\n' "$1" > "$OUT/report.md"
  cp e2e.log "$OUT/e2e-log.txt" 2>/dev/null || true
  shopt -s nullglob
  files=("$OUT"/*.md "$OUT"/*.png "$OUT"/*.txt)
  gh release delete e2e-report --yes --cleanup-tag 2>/dev/null || true
  gh release create e2e-report --prerelease --target "$GITHUB_SHA" \
    --title "E2E レポート (${GITHUB_SHA::7})" --notes-file "$OUT/report.md" "${files[@]}"
}
die() { echo "::error::$1"; publish "$1"; exit 1; }

# --- emulator (KVM is required; never run the slow non-accelerated emulator)
echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules >/dev/null
sudo udevadm control --reload-rules && sudo udevadm trigger --name-match=kvm
[ -w /dev/kvm ] || die "KVM is not available on this runner"

SDK="${ANDROID_HOME:-$ANDROID_SDK_ROOT}"
BIN="$SDK/cmdline-tools/latest/bin"
yes | "$BIN/sdkmanager" --licenses >/dev/null 2>&1
"$BIN/sdkmanager" --install emulator platform-tools "$IMAGE" > sdk.log 2>&1 || { cat sdk.log; die "sdkmanager could not install $IMAGE"; }
export PATH="$SDK/platform-tools:$SDK/emulator:$PATH"
echo no | "$BIN/avdmanager" create avd -n e2e -k "$IMAGE" -d "$DEVICE" --force >/dev/null || die "avdmanager failed"
printf 'hw.ramSize=4096\ndisk.dataPartition.size=6G\nhw.keyboard=yes\n' >> "$HOME/.android/avd/e2e.avd/config.ini"
emulator -avd e2e -no-window -no-audio -no-boot-anim -no-snapshot -gpu swiftshader_indirect \
  -camera-back none -camera-front none > emulator.log 2>&1 &

# --- build the debug APK while the emulator boots
./gradlew ":$MODULE:assembleDebug" --stacktrace > build.log 2>&1 || { tail -100 build.log; cp build.log "$OUT/build-log.txt"; die "Debug build failed"; }
apk=$(find "$MODULE/build/outputs/apk/debug" -name '*.apk' | head -1)
[ -n "$apk" ] || die "No debug APK"

adb wait-for-device
for i in $(seq 1 120); do
  [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && break
  sleep 5
done
[ "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1 ] || { tail -50 emulator.log; die "Emulator did not boot"; }
sleep 10

# --- run the app's test script
E2E_PACKAGE="$APP_ID" E2E_OUT="$OUT" E2E_APK="$apk" PYTHONPATH="$LIB" \
  python3 -u "$TEST" 2>&1 | tee e2e.log
status=${PIPESTATUS[0]}
publish "test script exited with $status"
[ "$status" -eq 0 ] || { echo "::error::E2E failed - see the e2e-report pre-release"; exit 1; }
