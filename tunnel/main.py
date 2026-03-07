"""
Cloudflare Tunnel エントリポイント
config/config.json のポートを参照し、Quick Tunnel を起動する
"""

from tunnel_runner import run_tunnel


def main() -> None:
    """メイン処理"""
    exit(run_tunnel())


if __name__ == "__main__":
    main()
