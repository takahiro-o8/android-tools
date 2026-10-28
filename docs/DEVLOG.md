# 作業記録

## 2026-10-28 3 回目: インストールが「Broken pipe」で失敗 → 修正
- 原因: 起動完了直後はパッケージサービスが未準備
- 対処: `pm path android` が返るまで待ち、インストールを最大 5 回再試行。準備で失敗してもレポートに「準備」の失敗として出す

## 2026-10-28 2 回目: エミュレーターが容量不足で終了 → 修正
- 原因: データ領域 6G 指定で「Not enough space to create userdata partition(空き 4.3GB、必要 7.3GB)」
- 対処: データ領域を 2G に、ランナーの不要なツール(dotnet・ghc・boost など)を削除して空きを確保、`-no-metrics`

## 2026-10-28 初回 E2E が 60 分で打ち切り → 修正
- 原因: avdmanager が AVD を `~/.android/avd` 以外に作り、エミュレーターが起動しないまま `adb wait-for-device` が無限に待った
- 対処: `ANDROID_AVD_HOME` を固定し作成を確認、起動直後に落ちたら即失敗。すべての adb 呼び出しと各段階に時間制限、テストは 25 分で打ち切り、手順ごとにレポートを書くので打ち切られても途中結果を公開する

## 2026-10-28 作成
- やったこと: launcher の build.yml を composite action `actions/build` に移し、E2E の仕組み(`actions/e2e`、`e2e/adbtest.py`)と全アプリ共通ルール(AGENTS.md、docs/)を作成。雛形を templates/ に
- 理由: ADR-0001
- 確認: launcher で `[e2e]` 付き push により初回実行(結果は launcher の DEVLOG に記録)
- 未確認: 他のアプリへの適用
