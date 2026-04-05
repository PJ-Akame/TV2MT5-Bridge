# Pine Scripts

## SMCExecutionSignal.pine

メインのインジケーター（表示名は Pine 内で **Mxwll Suite**）。SMC 系表示に加え、**`smcse.entry.v1` 形式の JSON を `alert()` で送信**し、Webhook → `MQL5` → MT5 連携と整合します。

- エントリー用アラート: インジ設定の **Entry alert** をオンにし、TradingView 側で **このスクリプトの `alert()` 呼び出し**に紐づけたアラートを作成する
- 送信される JSON のキーはリポジトリ直下 `README.md` の **Webhook POST リファレンス（smcse.entry.v1）** を参照

## レガシー形式（参考）

MT5 ブリッジは **`{"symbol","action"}`** のレガシー JSON も受け付けます。分足で一定間隔テストだけしたい場合は、同等の JSON をアラートのメッセージ欄に手入力するか、別途スクリプトを作成してください（本フォルダには `one_minute_alert.pine` は同梱していません）。
