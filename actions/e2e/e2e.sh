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
sudo udevadm settle --timeout=30 || true
[ -e /dev/kvm ] && [ ! -w /dev/kvm ] && sudo chmod 666 /dev/kvm
[ -w /dev/kvm ] || die "KVM is not available on this runner ($(ls -l /dev/kvm 2>&1); $(grep -cE 'vmx|svm' /proc/cpuinfo) CPUs with virtualization)"

# Free disk space on the runner (preinstalled toolchains this job never uses).
sudo rm -rf /usr/share/dotnet /opt/ghc /usr/local/.ghcup /usr/local/share/boost /usr/share/swift \
  /usr/local/lib/node_modules /opt/hostedtoolcache/CodeQL 2>/dev/null || true
echo "Free disk: $(df -h "$HOME" | awk 'NR==2{print $4}')"

SDK="${ANDROID_HOME:-$ANDROID_SDK_ROOT}"
BIN="$SDK/cmdline-tools/latest/bin"
yes | "$BIN/sdkmanager" --licenses >/dev/null 2>&1
echo "::group::Install emulator and $IMAGE"
timeout 900 "$BIN/sdkmanager" --install emulator platform-tools "$IMAGE" > sdk.log 2>&1 || { cat sdk.log; die "sdkmanager could not install $IMAGE"; }
echo "::endgroup::"
export PATH="$SDK/platform-tools:$SDK/emulator:$PATH"
# Fix the AVD location: avdmanager and the emulator otherwise disagree on newer runner images.
export ANDROID_AVD_HOME="$HOME/.android/avd"
mkdir -p "$ANDROID_AVD_HOME"
echo no | "$BIN/avdmanager" create avd -n e2e -k "$IMAGE" -d "$DEVICE" --force >/dev/null || die "avdmanager failed"
[ -f "$ANDROID_AVD_HOME/e2e.avd/config.ini" ] || die "AVD was not created in $ANDROID_AVD_HOME ($(emulator -list-avds 2>&1 | tr '\n' ' '))"
printf 'hw.ramSize=4096\ndisk.dataPartition.size=2G\nhw.keyboard=yes\nhw.cpu.ncore=2\n' >> "$ANDROID_AVD_HOME/e2e.avd/config.ini"
# GPU modes to try in order until the screen can be captured (docs/E2E.md: API 37 images abort
# in screencap/surfaceflinger with emulator 37.2 in every mode, so the default is API 36).
MODES=("${GPU:-swiftshader_indirect}|")
for m in swiftshader_indirect swangle_indirect guest; do [ "$m" = "${GPU:-swiftshader_indirect}" ] || MODES+=("$m|"); done

start_emulator() {  # $1 = gpu mode, $2 = extra flags
  adb emu kill >/dev/null 2>&1; sleep 3; pkill -f qemu-system >/dev/null 2>&1; sleep 2
  echo "Starting emulator: -gpu $1 $2"
  # shellcheck disable=SC2086
  emulator -avd e2e -no-metrics -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data -gpu "$1" $2 \
    -camera-back none -camera-front none > emulator.log 2>&1 &
  emu=$!
  sleep 15
  kill -0 "$emu" 2>/dev/null || { cat emulator.log; cp emulator.log "$OUT/emulator-log.txt"; die "Emulator exited right after start"; }
}

wait_boot() {
  timeout 300 adb wait-for-device || return 1
  for _ in $(seq 1 120); do
    [ "$(timeout 20 adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && { sleep 15; return 0; }
    sleep 5
  done
  return 1
}

screen_ok() {  # screencap must work, otherwise every step fails
  timeout 60 adb exec-out screencap -p > "$OUT/boot.png" 2>/dev/null
  [ "$(stat -c%s "$OUT/boot.png" 2>/dev/null || echo 0)" -gt 10000 ]
}

start_emulator "${MODES[0]%%|*}" "${MODES[0]#*|}"

# --- build the debug APK while the emulator boots
echo "Building debug APK"
timeout 1200 ./gradlew ":$MODULE:assembleDebug" --stacktrace > build.log 2>&1 || { tail -100 build.log; cp build.log "$OUT/build-log.txt"; die "Debug build failed"; }
apk=$(find "$MODULE/build/outputs/apk/debug" -name '*.apk' | head -1)
[ -n "$apk" ] || die "No debug APK"

ok=""
for i in "${!MODES[@]}"; do
  mode="${MODES[$i]%%|*}"; extra="${MODES[$i]#*|}"
  [ "$i" -gt 0 ] && start_emulator "$mode" "$extra"
  echo "::group::Boot emulator (-gpu $mode $extra)"
  if wait_boot && screen_ok; then ok="-gpu $mode $extra"; echo "::endgroup::"; break; fi
  echo "::endgroup::"
  echo "::warning::Screen not usable with -gpu $mode $extra"
  adb logcat -d -b crash > "$OUT/crash-$mode.txt" 2>/dev/null
  cp emulator.log "$OUT/emulator-log-$mode.txt"
done
[ -n "$ok" ] || die "Screen capture does not work with any GPU mode (${MODES[*]})"
echo "Using emulator $ok"
echo "$ok" > "$OUT/emulator-mode.txt"

# --- run the app's test script
# Hard limit so a hang still publishes a (partial) report before the job timeout.
E2E_PACKAGE="$APP_ID" E2E_OUT="$OUT" E2E_APK="$apk" PYTHONPATH="$LIB" \
  timeout --kill-after=30 "${E2E_TIMEOUT:-1500}" python3 -u "$TEST" 2>&1 | tee e2e.log
status=${PIPESTATUS[0]}
[ "$status" -eq 124 ] && echo "**途中で時間切れ(${E2E_TIMEOUT:-1500} 秒)。最後の手順で止まった可能性**" >> "$OUT/report.md"
publish "test script exited with $status"
[ "$status" -eq 0 ] || { echo "::error::E2E failed - see the e2e-report pre-release"; exit 1; }
