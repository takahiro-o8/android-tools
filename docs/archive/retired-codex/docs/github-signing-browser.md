# GitHubの画面でAndroid署名を設定する

ソフトのインストールやターミナルは不要。各アプリのGitHubリポジトリで、Settings → Secrets and variables → Actions → New repository secretを開く。

既存のSecretsに `SIGNING`、`KEYSTORE`、`KEY_ALIAS`、`KEY_PASSWORD` を含む項目がある場合は、既存鍵を保護するため登録・上書きを行わず、項目名だけを確認する。値やパスワードをチャットに送らない。

- Voice Copy: `VOICE_SIGNING_KEY`、`VOICE_SIGNING_PASSWORD`、`VOICE_SIGNING_CERT_SHA256`
- Traffic Monitor: `TRAFFIC_SIGNING_KEY`、`TRAFFIC_SIGNING_PASSWORD`、`TRAFFIC_SIGNING_CERT_SHA256`

`*_SIGNING_KEY`はPKCS12鍵のBase64テキスト全文、`*_SIGNING_PASSWORD`はその鍵のパスワード、`*_SIGNING_CERT_SHA256`は公開証明書のSHA-256をコロンなし小文字64桁で指定する。各値は別のSecretとして登録する。鍵とパスワードはGitHubのリポジトリ、Issue、チャット、Releaseへ掲載しない。

鍵とパスワードのバックアップを安全な場所に保存する。紛失すると同じ署名でアップデートできなくなる。作業環境が失われてもGitHub Secretsから元の値を読み出すことはできない。

Secrets登録後、対象アプリのActionsで署名とAPK生成を実行し、証明書・アプリID・バージョンを確認後にReleaseへ公開する。旧デバッグ署名版から固定署名版へ移行する際は一度だけ再インストールが必要で、アンインストール時にアプリ内データが消える。固定署名版以降は同じ鍵を維持し、versionCodeを増加させる。
