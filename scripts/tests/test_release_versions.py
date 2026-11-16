"""Local-only policy regression checks. No Android build, emulator or GitHub I/O."""
import json
import contextlib
import io
import runpy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_versions import ApkVersion, MAX_CODE, next_version, published_apks, semantic, verify_candidate

PACKAGE = "com.example.app"


def apk(name, code):
    return ApkVersion(PACKAGE, code, name)


def release(name="1.4.0.b11", code=100011, **changes):
    result = {"id": 1, "tag_name": "misleading-tag-999", "name": "Misleading 99.0.0", "assets": [{"id": 2, "name": "app.apk"}],
              "body": f"Verified-APK: package={PACKAGE}; versionCode={code}; versionName={name}"}
    result.update(changes)
    return result


class VersionPolicy(unittest.TestCase):
    def test_first_release_uses_requested_version_and_floor(self):
        self.assertEqual(next_version("1.0.0", 7, []), (7, "1.0.0"))

    def test_migrates_all_six_current_app_versions(self):
        for before, after, code in [("4.0.0.b70", "4.0.1", 100070), ("3.7.0.b173", "3.7.1", 100173),
                                    ("1.4.0.b11", "1.4.1", 100011), ("0.3.1.b22", "0.3.2", 100022),
                                    ("2.2.2.b20", "2.2.3", 100020), ("0.1.0.b6", "0.1.1", 100006)]:
            with self.subTest(before=before):
                self.assertEqual(next_version(before.split(".b")[0], 1, [apk(before, code)]), (code + 1, after))

    def test_numeric_order_not_lexical_or_history_order(self):
        history = [apk("2.10.9", 100007), apk("2.9.100", 100008), apk("2.10.10.b2", 100006)]
        self.assertEqual(next_version("2.2.0", 1, history), (100009, "2.10.11"))

    def test_explicit_minor_or_major_bump_is_preserved(self):
        for requested in ["1.5.0", "2.0.0"]:
            self.assertEqual(next_version(requested, 1, [apk("1.4.99", 42)]), (43, requested))

    def test_unpublished_retry_does_not_consume_a_version(self):
        history = [apk("1.0.0", 100100)]
        self.assertEqual(next_version("1.0.0", 1, history), (100101, "1.0.1"))
        self.assertEqual(next_version("1.0.0", 1, history), (100101, "1.0.1"))
        self.assertEqual(next_version("1.0.0", 1, history + [apk("1.0.1", 100101)]), (100102, "1.0.2"))

    def test_explicit_code_floor_never_goes_backwards(self):
        self.assertEqual(next_version("1.0.0", 300, [apk("1.0.0.b9999", 250)]), (300, "1.0.1"))

    def test_only_canonical_three_integer_components_allowed(self):
        for name in ["1.2", "1.2.3.4", "1.2.3.b4", "1.2.3-beta", "v1.2.3", "01.2.3", "-1.2.3", "1.2.3\n"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                semantic(name)
        self.assertEqual(semantic("1.2.3.b173", legacy=True), (1, 2, 3))
        with self.assertRaises(ValueError):
            semantic("1.2.3-beta", legacy=True)

    def test_android_integer_limit_is_enforced(self):
        for floor in [0, -1, MAX_CODE + 1]:
            with self.assertRaises(ValueError):
                next_version("1.0.0", floor, [])
        with self.assertRaises(ValueError):
            next_version("1.0.0", 1, [apk("1.0.0", MAX_CODE)])

    def test_signed_manifest_and_expected_identity_must_match(self):
        with self.assertRaises(ValueError):
            verify_candidate(ApkVersion("com.other.app", 101, "1.0.1"), apk("1.0.1", 101), [])

    def test_both_display_name_and_android_code_must_increase(self):
        for candidate in [apk("1.0.0", 101), apk("0.9.99", 101), apk("1.0.1", 100), apk("1.0.1.b7", 101)]:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                verify_candidate(candidate, candidate, [apk("1.0.0.b6", 100)])
        verify_candidate(apk("1.0.1", 101), apk("1.0.1", 101), [apk("1.0.0.b6", 100)])

    def test_final_gate_rejects_another_release_since_selection(self):
        planned = apk("1.0.1", 101)
        with self.assertRaises(ValueError):
            verify_candidate(planned, planned, [apk("1.0.0", 100), apk("1.0.1", 101)])

    def test_history_metadata_avoids_apk_downloads_and_ignores_titles(self):
        with patch("release_versions.command", return_value=json.dumps([release()])) as call:
            self.assertEqual(published_apks("owner/repo", PACKAGE, "aapt"), [apk("1.4.0.b11", 100011)])
            self.assertEqual(call.call_count, 1)

    def test_auxiliary_releases_do_not_consume_versions(self):
        rows = [release(draft=True), release(prerelease=True), release(assets=[])]
        with patch("release_versions.command", return_value=json.dumps(rows)):
            self.assertEqual(published_apks("owner/repo", PACKAGE, "aapt"), [])

    def test_wrong_package_unreadable_history_and_truncated_page_stop(self):
        for rows in [{"error": "denied"}, [release()] * 100, [release(body="Verified-APK: package=com.other.app; versionCode=4; versionName=1.0.0")]]:
            with patch("release_versions.command", return_value=json.dumps(rows)), self.assertRaises(ValueError):
                published_apks("owner/repo", PACKAGE, "aapt")


    def test_duplicate_guard_uses_max_code_not_latest_publication(self):
        script = Path(__file__).resolve().parents[1] / "skip-duplicate-release.py"
        main = runpy.run_path(str(script))["main"]
        current = "a" * 40
        older = release(code=100009, published_at="2099-01-01")
        newer = release(code=100011, published_at="2000-01-01")
        older["body"] += "\nSigned production APK from " + "b" * 40
        newer["body"] += "\nSigned production APK from " + current
        def command(*args):
            self.assertEqual(args[0], "gh", "A duplicate must not fetch git objects or rebuild")
            return json.dumps([[older, newer]])
        with patch.dict(main.__globals__, {"command": command}), patch.object(sys, "argv", [str(script), "--repo", "owner/repo", "--expected-package", PACKAGE, "--source-sha", current]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 0)

    def test_old_metadata_less_release_uses_actual_apk(self):
        def command(args):
            if args[:2] == ["gh", "api"]:
                return json.dumps([release(body="Legacy title 9.9.9")])
            directory = Path(args[args.index("--dir") + 1])
            (directory / "app.apk").write_bytes(b"x" * 100)
            return ""
        with patch("release_versions.command", side_effect=command), patch("release_versions.manifest", return_value=apk("1.4.0", 18)):
            self.assertEqual(published_apks("owner/repo", PACKAGE, "aapt"), [apk("1.4.0", 18)])


if __name__ == "__main__":
    unittest.main()
