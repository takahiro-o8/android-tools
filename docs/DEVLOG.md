# 作業記録

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
