# LINE Messaging API 共通連携情報

更新日: 2026-11-16

## 登録済みアカウント（開発用の共通設定）
- LINE公式アカウント名: **AI通知Bot**
- チャネル説明: AI通知Bot
- Messaging API Channel ID: `2012638315`
- Messaging API: **有効化済み**
- オーナーの個人LINEからBotを友だち追加: **完了**
- LINE Developers: https://developers.line.biz/console/
- LINE Official Account Manager: https://manager.line.biz/

この情報は、将来の複数AndroidアプリやAIツールが共通でLINE連携する際の参照元。LINE公式アカウントを作り直す必要はない。

## 現時点の範囲と未実装
- **LINE側の初期設定だけ完了**。送信テスト、受信テスト、サーバー実装、Android実装は未実施。
- Channel Access Token: 発行・有効性は未確認。必要になった際に取得し、安全な保管先に登録する。
- Webhook URL: **未設定**。Webhook受信先は今後のアプリ設計時に決める。
- **Google Apps Script (GAS) は利用しない。Cloudflareの導入も現時点では行わない。**
- 将来の目標: (1) 自作アプリやAIの処理結果を個人LINEへ通知する、(2) 個人LINEからBotに送ったテキスト等を自作Androidアプリが取得・処理する。

## アプリ側での利用方式（今後の設計方針）
- **送信**: アプリ/AI → 安全な中継処理 → LINE Messaging APIのPushメッセージ → 指定ユーザーの個人LINE。
- **受信**: 個人LINE → AI通知Bot → LINE Webhook → 公開HTTPS受信先 → 自作Androidアプリ（通知/同期/取得など）。
- LINEのWebhookは公開HTTPSエンドポイントへのサーバー間通知であり、Androidアプリの内部へ直接自動配信されるものではない。
- Android APKや公開GitHubファイルにChannel Secret/Channel Access Tokenを埋め込まず、受信側でWebhook署名を検証する。
- 中継処理のホスティング先は**未決定**。GASやCloudflareを使用する決定ではない。
- ChatGPT定期タスクなど、任意のHTTPリクエストを送れない実行環境では、Googleスプレッドシート上の通知キュー等の中継方式を必要に応じて検討する。実装済みと誤認しないこと。

## 公開しない情報と設定キー
共通基盤のGitHubリポジトリは**public**。以下の値はGitファイル・Issue・ログ・チャットに平文保存しない。

| 設定名（例） | 用途 | 公開Gitでの保存 |
|---|---|---|
| `LINE_CHANNEL_ID` | 公開用チャネル識別子。現在の値は `2012638315` | 可 |
| `LINE_CHANNEL_SECRET` | Webhook署名検証 | **不可** |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API呼び出し | **不可** |
| `LINE_RECIPIENT_USER_ID` | 個人LINEの送信先User ID（`U`で始まる値） | **不可（個人識別子）** |

オーナーのLINE User IDは設定・確認済みだが、この公開文書には転記していない。将来実装時に安全なシークレット管理先で設定する。登録メールアドレスも個人情報のため記載しない。

## 開発時の確認事項
1. LINE側の既存チャネル（ID `2012638315`）を再利用する。
2. Access Tokenと受信者User IDは、必要な実行環境の安全な設定から読み込む。
3. 新しくHTTPS受信先を設ける場合はWebhook URL登録、Webhook利用ON、署名検証、送信元認可を実装する。
4. LINEの無料プランのメッセージ数制限・API仕様は実装時点で公式資料を再確認する。
5. **現時点では外部サービスを追加契約せず、既存アプリやCIを変更しない。**
