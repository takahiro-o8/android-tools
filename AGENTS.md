# AGENTS.md — 全アプリ共通の AI 向け作業ルール

オーナーの Android アプリはすべてこのルールで開発します。どの AI / 人でも、会話履歴なしで同じやり方を再現できることが目的です。
各アプリの `CLAUDE.md`(または `AGENTS.md`)は、このファイルを最初に読むよう指示し、アプリ固有の注意だけを書きます。
アプリ固有のルールとこのファイルが食い違うときは、アプリ側を優先します。

## 恒常ルール(オーナー指示)
1. **実装・実行の前に、必ず質問を重ねて仕様を詰める。** 選択肢を示して確認し、必要なら何度でも聞く。判断に迷う機能追加・設定追加も先に確認する
2. **APK で配布・更新できること。** GitHub Releases に APK を置く。同じ署名鍵で署名し、versionCode は単調増加(上書き更新できるように)。リリースに sha256 ファイルは付けない
3. **記録はすべて GitHub に置く。** 開発思想・仕様・判断・作業記録・残作業をリポジトリに書く。チャットだけに残った決定は存在しないものとして扱う
4. **設定変更で古い設定・データが残って反映されない不具合を出さない。** 詳細は [docs/PRINCIPLES.md](docs/PRINCIPLES.md)
5. **動作確認**
   - 自動: GitHub 上のエミュレーター(KVM あり、Android 16)で E2E テスト。手順は [docs/E2E.md](docs/E2E.md)
   - 手動: Mac が使えるときは Mac 上の Android Studio / エミュレーター
   - **仮想化なしの(極端に遅い)クラウドエミュレーターは使わない**
6. **修正したら確認せずにリリースしてよい。** 仕様を決める質問は実装前にするが、修正が終わって動作確認(E2E)が通ったら、改めて聞かずに版を上げてリリースする
7. **報告には常にリンクを付ける。** リリース・APK・E2E レポート・リポジトリ・コミットなど、話題にしたものの URL を添える
8. **個人名を入れない。** オーナーの名前・アカウント名をコード・アプリ・署名証明書・資料に入れない(リポジトリ所有者名の URL は除く)。表示名やアプリ ID も一般的な名前にする

## 各アプリのリポジトリの標準構成
```
CLAUDE.md / AGENTS.md     AI 向けルール(このファイルへの参照 + アプリ固有の注意)
README.md                 何のアプリか・入れ方
version.properties        VERSION_NAME / VERSION_CODE(CI が読む)
docs/SPEC.md              仕様と実装状態
docs/DECISIONS.md         判断の記録(ADR)。覆すときは新しい ADR を追記
docs/DEVLOG.md            作業記録(やったこと・理由・確認結果・未確認事項)
docs/TODO.md              残作業
docs/CHANGELOG.md         ## X.Y.Z ごとの変更点(リリースノートになる)
.github/workflows/build.yml   templates/workflows/build.yml をコピー
.github/workflows/e2e.yml     templates/workflows/e2e.yml をコピー
e2e/test.py               アプリ固有の E2E 手順(templates/e2e/test.py が雛形)
```
新しいアプリの始め方は [README.md](README.md)。

## 作業の始めと終わり
- **始め**: アプリの `docs/SPEC.md`・`docs/TODO.md`・`docs/DEVLOG.md` の最新数件・関係する `docs/DECISIONS.md` を読む。Releases の `dev`(最新ビルド)・`ci-logs`(失敗ログ)・`e2e-report`(最新 E2E 結果)を確認する
- **終わり**: `docs/DEVLOG.md` に追記。仕様・残作業・判断が変わったら各ファイルを更新。リリースするなら `VERSION_CODE` を増やし `docs/CHANGELOG.md` に `## X.Y.Z` を足して `main` に push(CI がタグと正式リリースを作る)

## AI セッション(クラウドのサンドボックス)での制約と回避
- Maven Central が 429 を返しローカルでビルドできないことが多い → ビルドは GitHub Actions に任せる
- タグの push、Releases の作成 API、Actions の API は 403 → 次の仕組みで回避している
  - リリース: `version.properties` を上げて push すると CI が作る([docs/BUILD.md](docs/BUILD.md))
  - ビルド結果: Releases の `dev` / `ci-logs` を読む
  - E2E: コミットメッセージに `[e2e]` を入れて push → Releases の `e2e-report` を読む
- Releases は読める: `gh api repos/<owner>/<repo>/releases`、添付は `gh api -H "Accept: application/octet-stream" repos/<owner>/<repo>/releases/assets/<id> > file`
- 署名鍵はリポジトリに入れない(GitHub Secrets)

## この共通リポジトリ(android-tools)を変えるとき
- 全アプリが `main` を直接使う。壊すと全アプリのビルドが止まるので、変えたら代表アプリ(launcher)で `[e2e]` 付きの push とビルドを通して確認する
- 互換性を壊す変更(入力名の変更など)は、使っている全アプリの呼び出しファイルを同時に直す
- 判断は [docs/DECISIONS.md](docs/DECISIONS.md)、作業記録は [docs/DEVLOG.md](docs/DEVLOG.md)
