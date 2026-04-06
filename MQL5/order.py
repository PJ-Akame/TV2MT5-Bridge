"""
MetaTrader 5 オーダー実行スクリプト（Python ブリッジ）
1. ターミナル起動確認
2. 取引アカウント確認
3. ポジション上限チェック（上限未満の時のみ実行）
4. 取引禁止時間帯チェック（config.no_trade_windows）
5. オーダー実行
"""

from __future__ import annotations

import json
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SHUTDOWN_TIMEOUT = 2.0  # 秒


def _safe_shutdown() -> None:
    """mt5.shutdown() をタイムアウト付きで実行（ブロック対策）"""
    if mt5 is None:
        return
    done = threading.Event()

    def _do_shutdown() -> None:
        try:
            mt5.shutdown()
        finally:
            done.set()

    t = threading.Thread(target=_do_shutdown, daemon=True)
    t.start()
    done.wait(timeout=_SHUTDOWN_TIMEOUT)

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None  # type: ignore[assignment]

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.json"


def _load_config() -> dict[str, Any]:
    """config.json から MetaTrader 5 連携設定（mt5 セクション）を読み込む"""
    try:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f).get("mt5", {})
    except (json.JSONDecodeError, OSError):
        pass
    return {}


@dataclass
class OrderResult:
    """オーダー実行結果"""
    success: bool
    message: str
    symbol: str | None = None
    type: str | None = None  # "buy" or "sell"
    volume: float | None = None
    price: float | None = None  # 約定価格
    time: Any = None  # 約定時間 (datetime)
    order_id: int | None = None


def _check_mt5_running(terminal_path: str | None = None) -> tuple[bool, str]:
    """
    MetaTrader 5 ターミナル起動確認

    Returns:
        (成功, メッセージ) 失敗時はメッセージに「未起動」等を返す
    """
    if mt5 is None:
        return False, "MetaTrader5 パッケージがインストールされていません"

    init_params: dict[str, Any] = {}
    if terminal_path:
        init_params["path"] = terminal_path

    if not mt5.initialize(**init_params):
        return False, "MetaTrader 5 が未起動です。ターミナルを起動してください"

    return True, ""


def _check_account(expected_login: int) -> tuple[bool, str]:
    """
    取引アカウント確認

    Args:
        expected_login: 想定するアカウント番号（0 の場合はチェック省略）

    Returns:
        (成功, メッセージ)
    """
    if expected_login == 0:
        return True, ""

    info = mt5.account_info()
    if info is None:
        return False, "アカウント情報の取得に失敗しました"

    if info.login != expected_login:
        return False, f"想定していないアカウントです。現在: {info.login}、想定: {expected_login}"

    return True, ""


def _parse_hhmm_to_minutes(s: Any) -> int | None:
    """'HH:MM' をその日の 0 時からの分に変換。不正なら None。"""
    if s is None:
        return None
    parts = str(s).strip().split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if h == 24 and m == 0:
        return 24 * 60
    if not (0 <= h < 24 and 0 <= m < 60):
        return None
    return h * 60 + m


def _now_for_no_trade_check(config: dict[str, Any]) -> datetime:
    """no_trade_timezone があればそのタイムゾーンの現在時刻、無ければシステムローカル。"""
    tz_name = (config.get("no_trade_timezone") or "").strip()
    if not tz_name:
        return datetime.now()
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        if tz_name.upper() == "UTC":
            return datetime.now(timezone.utc)
        return datetime.now()


def _minute_is_in_window(now_min: int, start_min: int, end_min: int) -> bool:
    """開始・終了（分・当日基準）。終了が開始より前なら日跨ぎ。境界は両端含む。"""
    if start_min == end_min:
        return False
    if start_min < end_min:
        return start_min <= now_min <= end_min
    return now_min >= start_min or now_min <= end_min


