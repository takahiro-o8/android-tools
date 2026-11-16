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
- `scripts/bootstrap-signing.sh`：新規アプリで固定署名鍵を初回だけ自動生成する。個別の強いパスワードSecret1つが必要。
- E2E用のAction・テスト・手順書は完全撤去済み。今後も作成しない。過去のE2E履歴はGit履歴でのみ参照する。
- `docs/DECISIONS.md`：現行方針に関する判断の記録。

## アプリ側の構成
各アプリの`AGENTS.md`/`CLAUDE.md`は本共通ルールへの参照とアプリ固有の制約だけにし、READMEはそのアプリの使い方を記す。アプリID・既存の署名鍵は共通化しない。

## 新規アプリの簡単な署名設定

新規の非公開リポジトリには[build.ymlテンプレート](templates/workflows/build.yml)を使い、[初回設定](docs/SIGNING_BROWSER.md)で強いパスワードSecretを1つ登録する。初回のRun workflowだけ鍵を作成。次回以降は同じ鍵で自動的に正式APKを公開する。既存4アプリは現在の鍵を維持。

## 署名鍵の復旧（個別パスワードの記憶不要）

[5アプリ共通・PCの復旧用鍵による暗号化バックアップ手順](docs/SIGNING_RECOVERY.md)。既存アプリの鍵は変更しない。バックアップ用Actionsは手動起動のみで、Androidビルド・E2Eを実行しない。復旧用秘密鍵ファイルのバックアップは必須。
