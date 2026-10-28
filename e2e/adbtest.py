"""
adbtest — tiny end-to-end test helper for Android apps, driven only by adb.

Standard library only. An app's test script (e2e/test.py in the app repository) imports this,
defines steps with @step, and calls main(). The shared E2E action (actions/e2e) starts the
emulator, builds the debug APK, runs the script and publishes e2e-out/ to the "e2e-report"
pre-release. See docs/E2E.md.

    from adbtest import *

    @step("起動")
    def start():
        home()
        check(find(desc="ホーム画面"), "ホーム画面が見つからない")
        return "OK"   # optional detail shown in the report

    if __name__ == "__main__":
        main(setup=lambda: install(home_role=True))
"""
import json
import os
import re
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

__all__ = [
    "PKG", "OUT", "APK", "adb", "sh", "shot", "nodes", "find", "find_all", "size",
    "tap", "down", "move", "up", "long_press", "drag", "swipe", "home", "back", "wait_for",
    "run_as_cat", "run_as_json", "set_rotation", "install", "focused", "step", "check", "main",
]

PKG = os.environ.get("E2E_PACKAGE", "")        # application id under test (debug build)
OUT = os.environ.get("E2E_OUT", "e2e-out")     # report + screenshots
APK = os.environ.get("E2E_APK") or (sys.argv[1] if len(sys.argv) > 1 else None)

_results = []   # (title, ok, detail, image)
_steps = []


# ------------------------------------------------------------------ adb

def adb(*args, check=False, timeout=90):
    try:
        r = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"adb {' '.join(args)[:80]} timed out after {timeout}s")
    if check and r.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)} failed: {(r.stderr or r.stdout).strip()}")
    return r.stdout


def sh(cmd):
    """Run a shell command on the device and return stdout."""
    return adb("shell", cmd)


def shot(name):
    """Save a screenshot as OUT/<name>.png and return the file name."""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}.png")
    with open(path, "wb") as f:
        try:
            f.write(subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True, timeout=60).stdout)
        except subprocess.TimeoutExpired:
            pass
    return os.path.basename(path)


# ------------------------------------------------------------------ screen contents

