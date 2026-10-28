# E2E テスト(actions/e2e + e2e/adbtest.py)

GitHub Actions の Linux ランナー(KVM あり)で Android エミュレーターを起動し、adb で人と同じ操作(タップ・長押し・ドラッグ・回転)をして結果を確かめます。外部ライブラリは使いません(Python 標準ライブラリ + adb + `uiautomator dump`)。

## 実行のしかた(指示したときだけ動く)
- 人: GitHub → Actions → **E2E** → Run workflow
- AI: コミットメッセージに **`[e2e]`** を含めて `main` に push(AI のセッションは Actions を直接起動できないため)

## 結果の見かた
プレリリース **`e2e-report`** が毎回作り直されます。
- 本文 = `report.md`(手順ごとの ✅/❌、失敗の詳細、クラッシュ)
- 添付 = 手順ごとのスクリーンショット `NN.png`、`crash.txt`(logcat のクラッシュ)、`e2e-log.txt`(実行ログ)、ビルド失敗時は `build-log.txt`

AI は次で読む:
```
gh api repos/<owner>/<repo>/releases --jq '.[] | select(.tag_name=="e2e-report") | .body'
gh api repos/<owner>/<repo>/releases --jq '.[] | select(.tag_name=="e2e-report") | .assets[] | "\(.id) \(.name)"'
gh api -H "Accept: application/octet-stream" repos/<owner>/<repo>/releases/assets/<id> > 01.png
```
実行中はリリースがまだ古いので、本文の「コミット」が自分の push と一致するまで待つ(ビルド込みで 10〜20 分程度)。
テストが失敗するとワークフローも失敗になります。

## 既定の環境
- 端末: `pixel_6`、イメージ `system-images;android-36;google_apis;x86_64`(Android 16)。`system-image` 入力で変更可
  - Android 17(API 37)は 2026-10 時点のエミュレーター 37.2 と組み合わせると画面取得(screencap)と surfaceflinger が `hasReadColorBufferDma` のアサーションで落ち、どの描画方式でも動かないため既定から外した(オーナー判断)。新しいエミュレーターで直ったら戻す
- 描画方式は `swiftshader_indirect` → `swangle_indirect` → `guest` の順に、画面が撮れるまで試す(使った方式は `emulator-mode.txt`)
- 検証対象は **デバッグビルド**(`:app:assembleDebug`)。`run-as` でアプリの保存データを読めるため
- アニメーションは 0.5 倍、画面の自動回転は OFF(回転は `set_rotation()` で指定)

## テストの書き方(アプリの `e2e/test.py`)
```python
from adbtest import *

@step("起動してホームが出る")
def start():
    home()
    check(find(desc="ホーム画面"), "ホーム画面が見つからない")
    return "OK"                      # レポートの「内容」欄

@step("設定を変えると保存される")
def settings():
    ...
    check('value="7"' in run_as_cat("shared_prefs/settings.xml"), "保存されていない")

if __name__ == "__main__":
    main(setup=lambda: install(home_role=False))
```
- 手順は書いた順に実行。1 つ失敗しても次へ進む。各手順の後に自動でスクリーンショット
- 画面上の部品は `contentDescription`(`desc`)か文字(`text`)で探す。**テストで触る部品にはアプリ側で `contentDescription` を付ける**(アクセシビリティにもなる)
- 主な関数
  - 画面: `nodes()`, `find(desc=, text=, contains=, cls=)`, `find_all(...)`, `size()`, `wait_for(fn)`, `focused()`, `shot(name)`
  - 操作: `tap`, `long_press`, `drag(x1,y1,x2,y2, before_up=)`, `swipe`, `down/move/up`, `home`, `back`, `set_rotation(0〜3)`
  - データ: `run_as_cat(path)`, `run_as_json(path)`(アプリのデータディレクトリからの相対パス)
  - 準備: `install(home_role=, widget_bind=, permissions=())`
  - 判定: `check(cond, "失敗時の説明")`
- 環境変数: `E2E_PACKAGE`(対象のアプリ ID)、`E2E_OUT`(出力先)、`E2E_APK`

## 注意
- uiautomator はアニメーション中に失敗することがある(自動で再試行する)
- 端末の言語は英語。アプリの文字列が日本語だけなら日本語で表示される
- Google Play の入っていないイメージ(google_apis)。Google アプリ依存の機能は確認できない
