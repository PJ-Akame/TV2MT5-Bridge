"""
TradingView Webhook ペイロードを MT5 注文パラメータに正規化する。
smcse.entry.v1 とレガシー {symbol, action} の両方に対応。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


def flatten_tradingview_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    TradingView / 中継のラップを剥がし、Pine の smcse.entry.v1 等をトップレベルに寄せる。
    """
    merged = dict(payload)
    for key in ("message", "text"):
        val = merged.get(key)
        if isinstance(val, dict):
            merged = {**merged, **val}
        elif isinstance(val, str):
            s = val.strip()
            if s.startswith("{"):
                try:
                    inner = json.loads(s)
                    if isinstance(inner, dict):
                        merged = {**merged, **inner}
                except json.JSONDecodeError:
                    pass
    raw = merged.get("raw")
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("{"):
            try:
                inner = json.loads(s)
                if isinstance(inner, dict):
                    merged = {**merged, **inner}
            except json.JSONDecodeError:
                pass
    for nest_key in ("payload", "body", "data"):
        v = merged.get(nest_key)
        if isinstance(v, dict):
            merged = {**merged, **v}
    return merged


def strip_exchange_prefix(symbol: str) -> str:
    if ":" in symbol:
        return symbol.split(":")[-1]
    return symbol


@dataclass(frozen=True)
class WebhookOrderIntent:
    """MT5 成行エントリー試行用の解決結果"""

    symbol: str
    action: str
    volume: float
    comment: str | None = None


@dataclass(frozen=True)
class WebhookOrderSkip:
    """注文しない（No trade・不正ペイロードなど）"""

    reason: str


def _safe_float_volume(x: Any, default: float) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _entry_v1_comment(config_comment: str, result: str, position_pct: Any) -> str:
    base = (config_comment or "SMCSE")[:14]
    r = (result or "?")[:8]
    parts: list[str] = [base, r]
    if isinstance(position_pct, float) and math.isnan(position_pct):
        pass
    elif isinstance(position_pct, (int, float)):
        parts.append(str(int(round(float(position_pct)))))
    return " ".join(parts)[:31]


def _use_entry_v1_rules(merged: dict[str, Any]) -> bool:
    """schema 明示または smcse.entry.v1 形状なら v1 解釈（result + symbol + 補助フィールド）。"""
    if str(merged.get("schema") or "").strip() == "smcse.entry.v1":
        return True
    if merged.get("schema"):
        return False
    if merged.get("result") is None:
        return False
    if not (merged.get("symbol") or merged.get("ticker")):
        return False
    return any(
        k in merged
        for k in (
            "lastPrice",
            "upperObCount",
            "lowerObCount",
            "positionPct",
            "upperObRef",
            "lowerObRef",
        )
    )


def parse_webhook_for_mt5(
    payload: dict[str, Any],
    mt5_config: dict[str, Any],
) -> WebhookOrderIntent | WebhookOrderSkip:
    """
    Webhook 1 件分の dict から注文意図を得る。

    Args:
        payload: 生の POST JSON（または flat 済み）
        mt5_config: config.json の mt5 セクション
    """
    merged = flatten_tradingview_payload(payload)
    default_vol = _safe_float_volume(mt5_config.get("volume"), 0.01)
    default_symbol = mt5_config.get("symbol")
    cfg_comment = str(mt5_config.get("comment", "SMCSE"))

    if _use_entry_v1_rules(merged):
        raw_result = merged.get("result")
        rl = str(raw_result).strip().lower() if raw_result is not None else ""
        if rl in ("no trade", "no_trade", "flat", "hold"):
            return WebhookOrderSkip(reason="smcse.entry.v1: No trade（注文なし）")
        if rl in ("buy", "long"):
            action = "buy"
        elif rl in ("sell", "short"):
            action = "sell"
        else:
            return WebhookOrderSkip(reason=f"smcse.entry.v1: 未対応の result={raw_result!r}")
        symbol = (
            merged.get("symbol")
            or merged.get("symbol_name")
            or merged.get("ticker")
            or default_symbol
        )
        if not symbol:
            return WebhookOrderSkip(reason="symbol がペイロードにも config にもありません")
        symbol = strip_exchange_prefix(str(symbol))
        volume = _safe_float_volume(
            merged.get("volume") if merged.get("volume") is not None else merged.get("quantity"),
            default_vol,
        )
        cmt = _entry_v1_comment(cfg_comment, str(raw_result).strip(), merged.get("positionPct"))
        return WebhookOrderIntent(symbol=symbol, action=action, volume=volume, comment=cmt)

    symbol = (
        merged.get("symbol")
        or merged.get("symbol_name")
        or merged.get("ticker")
        or default_symbol
    )
    if not symbol:
        return WebhookOrderSkip(reason="symbol がペイロードにも config にもありません")
    symbol = strip_exchange_prefix(str(symbol))
    raw_action = (
        merged.get("action")
        or merged.get("trade")
        or merged.get("order")
        or merged.get("side")
        or "buy"
    )
    action = str(raw_action).lower().strip()
    volume = _safe_float_volume(
        merged.get("volume") if merged.get("volume") is not None else merged.get("quantity"),
        default_vol,
    )
    return WebhookOrderIntent(symbol=symbol, action=action, volume=volume, comment=None)
