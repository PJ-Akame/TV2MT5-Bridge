"""
MQL5 / MetaTrader 5 連携（Python）

TradingView Webhook のシグナルを MetaTrader 5 ターミナルに送信する。
ディレクトリ名は `MQL5`。公式の MetaTrader 5 Python パッケージは `import MetaTrader5`。
"""

from .get_positions import get_positions
from .mt5_order import OrderResult, execute_from_webhook, is_available, send_order
from .order import execute_order
from .webhook_parse import (
    WebhookOrderIntent,
    WebhookOrderSkip,
    flatten_tradingview_payload,
    parse_webhook_for_mt5,
)

__all__ = [
    "OrderResult",
    "WebhookOrderIntent",
    "WebhookOrderSkip",
    "execute_from_webhook",
    "execute_order",
    "flatten_tradingview_payload",
    "get_positions",
    "is_available",
    "parse_webhook_for_mt5",
    "send_order",
]
