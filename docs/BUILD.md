# ビルドと配布(actions/build)

## 流れ
| きっかけ | 結果 |
|---|---|
| `main` に push | プレリリース **`dev`** を最新 APK(`<名前>-<版>-dev-<コミット>.apk`)で置き換え |
| `version.properties` の版にまだリリースが無い状態で `main` に push | タグ **`vX.Y.Z`** と正式リリース(`<名前>-<版>.apk`)を自動作成。ノートは `docs/CHANGELOG.md` の `## X.Y.Z` 節。本番鍵で署名できたときだけ |
| ビルド失敗 | プレリリース **`ci-logs`** にログ `build-log-<run id>.txt` |
| pull request | ビルドだけ(公開しない) |

sha256 ファイルは付けません。

## アプリ側に必要なもの
- `version.properties`
  ```
  VERSION_NAME=1.0.0
  VERSION_CODE=1
  ```
- `app/build.gradle.kts` で `version.properties` を読み、ルートに `keystore.properties`(CI が書く: `storeFile` / `storePassword` / `keyAlias` / `keyPassword`)があればリリース署名に使う。無ければデバッグ鍵
- `.github/workflows/build.yml`(`templates/workflows/build.yml` をコピーして名前・鍵のエイリアス・Secrets 名を設定)

## 署名鍵(アプリごとに 1 回・オーナー作業)
1. `keytool -genkeypair -v -keystore <app>-release.jks -alias <alias> -keyalg RSA -keysize 4096 -validity 36500 -dname "CN=<アプリ名>"`(個人名を入れない)
2. リポジトリ → Settings → Secrets and variables → Actions に登録
   - `<APP>_KEYSTORE_BASE64`: `base64 -w0 <app>-release.jks` の結果
   - `<APP>_KEYSTORE_PASSWORD`: パスワード(ストア・キー共通)
3. 鍵とパスワードはパスワードマネージャー等にも保管。失くすと既存インストールを更新できない

## リリース手順
1. `VERSION_CODE` を +1、`VERSION_NAME` を更新
2. `docs/CHANGELOG.md` に `## X.Y.Z` を追加
3. `main` に push(タグは CI が作る)
