# GitHubのブラウザ画面による署名鍵設定・確認

Android Studioやターミナルの追加インストールを前提としない。**既存アプリの鍵を新たに作る手順ではない。**

1. 対象アプリのGitHubリポジトリを開き、**Settings → Secrets and variables → Actions**を開く。
2. 既存のSecrets一覧に`SIGNING`、`KEYSTORE`、`KEY_ALIAS`、`KEY_PASSWORD`等を含む名前があるか確認する。値は表示・取得できない。既存鍵がある場合は上書きも再生成もしない。
3. アプリ固有の`.github/workflows/`と`docs/SIGNING.md`等で、**現在実際に使う**Secret名・鍵形式（JKS/PKCS12）・エイリアスを確認する。古い別アプリの例示名を流用しない。
4. **新規アプリで鍵を準備済みの場合に限り**、画面の **New repository secret**から必要な値を1項目ずつ登録する。値は端末に安全に保管した鍵のBase64文字列・パスワードなどであり、チャットに貼らない。
5. 一度登録したSecretはGitHubから取り戻せないため、**鍵ファイルとパスワードをGitHubとは別の安全な場所にバックアップ**する。
6. GitHub Actionsが署名済みAPKのアプリID・証明書・versionCodeをチェックし、成功した配布版がRelease Assetsにあることを確認する。

既存正式版との証明書不一致は更新不能になるため、本人による明示的な再インストール方針が決まるまで配布を停止する。APKの実機更新はAPK構造の確認とは別である。[正式APKの検証方針](RELEASE_SAFETY.md)。
