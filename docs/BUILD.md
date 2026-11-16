# Androidアプリの共通ビルド・署名・配布（現行）

## 運用
`main`にコードをPush → `assembleRelease`のみ実行 → **既存固定鍵で署名** → APK証明書・versionCode・versionNameを確認 → 正式GitHub Releaseを作成 → 最新版＋過去2件以外のReleaseと旧補助Releaseを削除する。

- 新しい版をリリースするのに、`VERSION_CODE`や`VERSION_NAME`を毎回手動で増やす必要はない。CIは`versionCode = 100000 + GITHUB_RUN_NUMBER`、`versionName = <基準の版名>.b<実行番号>`を設定する。
- ビルド失敗、署名鍵欠落、証明書不一致、APK版数不一致では公開中止。手動承認・PR・単体テスト・lintを通常の必須条件にしない。E2Eの手順・実行・補助コードは今後一切作らない。
- **古いビルドが新しいコードを上書きしない**よう判定。後続変更がMarkdownのみなら、その直前に作った同じソースのAPKを公開できる。
- `dev`・診断`ci-logs`/`e2e-report`・下書きReleaseは作らない。調査はGitHub Actionsのログを見る。

## 新規アプリの標準方式：Secretはパスワード1項目だけ

この方式は**最初から新しく配布するアプリ**向け。既存4アプリの署名鍵は維持し、勝手に再生成しない。`file`はユーザーが旧版のアンインストールを了承したため例外的にこの方式へ移行する。

1. **非公開GitHubリポジトリ**を使う。AIが`templates/workflows/build.yml`をコピーし、`APP_NAME`（APK名）、`APP_ALIAS`（英数字の鍵名）、`APP_APPLICATION_ID`（固定アプリID）、`APP_SIGNING_PASSWORD`（GitHub Secretの名前）を各アプリ固有の値に置き換える。`templates/version.properties`と`templates/gitignore.example`も参考にする。
2. **AIがSecret Name・ランダム48文字の英数字Value・登録URL・初回手順を記載したTXTを生成し、添付で渡す。** ユーザーはそのTXTからGitHub Settings → Secrets and variables → Actionsへ1項目だけ貼り付ける。値を覚えたり追加バックアップしたりする必要はない。Secretだけ変更すると鍵を開けなくなるため、意図しない変更をしない。鍵は初回のGitHub Actionsが生成し、パスワード暗号化された`signing/app-release.p12`として非公開Gitに保管する。
3. Actions → Build APK → Run workflow で`initialize_new_key`に**初回のみ**チェック。共通`scripts/bootstrap-signing.sh`が鍵ファイルと公開証明書のSHA-256指紋を作り、Gitにコミット。以降は**鍵を生成しない**。
4. 共通`actions/build`が同一鍵を使い、アプリID・バージョン・署名を検証して正式APKを公開する。以後mainへのコードPushだけで自動更新。鍵パスワードの再登録は不要。
5. 鍵とSecretを紛失した場合、ユーザーは旧アプリのアンインストールと再インストールを許容している。通常運用では鍵の追加バックアップを作らない。

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

**安全上の違い**：暗号化されたPKCS12をGitに保存するため、リポジトリを取得した攻撃者がオフラインでパスワードを総当たりする余地がある。非公開リポジトリ、十分強いランダムパスワード、アクセス制限が必須。パスワード保護されたファイルも安全性がゼロリスクになるわけではない。

### AIの初回セットアップ納品物
`scripts/generate-new-app-signing-txt.py`で、ユーザーがGitHub Secretsに貼る値を生成し、必ずコピー可能な`.txt`ファイルとして直接渡す。**リポジトリへのコミットは禁止**。作成時に鍵そのものをGitHub Secretsに登録させる必要はない。GitHub Actionsが鍵を自動生成するため、利用者の手作業はSecret1個の貼り付けで完了する。

## 既存4アプリの方式（変更しない）
Launcher・Limitless・G-widget・LinkAutoDLは各アプリの従来の署名鍵をそのまま利用し、当該リポジトリのGitHub Secretsで設定する。`file`だけは元の鍵を紛失し、アンインストールを明示的に了承したため、新しい署名鍵へ一度移行する。**既存鍵を統一・再生成しない。**

## ライフサイクル
正式リリース直後に、`scripts/retain-apk-versions.py --keep 3 --apply --remove-aux`で保存版数を管理する。コードのGit履歴と署名鍵は削除しない。署名鍵の追加バックアップは行わない。紛失時のみ再インストールを許容する。

## 共通Actionの更新と証明書の継続性

- 既存アプリの`.github/workflows/build.yml`は、共通`android-tools`を検証済みコミットSHAへ固定して取得する。共通リポジトリの`main`が進んでも既存アプリの挙動は勝手に変わらない。共通Actionを改修した場合は、対象アプリでSHAを明示的に更新し、実際の署名済みAPK公開結果を検証する。
- 公開ジョブは`cancel-in-progress: false`で直列実行する。共通Actionの`preflight`がAndroid SDKセットアップ前にmainの新しいコード変更を検出し、古いビルドを早期終了する。公開直前にも同じ確認を行う。
- `expected-certificate`または`expected-certificate-file`が未設定の既存アプリは、最新の正式ReleaseにあるAPKの実際の署名証明書SHA-256と、現在の固定鍵を比較してから本番ビルドを続行する。検証できない場合は公開しない。照合に成功したら、その証明書指紋をアプリ側ワークフローへ固定すると過去APKの再ダウンロードを省略できる。
- この安全確認はアプリの再署名・鍵の再生成を意味しない。正しい既存鍵が得られなければ配布を停止する。
- `File`は通常の正式APKビルド時の`lintVital`を省略する。アプリID・署名・versionCode・公開前チェックは省略しない。

## 重複ビルドの防止

- 新しいRunの開始前に、正式Releaseに記録された検証済みAPKのソースSHAと現在のSHAを照合し、同一ならAndroid SDKの準備とGradleビルドを省略する。
- SHAが違っても、差分がMarkdownと旧 `dist/`・`validation/` 配下だけならAPKを再発行しない。ワークフロー、ビルド設定、ソース、署名ファイルなどの差分は省略対象外。
- 比較対象となる正式ReleaseのアプリID・ソースSHAを検証できない場合は通常ビルドへ進む。GitHub APIの障害は失敗扱いとして公開停止する。
- 公開直前にも同じ検査を繰り返す。既存の証明書・アプリID・versionCodeの安全確認は維持する。
