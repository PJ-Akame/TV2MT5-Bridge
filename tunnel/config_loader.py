"""
設定ファイル読み込み
config/config.json からサーバー設定を取得する（Tunnel 用）
"""

import json
from pathlib import Path
from typing import Any


def get_config_path() -> Path:
    """config.json のパスを返す（SMCSE/config を基準）"""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "config" / "config.json"


def get_server_port() -> int:
    """
    サーバーポートを取得する（LocalServer と同期）

    Returns:
        ポート番号
    """
    default_port = 8080

    try:
        config_path = get_config_path()
        if not config_path.exists():
            return default_port

        with open(config_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)
        server = config.get("server", {})
        return int(server.get("port", default_port))
    except (json.JSONDecodeError, ValueError):
        return default_port


def get_tunnel_token() -> str | None:
    """
    Cloudflare Tunnel のトークンを取得する（Named Tunnel 用）

    Returns:
        トークン文字列。未設定の場合は None
    """
    try:
        config_path = get_config_path()
        if not config_path.exists():
            return None

        with open(config_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)
        tunnel = config.get("tunnel", {})
        token = tunnel.get("token", "").strip()
        return token if token else None
    except (json.JSONDecodeError, ValueError):
        return None


def get_tunnel_hostname() -> str | None:
    """
    トンネルの公開ホスト名を取得する

    Returns:
        ホスト名（例: your-subdomain.example.com）。未設定の場合は None
    """
    try:
        config_path = get_config_path()
        if not config_path.exists():
            return None

        with open(config_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)
        tunnel = config.get("tunnel", {})
        hostname = tunnel.get("hostname", "").strip()
        return hostname if hostname else None
    except (json.JSONDecodeError, ValueError):
        return None


def get_tunnel_api_token() -> str | None:
    """
    Cloudflare API トークンを取得する（Ingress 更新用）

    Returns:
        API トークン。未設定の場合は None
    """
    try:
        config_path = get_config_path()
        if not config_path.exists():
            return None

        with open(config_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)
        tunnel = config.get("tunnel", {})
        api_token = tunnel.get("api_token", "").strip()
        return api_token if api_token else None
    except (json.JSONDecodeError, ValueError):
        return None
