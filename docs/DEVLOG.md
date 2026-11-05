# 作業記録

## 2026-10-28 launcher で 14/14 成功(仕組みとして完成)
- launcher の E2E がすべて成功。共通の仕組みとしての既知の注意: 1 コマンドずつ送る長押し(`long_press`)は時々効かないことがある。手順の前に画面をまっさらに戻す(アプリ側で reset 相当を用意する)と安定する

## 2026-10-28 9〜10 回目: ドラッグの方式
- 1 コマンドずつの motionevent ではアプリ一覧からのドラッグが動かず、`input draganddrop` では動いた。ただし draganddrop は長押し判定の瞬間に動き出すため、下向きのドラッグでランチャーの「下スワイプ=通知」に取られた
- `drag()` の既定を「DOWN → 待機 → MOVE 群」を 1 回の端末シェルで送る方式に。draganddrop は `method="dnd"` で残す。`mid_shot` で離す直前の画面を保存できる

## 2026-10-28 8 回目: テストが動いた(4/12 成功)。レポート公開の失敗を修正
- 空の crash.txt があるとアップロードが 400 で失敗し、e2e-report が消えたままになっていた → 空ファイルは添付しない
- `find(cls=...)` が末尾一致で `GridView` も `View` として拾っていた → クラス名の完全一致(またはパッケージ付きの一致)に

## 2026-10-28 7 回目: 「KVM is not available」→ 修正
- それまでの実行では KVM が使えていたので、udev の権限反映待ちの競合とみて `udevadm settle` と `chmod 666 /dev/kvm` を追加。失敗時は /dev/kvm の状態と CPU の仮想化対応数をレポートに出す

## 2026-10-28 6 回目: どの描画方式でも同じ異常終了 → Android 16 に変更
- `-feature -ReadColorBufferDma` は「Bad feature name」で無効。guest / swangle / swiftshader とも同じアサーション
- オーナー判断で既定イメージを Android 16(API 36)に(ADR-0002)。描画方式は swiftshader_indirect から順に試す

## 2026-10-28 5 回目: swangle_indirect でも同じ異常終了 → 修正
- 原因はホスト側の機能 ReadColorBufferDma(GPU モードではない)。ゲスト(API 37)の mapper がこの機能を想定しておらず assert で落ちる
- 対処: `-feature -ReadColorBufferDma` で無効化して起動。画面が取れなければ `-gpu guest`、次に `swiftshader_indirect` で再起動して試す。使ったモードは `emulator-mode.txt` に残す

## 2026-10-28 4 回目: 画面の取得ができず全手順失敗 → 修正
- 原因: `-gpu swiftshader_indirect` で screencap と surfaceflinger が `hasReadColorBufferDma` のアサーションで異常終了(API 37 + emulator 37.2)。uiautomator dump も失敗
- 対処: 既定を `-gpu swangle_indirect` に(入力 `gpu` で変更可)。起動後に画面取得を確認し、だめならテストを始めずに理由を報告。uiautomator の失敗理由をレポートに出す

## 2026-10-28 3 回目: インストールが「Broken pipe」で失敗 → 修正
- 原因: 起動完了直後はパッケージサービスが未準備
- 対処: `pm path android` が返るまで待ち、インストールを最大 5 回再試行。準備で失敗してもレポートに「準備」の失敗として出す

## 2026-10-28 2 回目: エミュレーターが容量不足で終了 → 修正
- 原因: データ領域 6G 指定で「Not enough space to create userdata partition(空き 4.3GB、必要 7.3GB)」
- 対処: データ領域を 2G に、ランナーの不要なツール(dotnet・ghc・boost など)を削除して空きを確保、`-no-metrics`

## 2026-10-28 初回 E2E が 60 分で打ち切り → 修正
- 原因: avdmanager が AVD を `~/.android/avd` 以外に作り、エミュレーターが起動しないまま `adb wait-for-device` が無限に待った
- 対処: `ANDROID_AVD_HOME` を固定し作成を確認、起動直後に落ちたら即失敗。すべての adb 呼び出しと各段階に時間制限、テストは 25 分で打ち切り、手順ごとにレポートを書くので打ち切られても途中結果を公開する

## 2026-10-28 作成
- やったこと: launcher の build.yml を composite action `actions/build` に移し、E2E の仕組み(`actions/e2e`、`e2e/adbtest.py`)と全アプリ共通ルール(AGENTS.md、docs/)を作成。雛形を templates/ に
- 理由: ADR-0001
- 確認: launcher で `[e2e]` 付き push により初回実行(結果は launcher の DEVLOG に記録)
- 未確認: 他のアプリへの適用

## 2026-11-03 共通ウィジェット・書体仕様
- ユーザー指定をdocs/WIDGET_STYLE.mdとAGENTS.mdに記録。既存/新規アプリ共通、壁紙判定は廃止。
- 共通actionの実装や入出力は変更していない。文書のリンクと差分を確認。E2Eは新規に実行していない。

### 共通仕様の適用結果
- Traffic Monitor 1.3.1: https://github.com/takahiro-o8/traffic-monitor/releases/tag/v1.3.1
- AI Usage 0.6.10: https://github.com/takahiro-o8/ai-usage/releases/tag/signed-82086220cca779bd6b956426f37dc26388286bc8
- Launcher 2.4.1: https://github.com/takahiro-o8/launcher/releases/tag/v2.4.1
- File 1.0.1: ソース検証済み、既存署名鍵のSecrets復元待ち。詳細: https://github.com/takahiro-o8/android-file/blob/main/docs/CHANGES-1.0.1.md
- 既存の自動チェック・配布工程を利用。LauncherのE2Eはアプリ固有のオーナー指示に従い未実行。共通actionのコード変更なし。実機の外観は未確認。

## 2026-11-05 Androidの開発言語をKotlinに統一

ユーザー指示により、今後のCodexによる既存・新規Androidアプリ開発はKotlinを標準とし、テストとGradle Kotlin DSLも含めて共通AGENTS.mdへ記録。今回は文書のみの変更で、共有Actionsの入出力・ビルド処理は変更なし。
