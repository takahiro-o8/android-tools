# android-tools

**全Androidアプリ・全開発AIの共通基盤。** Claude、Codex、Cursor、Meta Muse Code、Grok Build、その他のAIに共通。特定のAIの専用リポジトリは不要。

## ファイルの実体
ここにあるのはAPKそのものではなく、**テキストファイル**です。`.md`は開発ルール・設計資料、`.yml`はGitHub Actionsと共通Action、`.sh`はビルド・配布コマンド、`.py`はビルド後の整理や補助処理です。

## 現在の正本
- [AGENTS.md](AGENTS.md)：すべてのAI向け作業ルール
- [docs/APP_BUILD_POLICY.md](docs/APP_BUILD_POLICY.md)：個人用・即時本番・Kotlin・SDK・3世代保持
- [docs/RELEASE_SAFETY.md](docs/RELEASE_SAFETY.md)：署名証明書・アプリID・versionCode・APK公開前の安全確認
- [docs/SIGNING_BROWSER.md](docs/SIGNING_BROWSER.md)：GitHub画面から署名設定と既存Secretsを確認する方法
- [docs/MATERIAL_DESIGN.md](docs/MATERIAL_DESIGN.md)：全アプリ共通のMaterial 3
- [docs/WIDGET_STYLE.md](docs/WIDGET_STYLE.md)：ウィジェット・Google Sansの仕様とランチャー例外
- [docs/PRINCIPLES.md](docs/PRINCIPLES.md)：設定変更時の状態整合性と依存削減
- [scripts/retain-apk-versions.py](scripts/retain-apk-versions.py)：直近3正式APKを残し旧Releaseを削除する共通スクリプト

## 実装ファイル
- `actions/build/`：**現行の本番専用ビルド処理**。既存鍵で署名して証明書・versionCodeを検証し、成功APKを正式Releaseとして公開・3世代保持する。欠落・不一致なら公開しない。
- `templates/workflows/build.yml`：新規アプリ向けの共通Action呼び出しテンプレート。各アプリで**既存の鍵を初回だけSecretsに登録**する。
- `docs/BUILD.md`：現在のビルド・署名・配布の設定手順。
- `actions/e2e/`、`e2e/`：過去の調査用エミュレーター補助。通常のワークフローは呼び出さない。
- `docs/E2E.md`、`docs/DECISIONS.md`、`docs/DEVLOG.md`：過去の実装・判断の記録であり、現在の正本ではない。

## アプリ側の構成
各アプリの`AGENTS.md`/`CLAUDE.md`は本共通ルールへの参照とアプリ固有の制約だけにし、READMEはそのアプリの使い方を記す。アプリID・既存の署名鍵は共通化しない。
