# 判断の記録(ADR)

## ADR-0001 ビルド・配布・E2E を共通リポジトリにまとめる(2026-10-28)
- オーナー指示: GitHub 上の動作検証を今後のすべてのアプリ・別の AI でも使えるようにする
- 質疑応答で決定: 共通リポジトリ 1 つに集約(名前 android-tools、公開)/ビルド・リリースも共通化/全アプリ共通の AI ルールもここに置く/各アプリは常に `main` を使う/リポジトリはオーナーが作成
- 方式: 再利用ワークフロー(`uses: owner/repo/...@main`)ではなく **composite action** を `actions/checkout` で `${{ github.repository_owner }}/android-tools` から取得して使う。呼び出し側にアカウント名(個人名)を書かずに済むため
- 外部ライブラリなし: E2E は Python 標準ライブラリ + adb + uiautomator dump。ビルドは公式の setup-java / setup-gradle のみ
- 実行タイミング: E2E は手動ボタンか、コミットメッセージに `[e2e]`(AI セッションは Actions API が 403 のため)
- 端末: Android 17(API 37)、KVM 必須(仮想化なしのエミュレーターは使わない — オーナー指示)
- 結果: プレリリース `e2e-report` に report.md と画像(AI は Releases API で読める)
- 影響: android-tools の `main` を壊すと全アプリが止まる。変更後は launcher で確認する
