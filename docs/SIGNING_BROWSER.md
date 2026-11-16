# GitHubのブラウザ画面で署名鍵を初期設定する方法

## 新規アプリ、または旧版の再インストールを明示的に許可したアプリ（簡単な1-Secret方式）

1. 対象の**非公開**GitHubリポジトリを開き、**Settings → Secrets and variables → Actions**へ移動。
2. 「New repository secret」を選ぶ。Secret名はそのアプリのworkflowに指定したもの（例：`file`は`FILE_SIGNING_PASSWORD`）。
3. **AIが新規生成して渡したTXT**のNameとValueを、そのままGitHub Secretへコピーする。**ユーザー自身がパスワードを考えたり鍵を作成したりする必要はない。** TXTはASCII英数字48文字のランダム値を含む。値はGitHub Secretsが保持するため通常ビルドで再入力不要。紛失時は再インストールを許容する。
4. 対象リポジトリの **Actions → Build APK → Run workflow** で`initialize_new_key`を**初回だけ**選択し、mainで実行。
5. ビルドが成功し、正式ReleaseにAPKがあることを確認したらインストールする。既存アプリの旧鍵と異なる場合、必要なアプリ内データ・設定の退避を検討してから旧版をアンインストールする。
6. 以降は同じ鍵で自動更新し、Secretsの再登録は不要。新しい鍵を生成する操作は行わない。

この方式では**暗号化された署名鍵ファイルそのものを非公開Git履歴に保存**するため、32文字以上のランダムパスワードと非公開のアクセス制御が重要。GitHub以外の鍵バックアップはユーザー方針により省略する。鍵とSecretを失った場合は旧アプリの上書き更新ができない。

## 既存の鍵を引き続き使うアプリ

Launcher・Limitless・G-widget・LinkAutoDLは**この初回生成操作を使用しない**。既存の署名鍵をGitHub Secretsから読み込み、署名証明書の一致を確認する。

1. 各アプリの`.github/workflows/build.yml`や`docs/SIGNING.md`で実際のSecret名を確認。
2. GitHubのSettings → Secrets and variables → Actionsで必要な名前が登録済みか確認。Secretsの値は閲覧できない。値を失った場合は、ユーザー了承のもと新しい鍵とAPKへ切り替え、再インストールする。
3. 新規の鍵を作ると端末上の既存アプリに上書きできなくなるため、鍵の再発行や別アプリの鍵の流用をしない。

[共通ビルド手順](BUILD.md)・[安全な配布](RELEASE_SAFETY.md)。


**AI開発者向け**：新規アプリのSecrets値は必ずAIが生成してユーザーへコピー可能なTXTを納品する。[作成スクリプト](../scripts/generate-new-app-signing-txt.py)。TXTの秘密情報をGitにコミットしたりログへ出力しない。
