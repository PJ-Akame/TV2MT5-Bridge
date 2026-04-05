"""
MetaTrader 5 注文実行モジュール（Python ブリッジ）
TradingView Webhook のシグナルを MetaTrader 5 ターミナルに送信する
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None  # type: ignore[assignment]

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.json"


def _load_mt5_config() -> dict[str, Any]:
    """config.json の mt5 セクションを読み込む"""
    try:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f).get("mt5", {})
    except (json.JSONDecodeError, OSError):
        pass
    return {}


@dataclass
class OrderResult:
    """注文実行結果"""
    success: bool
    message: str
    order_id: int | None = None
    deal_id: int | None = None
    retcode: int | None = None
    symbol: str | None = None
    type: str | None = None  # "buy" or "sell"
    volume: float | None = None
    price: float | None = None  # 約定価格
    time: datetime | None = None  # 約定時間


def is_available() -> bool:
    """MetaTrader5 パッケージが利用可能か"""
    return mt5 is not None


def _resolve_symbol(symbol: str) -> str | None:
    """Webhook のシンボル名をターミナルのシンボル名に解決する"""
    if not mt5:
        return None
    info = mt5.symbol_info(symbol)
    if info is not None:
        return symbol
    symbols = mt5.symbols_get()
    if symbols is None:
        return None
    symbol_upper = symbol.upper()
    for s in symbols:
        if s.name.upper().startswith(symbol_upper) or symbol_upper in s.name.upper():
            return s.name
    return None


def _get_filling_modes_to_try(symbol: str) -> list[int]:
    """
    シンボルがサポートする注文約定タイプのリストを返す（優先順）
    SYMBOL_FILLING: 1=FOK, 2=IOC, 4=RETURN
    ORDER_FILLING: 0=FOK, 1=IOC, 2=RETURN（MetaTrader5 Python の実際の値）
    """
    if not mt5:
        return [1, 2, 0]  # IOC, RETURN, FOK の順で試行
    info = mt5.symbol_info(symbol)
    if info is None:
        return [1, 2, 0]
    modes = []
    if info.filling_mode & 2:  # SYMBOL_FILLING_IOC
        modes.append(1)  # ORDER_FILLING_IOC
    if info.filling_mode & 4:  # SYMBOL_FILLING_RETURN
        modes.append(2)  # ORDER_FILLING_RETURN
    if info.filling_mode & 1:  # SYMBOL_FILLING_FOK
        modes.append(0)  # ORDER_FILLING_FOK
    return modes if modes else [1, 2, 0]


def send_order(
    symbol: str,
    action: str,
    volume: float = 0.01,
    magic: int = 234000,
    comment: str = "SMCSE",
    sl: float | None = None,
    tp: float | None = None,
    terminal_path: str | None = None,
) -> OrderResult:
    """
    MetaTrader 5 に成行注文を送信する

    Returns:
        OrderResult: 実行結果（成功時は symbol, type, volume, price を含む）
    """
    if mt5 is None:
        return OrderResult(
            success=False,
            message="MetaTrader5 パッケージがインストールされていません。pip install MetaTrader5 を実行してください。",
        )

    init_params: dict[str, Any] = {}
    if terminal_path:
        init_params["path"] = terminal_path

    if not mt5.initialize(**init_params):
        err = mt5.last_error()
        return OrderResult(
            success=False,
            message=f"MetaTrader 5 の初期化に失敗しました。ターミナルが起動しているか確認してください。error={err}",
        )

    try:
        resolved = _resolve_symbol(symbol)
        if resolved is None:
            return OrderResult(
                success=False,
                message=f"シンボル '{symbol}' が見つかりません。Market Watch で確認してください。",
            )
        symbol = resolved

        info = mt5.symbol_info(symbol)
        if info is None:
            return OrderResult(success=False, message=f"シンボル情報の取得に失敗: {symbol}")
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                return OrderResult(success=False, message=f"シンボル '{symbol}' を Market Watch に追加できませんでした")

        action_lower = str(action).lower().strip()
        if action_lower in ("buy", "long"):
            order_type = mt5.ORDER_TYPE_BUY
            tick = mt5.symbol_info_tick(symbol)
            price = tick.ask if tick else 0.0
            order_type_str = "buy"
        elif action_lower in ("sell", "short"):
            order_type = mt5.ORDER_TYPE_SELL
            tick = mt5.symbol_info_tick(symbol)
            price = tick.bid if tick else 0.0
            order_type_str = "sell"
        else:
            return OrderResult(
                success=False,
                message=f"不明なアクション: '{action}'。'buy' または 'sell' を指定してください。",
            )

        if price <= 0:
            return OrderResult(success=False, message=f"価格の取得に失敗: {symbol}")

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info:
            if volume < symbol_info.volume_min:
                volume = symbol_info.volume_min
            if volume > symbol_info.volume_max:
                volume = symbol_info.volume_max
            volume = round(volume / symbol_info.volume_step) * symbol_info.volume_step

        filling_modes = _get_filling_modes_to_try(symbol)
        result = None

        for filling in filling_modes:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": magic,
                "comment": comment[:31],
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }

            if sl is not None and sl > 0:
                request["sl"] = sl
            if tp is not None and tp > 0:
                request["tp"] = tp

            result = mt5.order_send(request)

            if result is not None and result.retcode != 10030:
                break

        if result is None:
            err = mt5.last_error()
            return OrderResult(
                success=False,
                message=f"order_send が None を返しました: {err}",
                retcode=getattr(err, "code", None),
            )

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=False,
                message=f"注文失敗: retcode={result.retcode}, {result.comment}",
                order_id=getattr(result, "order", None),
                deal_id=getattr(result, "deal", None),
                retcode=result.retcode,
            )

        exec_price = getattr(result, "price", price)
        deal_id = getattr(result, "deal", None)

        exec_time = datetime.now()

        return OrderResult(
            success=True,
            message=f"注文成功: {order_type_str} {symbol} {volume} lots @ {exec_price}",
            order_id=getattr(result, "order", None),
            deal_id=deal_id,
            retcode=result.retcode,
            symbol=symbol,
            type=order_type_str,
            volume=volume,
            price=exec_price,
            time=exec_time,
        )

    finally:
        mt5.shutdown()


def execute_from_webhook(payload: dict[str, Any], config: dict[str, Any] | None = None) -> OrderResult:
    """Webhook ペイロードから MetaTrader 5 注文を実行する（smcse.entry.v1 / レガシー対応）"""
    if config is None:
        config = _load_mt5_config()

    if not config.get("enabled", False):
        return OrderResult(
            success=False,
            message="MetaTrader 5 連携が無効です。config.json の mt5.enabled を true に設定してください。",
        )

    from .webhook_parse import WebhookOrderSkip, flatten_tradingview_payload, parse_webhook_for_mt5

    merged = flatten_tradingview_payload(payload)
    parsed = parse_webhook_for_mt5(payload, config)
    if isinstance(parsed, WebhookOrderSkip):
        return OrderResult(success=False, message=parsed.reason)

    magic = int(config.get("magic", 234000))
    comment = parsed.comment if parsed.comment is not None else str(config.get("comment", "SMCSE"))[:31]

    sl = merged.get("sl") or merged.get("stop_loss")
    tp = merged.get("tp") or merged.get("take_profit")
    if sl is not None:
        sl = float(sl)
    if tp is not None:
        tp = float(tp)

    terminal_path = config.get("terminal_path") or None

    return send_order(
        symbol=str(parsed.symbol),
        action=str(parsed.action),
        volume=parsed.volume,
        magic=magic,
        comment=comment[:31],
        sl=sl,
        tp=tp,
        terminal_path=terminal_path,
    )
