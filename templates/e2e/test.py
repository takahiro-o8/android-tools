#!/usr/bin/env python3
"""E2E steps for this app. Shared helpers: android-tools/e2e/adbtest.py (see docs/E2E.md there)."""
from adbtest import *


@step("起動する")
def start():
    sh(f"monkey -p {PKG} -c android.intent.category.LAUNCHER 1")
    check(wait_for(lambda: PKG in focused()), "アプリが前面に出ない")
    return focused()


if __name__ == "__main__":
    main(setup=install)
