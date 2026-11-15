# Androidアプリの共通ビルド・署名・配布（現行）

## 運用
`main`にコードをPush → `assembleRelease`のみ実行 → **既存固定鍵で署名** → APK証明書・versionCode・versionNameを確認 → 正式GitHub Releaseを作成 → 最新版＋過去2件以外のReleaseと旧補助Releaseを削除する。

- 新しい版をリリースするのに、`VERSION_CODE`や`VERSION_NAME`を毎回手動で増やす必要はない。CIは`versionCode = 100000 + GITHUB_RUN_NUMBER`、`versionName = <基準の版名>.b<実行番号>`を設定する。
- ビルド失敗、署名鍵欠落、証明書不一致、APK版数不一致では公開中止。手動承認・PR・単体テスト・lint・エミュレーターE2Eを必須条件にしない。
- **古いビルドが新しいコードを上書きしない**よう判定。後続変更がMarkdownのみなら、その直前に作った同じソースのAPKを公開できる。
- `dev`・診断`ci-logs`/`e2e-report`・下書きReleaseは作らない。調査はGitHub Actionsのログを見る。

## 新規アプリでの初回設定（1回だけ）
1. `templates/workflows/build.yml`をアプリの`.github/workflows/build.yml`へコピーし、`APP_NAME`、`APP_KEY_ALIAS`、Secretsの`APP`という仮名を固有の名前に変更する。
2. AndroidアプリのGradle設定（Kotlin DSL、共通の互換最新版SDK/AGP/Gradle/JDK）に、`version.properties`等を元にした通常のバージョンとCI環境変数による上書きを記述する：

```kotlin
defaultConfig {
    applicationId = "com.example.yourapp" // 他アプリと重複不可。既存アプリでは変更禁止。
    minSdk = 34 // Pixel 8を前提
    versionCode = providers.environmentVariable("CI_VERSION_CODE").orNull?.toInt()
        ?: versionProps.getProperty("VERSION_CODE").toInt()
    versionName = providers.environmentVariable("CI_VERSION_NAME").orNull
        ?: versionProps.getProperty("VERSION_NAME")
}
```

3. リリース署名にはルート`keystore.properties`の`storeFile`/`storePassword`/`keyAlias`/`keyPassword`を使う（`limitless`だけ既存の環境変数方式を継続）。これらの設定・鍵ファイルは`.gitignore`に追加し、Gitへ入れない。
4. GitHubリポジトリの**Settings → Secrets and variables → Actions**に、その**アプリ固有の**鍵のBase64、ストアのパスワードを初回のみ登録。キーのパスワードが別ならそれも登録。詳しくは[署名ブラウザ設定](SIGNING_BROWSER.md)。
5. 既存アプリの鍵・証明書・applicationIdを変更しない。証明書が既知のアプリは`expected-certificate`を設定し、正確なSHA-256を比較して更新互換性を守る。
6. `main`にPushして[Actions](https://github.com/takahiro-o8/android-tools/actions)ではなく**当該アプリ側のActions**で実行とAPK公開を確認する。GitHub Secretsは初回登録以降、更新のたびに再設定しない。

## ライフサイクル
正式リリース直後に、`scripts/retain-apk-versions.py --keep 3 --apply --remove-aux`で保存版数を管理する。コードのGit履歴と署名鍵は削除しない。署名鍵は本人管理の安全な場所にも必ずバックアップする。