def _is_no_trade_time_now(config: dict[str, Any]) -> tuple[bool, str]:
    """
    取引禁止時間帯なら (True, 理由)。エントリー可なら (False, "")。
    no_trade_windows が空または未設定のときは常にエントリー可。
    """
    raw = config.get("no_trade_windows")
    if not raw:
        return False, ""
    if not isinstance(raw, list):
        return False, ""

    now = _now_for_no_trade_check(config)
    now_min = now.hour * 60 + now.minute

    for idx, w in enumerate(raw):
        if not isinstance(w, dict):
            continue
        start_min = _parse_hhmm_to_minutes(w.get("start"))
        end_min = _parse_hhmm_to_minutes(w.get("end"))
        if start_min is None or end_min is None:
            continue
        if _minute_is_in_window(now_min, start_min, end_min):
            start_s, end_s = w.get("start"), w.get("end")
            return True, (
                f"取引禁止時間帯です（ウィンドウ {idx + 1}: {start_s}–{end_s}、"
                f"判定時刻 {now.strftime('%Y-%m-%d %H:%M')}）"
            )
    return False, ""


def execute_order(
    symbol: str,
    action: str,
    volume: float = 0.01,
    config: dict[str, Any] | None = None,
    comment: str | None = None,
) -> OrderResult:
    """
    オーダーを実行する

    1. ターミナル起動確認
    2. 取引アカウント確認
    3. ポジション上限チェック（position_limit 未満の時のみ実行）
    4. 取引禁止時間帯チェック（no_trade_windows）
    5. オーダー実行

    Args:
        symbol: 通貨ペア
        action: "buy" または "sell"
        volume: ロット数
        config: config の mt5 セクション相当（省略時は config.json から読み込み）
        comment: 注文コメント（省略時は config の comment。MT5 は 31 文字まで）

    Returns:
        OrderResult: 実行結果（成功時は symbol, type, volume, price を含む）
    """
    if config is None:
        config = _load_config()

    try:
        from MQL5.symbol_mapping import load_symbol_mapping, resolve_symbol_for_mt5
    except ImportError:
        from symbol_mapping import load_symbol_mapping, resolve_symbol_for_mt5

    symbol = resolve_symbol_for_mt5(symbol, load_symbol_mapping())

    terminal_path = (config.get("terminal_path") or "").strip() or None
    expected_login = int(config.get("account_login", 0))

    ok, msg = _check_mt5_running(terminal_path)
    if not ok:
        return OrderResult(success=False, message=msg)

    try:
        ok, msg = _check_account(expected_login)
        if not ok:
            return OrderResult(success=False, message=msg)
    finally:
        _safe_shutdown()

    position_limit = int(config.get("position_limit", 1))
    if position_limit > 0:
        try:
            from MQL5.get_positions import get_positions
        except ImportError:
            from get_positions import get_positions
        current_count = get_positions(symbol=symbol)
        if current_count >= position_limit:
            return OrderResult(
                success=False,
                message=f"ポジション上限に達しています。{symbol}: 現在 {current_count} 件、上限 {position_limit} 件",
            )

    no_trade, no_trade_msg = _is_no_trade_time_now(config)
    if no_trade:
        return OrderResult(success=False, message=no_trade_msg)

    try:
        from MQL5.mt5_order import send_order
    except ImportError:
        from mt5_order import send_order

    comment_used = (comment if comment is not None else str(config.get("comment", "SMCSE")))[:31]
    result = send_order(
        symbol=symbol,
        action=action,
        volume=volume,
        magic=int(config.get("magic", 234000)),
        comment=comment_used,
        terminal_path=terminal_path,
    )

    if not result.success:
        return OrderResult(success=False, message=result.message)

    return OrderResult(
        success=True,
        message=result.message,
        symbol=result.symbol,
        type=result.type,
        volume=result.volume,
        price=result.price,
        time=result.time,
        order_id=result.order_id,
    )


def main() -> int:
    """コマンドラインから実行"""
    if len(sys.argv) < 4:
        print("Usage: python order.py <symbol> <buy|sell> <volume>", file=sys.stderr)
        return 1

    symbol = sys.argv[1]
    action = sys.argv[2]
    volume = float(sys.argv[3])

    result = execute_order(symbol=symbol, action=action, volume=volume)

    if result.success:
        time_str = result.time.strftime("%Y-%m-%d %H:%M:%S") if result.time else ""
        print(f"成功: {result.symbol} {result.type} {result.volume} lots @ {result.price} ({time_str})")
    else:
        print(f"失敗: {result.message}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
