"""
設定ファイル読み込み
config/config.json からサーバー設定を取得する
"""

import json
from pathlib import Path
from typing import Any


def get_config_path() -> Path:
    """config.json のパスを返す（SMCSE/config を基準）"""
    # LocalServer から見た config の相対パス
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "config" / "config.json"


def load_config() -> dict[str, Any]:
    """
    config.json を読み込む

    Returns:
        設定辞書。ファイルが存在しない場合はデフォルト値を返す

    Raises:
        FileNotFoundError: config.json が存在しない場合
        json.JSONDecodeError: JSON のパースに失敗した場合
    """
    config_path = get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def get_server_config() -> tuple[str, int]:
    """
    サーバー設定（host, port）を取得する

    Returns:
        (host, port) のタプル
    """
    default_host = "0.0.0.0"
    default_port = 8080

    try:
        config = load_config()
        server = config.get("server", {})
        host = server.get("host", default_host)
        port = int(server.get("port", default_port))
        return host, port
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"[警告] 設定の読み込みに失敗しました。デフォルト値を使用します: {e}")
        return default_host, default_port