def nodes():
    """Every view on screen (uiautomator dump): dicts with text, desc, cls, pkg, id, l/t/r/b, cx/cy."""
    for _ in range(6):
        out = sh("uiautomator dump /sdcard/ui.xml >/dev/null 2>&1; cat /sdcard/ui.xml")
        if "<hierarchy" in out:
            out = out[out.index("<"):]
            break
        time.sleep(1)  # "could not get idle state" while animating
    else:
        raise RuntimeError("uiautomator dump failed")
    res = []
    for n in ET.fromstring(out).iter("node"):
        l, t, r, b = map(int, re.findall(r"-?\d+", n.get("bounds", "[0,0][0,0]")))
        res.append(dict(text=n.get("text") or "", desc=n.get("content-desc") or "", cls=n.get("class") or "",
                        pkg=n.get("package") or "", id=n.get("resource-id") or "",
                        l=l, t=t, r=r, b=b, cx=(l + r) // 2, cy=(t + b) // 2))
    return res


def size(ns=None):
    """Current screen size in pixels, following rotation."""
    ns = ns if ns is not None else nodes()
    return max(n["r"] for n in ns), max(n["b"] for n in ns)


def find_all(desc=None, text=None, contains=None, cls=None, ns=None):
    ns = ns if ns is not None else nodes()
    w, h = size(ns)
    out = []
    for n in ns:
        if desc is not None and n["desc"] != desc:
            continue
        if text is not None and n["text"] != text:
            continue
        if cls is not None and not n["cls"].endswith(cls):
            continue
        if contains is not None and contains.lower() not in (n["text"] + " " + n["desc"]).lower():
            continue
        if not (0 <= n["cx"] < w and 0 <= n["cy"] < h and n["r"] > n["l"] and n["b"] > n["t"]):
            continue
        out.append(n)
    return out


def find(desc=None, text=None, contains=None, cls=None, ns=None):
    """First visible view matching all given conditions, or None."""
    r = find_all(desc, text, contains, cls, ns)
    return r[0] if r else None


def wait_for(fn, timeout=8.0, interval=0.5):
    """Call fn until it returns something truthy (or the timeout passes); returns the last result."""
    end = time.time() + timeout
    while True:
        r = fn()
        if r or time.time() > end:
            return r
        time.sleep(interval)


def focused():
    """The focused window line from dumpsys (contains the package of the app in front)."""
    return sh("dumpsys window | grep -E 'mCurrentFocus'").strip()


# ------------------------------------------------------------------ input

def tap(x, y):
    sh(f"input tap {int(x)} {int(y)}")


def down(x, y):
    sh(f"input motionevent DOWN {int(x)} {int(y)}")


def move(x, y):
    sh(f"input motionevent MOVE {int(x)} {int(y)}")


def up(x, y):
    sh(f"input motionevent UP {int(x)} {int(y)}")


def long_press(x, y, hold=1.2):
    down(x, y)
    time.sleep(hold)
    up(x, y)


def drag(x1, y1, x2, y2, hold=1.2, steps=8, before_up=None, settle=1.2):
    """Long press at (x1,y1), move to (x2,y2) and release.
    [before_up] is called before releasing and may return a new end point (e.g. a target that
    only appears during the drag)."""
    down(x1, y1)
    time.sleep(hold)
    for i in range(1, steps + 1):
        move(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps)
    if before_up:
        p = before_up()
        if p:
            x2, y2 = p
            move(x2, y2)
    time.sleep(0.4)
    up(x2, y2)
    time.sleep(settle)


def swipe(x1, y1, x2, y2, ms=250):
    sh(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {ms}")
    time.sleep(1.2)


def home():
    sh("input keyevent KEYCODE_HOME")
    time.sleep(1.5)


def back():
    sh("input keyevent KEYCODE_BACK")
    time.sleep(1)


def set_rotation(r):
    """0 = portrait, 1 = landscape (turned left), 2 = upside down, 3 = landscape (turned right)."""
    sh("settings put system accelerometer_rotation 0")
    sh(f"settings put system user_rotation {r}")
    time.sleep(3)


# ------------------------------------------------------------------ app data (debug builds only)

def run_as_cat(path):
    """Read a file in the app's private storage (path relative to its data directory)."""
    return sh(f"run-as {PKG} cat {path}")


def run_as_json(path, default=None):
    out = run_as_cat(path).strip()
    try:
        return json.loads(out)
    except ValueError:
        return default


# ------------------------------------------------------------------ setup

def install(home_role=False, widget_bind=False, permissions=(), animations=0.5):
    """Install the APK and prepare the device. Call from main(setup=...)."""
    adb("wait-for-device", timeout=300)
    if APK:
        adb("install", "-r", "-t", "-g", APK, check=True, timeout=300)
    if home_role:
        sh(f"cmd role add-role-holder --user 0 android.app.role.HOME {PKG}")
    if widget_bind:
        sh(f"appwidget grantbind --package {PKG} --user 0")
    for p in permissions:
        sh(f"pm grant {PKG} {p}")
    for k in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
        sh(f"settings put global {k} {animations}")
    set_rotation(0)
    sh("input keyevent KEYCODE_WAKEUP")
    sh("wm dismiss-keyguard")
    sh("logcat -c")
    home()
    time.sleep(2)


# ------------------------------------------------------------------ steps & report

def check(cond, msg):
    """Fail the current step with [msg] unless [cond] is truthy."""
    if not cond:
        raise AssertionError(msg)
    return cond


def step(title):
    """Decorator: register a test step. Steps run in definition order; one failing step does not
    stop the following ones. Return a string to show it in the report."""
    def wrap(fn):
        _steps.append((title, fn))
        return fn
    return wrap


def _run_step(i, title, fn):
    print(f"--- {i:02d} {title}", flush=True)
    try:
        detail, ok = fn() or "", True
    except Exception as e:  # noqa: BLE001
        detail, ok = f"{e}\n{traceback.format_exc(limit=3)}", False
    img = shot(f"{i:02d}")
    _results.append((title, ok, detail, img))
    print(("PASS " if ok else "FAIL ") + title + (f" — {detail.splitlines()[0]}" if detail else ""), flush=True)


def _crashes():
    try:
        log = adb("logcat", "-d", "-b", "crash")
    except RuntimeError:
        return []
    with open(os.path.join(OUT, "crash.txt"), "w") as f:
        f.write(log)
    return [b for b in log.split("FATAL EXCEPTION")[1:] if PKG and PKG in b]


def _report(crashes):
    passed = sum(1 for r in _results if r[1])
    def prop(k):
        try:
            return sh(f"getprop {k}").strip()
        except RuntimeError:
            return "?"
    lines = ["# E2E レポート", "",
             f"- アプリ: {PKG}",
             f"- 端末: {prop('ro.product.model')} / Android {prop('ro.build.version.release')} (API {prop('ro.build.version.sdk')})",
             f"- コミット: {os.environ.get('GITHUB_SHA', '?')[:7]}",
             f"- 結果: **{passed}/{len(_results)} 成功**" + (f"、**アプリのクラッシュ {len(crashes)} 件**" if crashes else ""),
             "", "| # | 手順 | 結果 | 内容 | 画像 |", "|---|---|---|---|---|"]
    for i, (title, ok, detail, img) in enumerate(_results, 1):
        d = (detail.splitlines()[0] if detail else "").replace("|", "/")
        lines.append(f"| {i} | {title} | {'✅' if ok else '❌'} | {d} | {img} |")
    fails = [r for r in _results if not r[1]]
    if fails:
        lines += ["", "## 失敗の詳細", ""]
        for title, _, detail, img in fails:
            lines += [f"### {title} ({img})", "```", detail.strip(), "```", ""]
    if crashes:
        lines += ["", "## クラッシュ", "", "```", crashes[0].strip()[:4000], "```"]
    with open(os.path.join(OUT, "report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def main(setup=install):
    """Run setup, then every @step, write OUT/report.md and exit non-zero if anything failed."""
    os.makedirs(OUT, exist_ok=True)
    if not PKG:
        sys.exit("E2E_PACKAGE is not set")
    setup()
    for i, (title, fn) in enumerate(_steps, 1):
        _run_step(i, title, fn)
        _report([])
    crashes = _crashes()
    _report(crashes)
    sys.exit(0 if all(r[1] for r in _results) and not crashes else 1)
