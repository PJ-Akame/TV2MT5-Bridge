"""
MT5 オーダー実行スクリプト
1. MT5 起動確認
2. 取引アカウント確認
3. ポジション上限チェック（上限未満の時のみ実行）
4. オーダー実行
"""

from __future__ import annotations

import json
import sys
import threading
from dataclasses import dataclass
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
    """config.json から MT5 設定を読み込む"""
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
    MT5 起動確認

    Returns:
        (成功, メッセージ) 失敗時はメッセージに「未起動」等を返す
    """
    if mt5 is None:
        return False, "MetaTrader5 パッケージがインストールされていません"

    init_params: dict[str, Any] = {}
    if terminal_path:
        init_params["path"] = terminal_path

    if not mt5.initialize(**init_params):
        return False, "MT5 が未起動です。ターミナルを起動してください"

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


def execute_order(
    symbol: str,
    action: str,
    volume: float = 0.01,
    config: dict[str, Any] | None = None,
) -> OrderResult:
    """
    オーダーを実行する（3ステップフロー）

    1. MT5 起動確認
    2. 取引アカウント確認
    3. ポジション上限チェック（position_limit 未満の時のみ実行）
    4. オーダー実行

    Args:
        symbol: 通貨ペア
        action: "buy" または "sell"
        volume: ロット数
        config: MT5 設定（省略時は config から読み込み）

    Returns:
        OrderResult: 実行結果（成功時は symbol, type, volume, price を含む）
    """
    if config is None:
        config = _load_config()

    terminal_path = (config.get("terminal_path") or "").strip() or None
    expected_login = int(config.get("account_login", 0))

    # 1. MT5 起動確認
    ok, msg = _check_mt5_running(terminal_path)
    if not ok:
        return OrderResult(success=False, message=msg)

    try:
        # 2. 取引アカウント確認
        ok, msg = _check_account(expected_login)
        if not ok:
            return OrderResult(success=False, message=msg)
    finally:
        _safe_shutdown()

    # 3. ポジション上限チェック（上限未満の時のみオーダー実行）
    position_limit = int(config.get("position_limit", 1))
    if position_limit > 0:
        try:
            from MT5.get_positions import get_positions
        except ImportError:
            from get_positions import get_positions
        current_count = get_positions(symbol=symbol)
        if current_count >= position_limit:
            return OrderResult(
                success=False,
                message=f"ポジション上限に達しています。{symbol}: 現在 {current_count} 件、上限 {position_limit} 件",
            )

    # 4. オーダー実行（send_order は内部で initialize/shutdown を行う）
    try:
        from MT5.mt5_order import send_order
    except ImportError:
        from mt5_order import send_order

    result = send_order(
        symbol=symbol,
        action=action,
        volume=volume,
        magic=int(config.get("magic", 234000)),
        comment=str(config.get("comment", "SMCSE"))[:31],
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
