# 作業記録

## 2026-10-28 作成
- やったこと: launcher の build.yml を composite action `actions/build` に移し、E2E の仕組み(`actions/e2e`、`e2e/adbtest.py`)と全アプリ共通ルール(AGENTS.md、docs/)を作成。雛形を templates/ に
- 理由: ADR-0001
- 確認: launcher で `[e2e]` 付き push により初回実行(結果は launcher の DEVLOG に記録)
- 未確認: 他のアプリへの適用
