# MT5 ツール

TradingView Webhook のシグナルを MetaTrader 5 に成行注文で送信するモジュール。

## 前提条件

- Windows（MetaTrader 5 は Windows 専用）
- MetaTrader 5 ターミナルが起動していること

## インストール

```powershell
pip install -r MT5/requirements.txt
```

## 設定

`config/config.json` の `mt5` セクションで有効化:

```json
"mt5": {
  "enabled": true,
  "volume": 0.01,
  "magic": 234000,
  "comment": "SMCSE",
  "terminal_path": ""
}
```

## 使い方

LocalServer の Webhook 受信時に、`mt5.enabled` が `true` の場合に自動で注文が実行されます。

直接呼び出す場合:

```python
from MT5.mt5_order import send_order, execute_from_webhook

# 直接注文
result = send_order(symbol="USDJPY", action="buy", volume=0.01)

# Webhook ペイロードから
result = execute_from_webhook({"symbol": "USDJPY", "action": "sell"})
```

## order.py

3ステップフローでオーダーを実行するスクリプト。

1. **MT5 起動確認** → 未起動なら「MT5 が未起動です」を返す
2. **取引アカウント確認** → `account_login` が 0 でなければ、想定アカウントと一致するか確認
3. **オーダー実行** → 結果（シンボル、buy/sell、ボリューム、約定価格）を返す

**コマンドライン:**
```powershell
python MT5/order.py USDJPY buy 0.01
python MT5/order.py BTCUSD sell 0.01
```

**スクリプトから呼び出し:**
```python
from MT5.order import execute_order

result = execute_order(symbol="USDJPY", action="buy", volume=0.01)
if result.success:
    print(f"{result.symbol} {result.type} {result.volume} @ {result.price}")
else:
    print(result.message)
```

## get_positions.py

ポジションの個数のみを返す。

**コマンドライン:**
```powershell
python MT5/get_positions.py        # 例: 1
python MT5/get_positions.py USDJPY
python MT5/get_positions.py --json  # 詳細を JSON で出力
```

**スクリプトから呼び出し:**
```python
from MT5 import get_positions

n = get_positions()           # 例: 1（int）
n = get_positions("USDJPY")   # 指定シンボルの個数
```
