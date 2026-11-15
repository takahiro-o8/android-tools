# Shared app-development preferences

> **最優先（2026-11-16）**：[android-tools共通方針](https://github.com/takahiro-o8/android-tools/blob/main/docs/APP_BUILD_POLICY.md)を必ず読み、古い開発・検証・言語・SDK・配布の指示より優先する。次回の改修時に自作JavaをすべてKotlinへ移行し、最新版の安定かつ互換性のあるAndroidビルド基盤へ統一する。ビルド成功で完了を確認する。アプリID・既存署名鍵・データ互換性は保持する。


These are the user's preferences for existing and new app development. Apply them to future app projects as well as the current one.

## Android APK delivery (user instruction, 2026-10-24 JST)

- Distribute an installable `.apk` attachment through GitHub Releases.
- In chat, link to the specific **Release page** (`https://github.com/<owner>/<repo>/releases/tag/<tag>`). Tell the user to open it in the GitHub app and tap the APK in **Assets**. This is the established AI Usage workflow.
- Do not present `/releases/download/.../*.apk` as the primary download link: the user reports download failures from those links.
- Do not send an Actions artifact ZIP or ask the user to unzip an APK.
- Verify that the Release exists and contains the APK before sending its page link. Private repositories require the user's signed-in GitHub account.
- Reuse this delivery format when starting a new Android app; do not ask the user to repeat the preference.

Reference example: https://github.com/takahiro-o8/voice-copy/releases/tag/preview-5 (asset: `Voice-Copy.apk`). Use the appropriate verified release for each future build, not this fixed example.

## 共通ウィジェット・フォント仕様（2026-11-03、ユーザー指示）
既存・新規アプリ共通で [docs/WIDGET_STYLE.md](docs/WIDGET_STYLE.md) を適用する。背景は透明、システムのライトモードは黒文字、ダークモードは縁取り付き白文字。壁紙による文字色判定は使わない。アプリUIのフォントはPixelのGoogle Sansを優先し、未搭載端末は標準フォント。正本は [android-toolsの共通仕様](https://github.com/takahiro-o8/android-tools/blob/main/docs/WIDGET_STYLE.md)。過去の異なるウィジェット外観より今回の指定を優先する。

## 全AndroidアプリのMaterial Design（2026-11-06、恒常的なユーザー指示）

既存・新規を問わず、このアプリ・他のアプリ・今後新しく開発するAndroidアプリの全画面と内蔵ビューアーは、常にMaterial Design（現在はMaterial 3）に準拠させる。[全アプリ共通仕様](https://github.com/takahiro-o8/android-tools/blob/main/docs/MATERIAL_DESIGN.md)を適用する。公式コンポーネント、端末のテーマ色、白ベースのライト／黒ベースのダーク、余白・文字階層・角丸・状態表示・アクセシビリティを揃える。2〜5段階の選択は1行のセグメントボタンを基本とする。ウィジェットの透明背景・共通フォントの既存ルールを維持する。Androidの開発言語はKotlin、Gradle Kotlin DSLを標準とする。アプリID・固定署名・保存済みデータの互換性を維持し、コードを改修するときは端末上で確認する。
