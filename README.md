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

## 実装ファイル（旧方式を含む）
- `actions/build/`：GitHub Actionsから呼び出す旧ビルド・配布処理。**現在の「正式APKだけ公開する」方針とは未統一で、移行作業が必要**。
- `actions/e2e/`、`e2e/`：従来のエミュレーター検査。個人用運用では通常の自動検査から除外する方針。
- `templates/`：従来の新規アプリ作成用雛形。旧方式であるため、採用前に現行ポリシーとの整合を確認する。
- `docs/BUILD.md`、`docs/E2E.md`、`docs/DECISIONS.md`、`docs/DEVLOG.md`：旧実装の説明・履歴。現行方針と矛盾する場合は上の正本が優先。

## アプリ側の構成
各アプリの`AGENTS.md`/`CLAUDE.md`は本共通ルールへの参照とアプリ固有の制約だけにし、READMEはそのアプリの使い方を記す。アプリID・既存の署名鍵は共通化しない。
