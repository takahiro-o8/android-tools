# Androidアプリの共通ビルド・署名・配布（現行）

## 運用
`main`にコードをPush → `assembleRelease`のみ実行 → **既存固定鍵で署名** → APK証明書・versionCode・versionNameを確認 → 正式GitHub Releaseを作成 → 最新版＋過去2件以外のReleaseと旧補助Releaseを削除する。

- 新しい版をリリースするのに、`VERSION_CODE`や`VERSION_NAME`を毎回手動で増やす必要はない。CIは`versionCode = 100000 + GITHUB_RUN_NUMBER`、`versionName = <基準の版名>.b<実行番号>`を設定する。
- ビルド失敗、署名鍵欠落、証明書不一致、APK版数不一致では公開中止。手動承認・PR・単体テスト・lintを通常の必須条件にしない。E2Eの手順・実行・補助コードは今後一切作らない。
- **古いビルドが新しいコードを上書きしない**よう判定。後続変更がMarkdownのみなら、その直前に作った同じソースのAPKを公開できる。
- `dev`・診断`ci-logs`/`e2e-report`・下書きReleaseは作らない。調査はGitHub Actionsのログを見る。

## 新規アプリの標準方式：Secretはパスワード1項目だけ

この方式は**最初から新しく配布するアプリ**向け。既存4アプリの署名鍵は維持し、勝手に再生成しない。`file`はユーザーが旧版のアンインストールを了承したため例外的にこの方式へ移行する。

1. **非公開GitHubリポジトリ**を使う。`templates/workflows/build.yml`をアプリの`.github/workflows/build.yml`にコピーし、`APP_NAME`（APK名）、`APP_ALIAS`（英数字の鍵名）、`APP_SIGNING_PASSWORD`（GitHub Secretの名前）を各アプリ固有の値に置き換える。`templates/version.properties`と`templates/gitignore.example`も参考にする。
2. GitHub Settings → Secrets and variables → Actions に、**ランダム32文字以上の強いパスワード**を1項目登録する。個別パスワードを覚えたり永久保管したりする代わりに、[PC共通復旧方式](SIGNING_RECOVERY.md)で署名鍵とSecretを暗号化バックアップする。バックアップ取得までは登録したSecretを消去・変更しない。鍵はSecretではなく、パスワード暗号化された`signing/app-release.p12`として非公開Gitに保管される。
3. Actions → Build APK → Run workflow で`initialize_new_key`に**初回のみ**チェック。共通`scripts/bootstrap-signing.sh`が鍵ファイルと公開証明書のSHA-256指紋を作り、Gitにコミット。以降は**鍵を生成しない**。
4. 共通`actions/build`が同一鍵を使い、アプリID・バージョン・署名を検証して正式APKを公開する。以後mainへのコードPushだけで自動更新。鍵パスワードの再登録は不要。
5. 鍵の`.p12`とパスワードを**GitHubとは別に安全にバックアップ**する。パスワードを忘れたりアクセスを失うと将来の上書き更新ができない。

Gradle設定では、固定`applicationId`、API 34以上を標準の`minSdk`にし、CIからバージョンを上書きできるようにする。

```kotlin
defaultConfig {
    applicationId = "com.example.yourapp" // 新規アプリ固有の値。既存アプリでは変更禁止。
    minSdk = 34
    versionCode = providers.environmentVariable("CI_VERSION_CODE").orNull?.toInt()
        ?: versionProps.getProperty("VERSION_CODE").toInt()
    versionName = providers.environmentVariable("CI_VERSION_NAME").orNull
        ?: versionProps.getProperty("VERSION_NAME")
}
```

リリース署名はルート`keystore.properties`の`storeFile`/`storePassword`/`keyAlias`/`keyPassword`を参照し、`keystore.properties`はGitに含めない。

**安全上の違い**：暗号化されたPKCS12をGitに保存するため、リポジトリを取得した攻撃者がオフラインでパスワードを総当たりする余地がある。非公開リポジトリ、十分強いランダムパスワード、アクセス制限、バックアップが必須。パスワード保護されたファイルも安全性がゼロリスクになるわけではない。

## 既存4アプリの方式（変更しない）
Launcher・Limitless・G-widget・LinkAutoDLは各アプリの従来の署名鍵をそのまま利用し、当該リポジトリのGitHub Secretsで設定する。`file`だけは元の鍵を紛失し、アンインストールを明示的に了承したため、新しい署名鍵へ一度移行する。**既存鍵を統一・再生成しない。**

## ライフサイクル
正式リリース直後に、`scripts/retain-apk-versions.py --keep 3 --apply --remove-aux`で保存版数を管理する。コードのGit履歴と署名鍵は削除しない。署名鍵は本人管理の安全な場所にも必ずバックアップする。
