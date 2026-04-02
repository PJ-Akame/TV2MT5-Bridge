"""
MQL5 / MetaTrader 5 連携（Python）

TradingView Webhook のシグナルを MetaTrader 5 ターミナルに送信する。
ディレクトリ名は `MQL5`。公式の MetaTrader 5 Python パッケージは `import MetaTrader5`。
"""

from .get_positions import get_positions
from .mt5_order import OrderResult, execute_from_webhook, is_available, send_order
from .order import execute_order

__all__ = [
    "OrderResult",
    "execute_from_webhook",
    "execute_order",
    "get_positions",
    "is_available",
    "send_order",
]
