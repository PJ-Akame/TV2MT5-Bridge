# MQL5 / MetaTrader 5 連携（Python）

TradingView Webhook のシグナルを **MetaTrader 5 ターミナル** に成行注文で送る Python モジュールです。

- **ディレクトリ名 `MQL5`**: 本リポジトリでのまとめ名（MQL5 言語のソースは `extras/MQL5/` 配下）。
- **`config.json` のキー `mt5`**: ターミナル接続設定（従来どおり）。
- **`import MetaTrader5 as mt5`**: 公式 Python パッケージの変数名 `mt5` は変更しません。

## 前提条件

- Windows（MetaTrader 5 は Windows 専用）
- MetaTrader 5 ターミナルが起動していること

## インストール

```powershell
pip install -r MQL5/requirements.txt
```

## 設定

`config/config.json` の `mt5` セクションで有効化:

```json
"mt5": {
  "enabled": true,
  "volume": 0.01,
  "magic": 234000,
  "comment": "SMCSE",
  "terminal_path": "",
  "no_trade_windows": [
    { "start": "23:00", "end": "06:00" }
  ],
  "no_trade_timezone": "America/New_York"
}
```

`no_trade_windows` が空なら取引禁止チェックは行いません。

## 使い方

localServer の Webhook 受信時に、`mt5.enabled` が `true` の場合に自動で注文が実行されます。

直接呼び出す場合:

```python
from MQL5.mt5_order import send_order, execute_from_webhook

result = send_order(symbol="USDJPY", action="buy", volume=0.01)

result = execute_from_webhook({"symbol": "USDJPY", "action": "sell"})
```

## webhook_parse.py

TradingView の POST JSON を **`parse_webhook_for_mt5(payload, mt5_config)`** で正規化します。

- **`smcse.entry.v1`**: `result` → `buy` / `sell`、**`No trade` はスキップ**（注文なし）
- **レガシー**: `symbol` + `action`

`flatten_tradingview_payload` で `message` / `text` / `raw` 内の JSON をマージします。

## order.py

1. **ターミナル起動確認**
2. **取引アカウント確認**（`account_login` が 0 でなければ一致確認）
3. **オーダー実行**

```powershell
python MQL5/order.py USDJPY buy 0.01
python MQL5/order.py BTCUSD sell 0.01
```

```python
from MQL5.order import execute_order

result = execute_order(symbol="USDJPY", action="buy", volume=0.01)
```

## get_positions.py

```powershell
python MQL5/get_positions.py
python MQL5/get_positions.py USDJPY
python MQL5/get_positions.py --json
```

```python
from MQL5 import get_positions

n = get_positions()
n = get_positions("USDJPY")
```
