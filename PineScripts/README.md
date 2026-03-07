# Pine Scripts

## one_minute_alert.pine

1分ごとにアラートを発火するスクリプト。

### 使い方

1. TradingView でチャートを開く
2. 下部の「Pine エディター」を開く
3. `one_minute_alert.pine` の内容をコピー＆ペースト
4. 「チャートに追加」をクリック
5. アラートを作成:
   - チャート上で右クリック → 「アラートを追加」
   - 条件: 「1分毎アラート」
   - 通知: 「Webhook URL」を選択
   - URL: `https://your-subdomain.example.com`（config の tunnel.hostname に対応する URL）
   - メッセージ: スクリプトのデフォルト（またはカスタム JSON）

### メッセージ形式（Webhook でオーダー実行に必要）

```json
{"time":"{{timenow}}","interval":"1m","symbol":"{{ticker}}","action":"buy"}
```

- `symbol`: 通貨ペア（{{ticker}} で自動設定）
- `action`: `buy` または `sell`（オーダー実行に必須）

### 注意

- 1分足チャートで使用することを推奨
- アラートは新しい分が始まるたびに発火
