# android-tools

オーナーの Android アプリで共通に使う仕組みとルール。各アプリは数行の呼び出しファイルとアプリ固有のテスト手順だけを持ち、ここの `main` を常に使います。

| 場所 | 内容 |
|---|---|
| [AGENTS.md](AGENTS.md) | 全アプリ共通の AI 向け作業ルール(**最初に読む**) |
| [actions/build](actions/build) | APK のビルドと GitHub Releases への公開(`dev` / `vX.Y.Z` / `ci-logs`)。説明: [docs/BUILD.md](docs/BUILD.md) |
| [actions/e2e](actions/e2e) | エミュレーターでの E2E テストと `e2e-report` への公開。説明: [docs/E2E.md](docs/E2E.md) |
| [e2e/adbtest.py](e2e/adbtest.py) | E2E テストを書くための adb 操作の部品(標準ライブラリのみ) |
| [templates](templates) | 各アプリにコピーするワークフローとテストの雛形 |
| [docs/PRINCIPLES.md](docs/PRINCIPLES.md) | 全アプリ共通の開発原則 |

## 新しいアプリに入れる
1. `templates/workflows/build.yml` と `e2e.yml` をアプリの `.github/workflows/` にコピーし、`APP_` の部分を設定
2. `templates/e2e/test.py` を `e2e/test.py` にコピーして手順を書く
3. `version.properties` と `docs/`(SPEC・DECISIONS・DEVLOG・TODO・CHANGELOG)を用意([AGENTS.md](AGENTS.md) の標準構成)
4. 署名鍵を作って Secrets に登録([docs/BUILD.md](docs/BUILD.md))
5. アプリの `CLAUDE.md` に「まず android-tools の AGENTS.md を読む」と書く

呼び出しファイルは `${{ github.repository_owner }}/android-tools` を取得して使うので、アカウント名を書く必要はありません(このリポジトリは公開のため、どのアプリからも取得できます)。

## 使っているアプリ
- launcher
