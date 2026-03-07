"""
MT5 の現在のポジションを取得するスクリプト
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None  # type: ignore[assignment]

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.json"


def _get_terminal_path() -> str | None:
    """config.json から MT5 ターミナルパスを取得"""
    try:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                return (json.load(f).get("mt5", {}).get("terminal_path") or "").strip() or None
    except (json.JSONDecodeError, OSError):
        pass
    return None


def get_positions(symbol: str | None = None) -> int:
    """
    ポジションの個数を返す

    Args:
        symbol: シンボルで絞り込み（省略時は全シンボル）

    Returns:
        ポジションの個数（0 以上）
    """
    if mt5 is None:
        return 0

    init_params: dict[str, Any] = {}
    if path := _get_terminal_path():
        init_params["path"] = path

    if not mt5.initialize(**init_params):
        return 0

    try:
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
            return len(positions) if positions else 0
        return mt5.positions_total()
    finally:
        mt5.shutdown()


def _get_positions_detail(symbol: str | None = None) -> list[dict[str, Any]]:
    """ポジション詳細を取得（--json 用の内部関数）"""
    if mt5 is None:
        return []

    init_params: dict[str, Any] = {}
    if path := _get_terminal_path():
        init_params["path"] = path

    if not mt5.initialize(**init_params):
        return []

    try:
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()

        if positions is None:
            return []

        result = []
        for p in positions:
            result.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "buy" if p.type == 0 else "sell",
                "volume": p.volume,
                "price_open": p.price_open,
                "price_current": p.price_current,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "swap": p.swap,
                "magic": p.magic,
                "comment": p.comment,
            })
        return result

    finally:
        mt5.shutdown()


def main() -> int:
    """コマンドラインから実行（ポジション数のみ出力）"""
    if mt5 is None:
        print("MetaTrader5 パッケージがインストールされていません。pip install -r MT5/requirements.txt", file=sys.stderr)
        return 1

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    symbol = args[0] if args else None

    if "--json" in sys.argv:
        positions = _get_positions_detail(symbol=symbol)
        print(json.dumps(positions, indent=2, ensure_ascii=False))
    else:
        print(get_positions(symbol=symbol))

    return 0


if __name__ == "__main__":
    sys.exit(main())
