# 5アプリの署名鍵：パスワードを覚えずに復旧できるバックアップ

## 原則
- **Launcher・G-widget・Limitless・LinkAutoDL・Fileの現在の署名鍵を変更しない。** Androidの上書き更新・設定保持を優先。
- 1台のPCで`age-keygen`から**復旧用の公開鍵・秘密鍵ペア**を作り、秘密鍵ファイルをPCと別の安全な媒体に保管。覚えるべき新しいパスワードはない。
- その**公開鍵だけ**を各アプリのGitHub Actionsの手動バックアップ画面へ貼る。各アプリの既存署名鍵＋必要なGitHub Secretsの値が、GitHubの実行環境内で復旧用公開鍵へ暗号化される。
- ダウンロードした**暗号化済み`android-signing-backup.age`**をGoogle Driveや外部ストレージに保管する。1アプリ1ファイル。暗号化前の鍵やパスワードをGit・Release・GitHub Artifactsに残さない。
- **パスワードの個別バックアップは不要になるが、PCの復旧用秘密鍵ファイルのバックアップは必須。** そのファイルも紛失したら、暗号化バックアップを復号できない。

## PCで初回のみ（Windows / macOS / Linux）
1. `age`（公式 <https://github.com/FiloSottile/age/releases>）のPC用実行ファイルを入手し、コマンドを実行できるようにする。Windowsでは`age-keygen.exe`、macOS/Linuxでは`age-keygen`。
2. PC上で`age-keygen -o android-recovery-key.txt`を実行。作成した**秘密鍵ファイル`android-recovery-key.txt`を絶対にGitHubやチャットに貼らない**。
3. `age-keygen -y android-recovery-key.txt`で表示される`age1...`から始まる**公開鍵**をコピー。これが5アプリ共通の宛先。
4. `android-recovery-key.txt`をPCと別のオフライン媒体等、**最低2か所**にバックアップする。ファイルを他人が入手するとすべてのアプリの署名鍵を復号可能なので、OSのディスク暗号化・アクセス制限を利用する。

## アプリごとに1回だけ
1. 各アプリのGitHub → **Actions → Backup signing key (manual only)** → **Run workflow**。
2. `recovery_public_key`欄へPCの`age1...`公開鍵を貼って実行。通常のAPKビルドやE2Eは実行しない（このバックアップだけの低負荷ジョブ）。
3. 成功した実行画面のArtifactsから`signing-backup-<アプリ名>`をダウンロードし、ZIP内の`android-signing-backup.age`をPC・クラウドドライブ等へ保管。Artifactsの保存期限は**1日**。期限切れ前に必ずダウンロードする。
4. 5アプリ分が揃っていることを確認する。公開鍵だけでは復号不可。秘密鍵ファイル`android-recovery-key.txt`が必要。

## 復旧時（今は実行しない）
- PCで`age -d -i android-recovery-key.txt -o recovered.tar android-signing-backup.age`。
- `recovered.tar`に`keystore.bin`と`manifest.json`が入っており、元の署名鍵、アプリ名、必要なSecret名と値が復旧可能。
- **復号した`recovered.tar`には平文の署名情報が含まれる。** 一時ファイルは安全な端末内で取り扱い、秘密情報をGitHub・チャット・共有リンクに貼らず、復旧後削除する。
- 各アプリで必要になった場合のみ`gh secret set`で元のSecretを再登録する。Fileは暗号化P12を維持し、`FILE_SIGNING_PASSWORD`を復旧すれば同じ鍵で署名できる。

## 計算リソース
- **バックアップは手動実行のみ**。定期実行しない。E2E・エミュレーター・APKビルド・Android SDKのセットアップは行わない。
- 既存5アプリの通常のActionsは、アプリソースとGradle・署名設定の変更でのみ起動する。
- バックアップは各アプリの既存鍵を一時的に参照するが、鍵自体を変更・再発行しない。

## リカバリー時の復号とSecretの復元を自動化（PCのみ）
GitHub CLI（`gh auth login`済み）、Python 3、`age`が使えるPCなら、暗号化バックアップをダウンロード済みの状態で、次のコマンドで復旧対象を安全に確認できる：

```sh
python3 scripts/restore-signing-backup.py android-signing-backup.age --identity android-recovery-key.txt
```

実際にGitHub Secretsを上書き復元するときだけ`--apply`を追加する。**通常運用では実行しない。**

```sh
python3 scripts/restore-signing-backup.py android-signing-backup.age --identity android-recovery-key.txt --apply
```

ローカルに元の鍵ファイルが必要になった場合は`--export-keystore ./private/keystore.bin`を追加。秘密鍵はそのPCだけに書き出され、`git add`したり共有しないこと。`file`の固定鍵は`signing/file-release.p12`を維持すること。署名証明書・アプリIDを変更しない。
