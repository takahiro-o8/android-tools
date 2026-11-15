# 全Androidアプリ共通の開発・ビルド方針（2026-11-16）

**唯一の正本**：この文書と[AGENTS.md](../AGENTS.md)、[署名・配布の安全基準](RELEASE_SAFETY.md)。新旧の文書が食い違う場合、ユーザーの最新指示と本書が優先する。Codex・Claude・Cursor・Meta Muse Code・Grok Build・将来のAIのいずれにも適用。AI専用の別リポジトリは不要。

## 個人用アプリの即時本番運用
- 開発は一人で行い、別AIが同じアプリを同時改修しない。AIに依頼した変更が反映されたら**直ちに最新版を本番として使う**。PR、承認、単体テスト・lint・エミュレーターE2Eの常時実行は必要ない。
- mainへのPushで、ビルド成功後に既存固定鍵で正式APKを署名・検証し、GitHub Releasesへ正式版として公開することを目標とする。旧コードのビルド実装がまだこの方針に未移行なら、移行が必要である。
- 失敗したビルドは公開しない。先行ビルドの競合を避け、古いAPKが最新を上書きしないようにする。
- 最新正式APK＋過去2件の計3件だけを残す。版名を変えずに新しいビルドを公開する場合は各公開APKを別の更新版として扱う。古い正式Release・APK・対応タグは削除する。
- 開発版`dev`、診断用`ci-logs`/`e2e-report`、下書きReleaseは今後作成せず、旧分も削除する。診断にはGitHub Actionsの実行ログを利用する。Gitコミットのソース履歴は残す。

## Kotlinと最新版ツールチェーン
- Androidの自作アプリ本体、自作ヘルパー、自作テストを完全Kotlin化。残存自作`.java`は次回そのアプリを改修する際に**Kotlinへ移行して削除**。ラッパーだけをKotlinで書いてJavaを残さない。外部ライブラリや自動生成コードは対象外。
- GradleはKotlin DSLを使用。SDKの`compileSdk`/`targetSdk`、Android Gradle Plugin、Gradle、Kotlin、JDK、依存ライブラリを、**正式安定版かつ組み合わせ互換性のある最新構成**にアプリ間で統一する。alpha/beta/RCを無理に採用しない。
- `minSdk`はPixel 8の発売時OSであるAndroid 14（API 34）を標準下限とする。最新版SDKに合わせて無条件に高くしない。現行Pixel 8が実際に起動することを優先する。
- バージョン変更による権限・通知・バックグラウンド処理の互換性は修正し、ビルド・署名検証成功をもって移行完了とする。書類の更新だけでは移行完了とみなさない。
- アプリID、既存の固定署名鍵、ユーザーデータと更新互換性、アプリ固有の権限・機能は保持する。

## 指示MDとREADMEの統一
- `android-tools/AGENTS.md`と本書を全AI共通の正本とする。各アプリの`AGENTS.md`/`CLAUDE.md`は短い参照と固有事項だけにする。
- AIが別リポジトリの文書を自動で読める保証はない。作業開始時に実際の取得を確認する。取得できないなら適用済みと断言しない。
- READMEは目的、使い方、正式APKのインストール/更新、固有の権限・制約、共通ルールへの参照を基本構成とする。
- [Material Design 3共通仕様](MATERIAL_DESIGN.md)・[ウィジェット仕様](WIDGET_STYLE.md)・[安全な署名・配布](RELEASE_SAFETY.md)を適用する。
- README・古いADRに書かれた旧版の検査/配布条件は当時の履歴として尊重するが、現行運用の根拠にしない。

## 実装の状況（2026-11-16時点）
- 共通指示と3世代整理のGitHub Actionsは全5アプリに導入済み。ただし旧Actionsにも`dev`を作る処理や重い自動テストが一部残るため、各アプリのビルド/配布ワークフロー自体の移行は未完了。
- アプリ別の最新安定SDK・AGP・Gradle・JDKへの実更新は未完了。Kotlin自作Javaの残存は`limitless/tools/widget-host-check/src/main/java/com/aiusage/hostcheck/HostActivity.java`の1ファイルを確認済み。
- 共通削除スクリプトは`scripts/retain-apk-versions.py`。旧リリース処理との競合がないように各アプリのワークフローを移行する。
