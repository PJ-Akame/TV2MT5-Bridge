"""
Webhook 受信サーバー エントリポイント
"""

from config_loader import get_server_config
from webhook_server import WebhookServer


def main() -> None:
    """メイン処理"""
    host, port = get_server_config()
    server = WebhookServer(host=host, port=port)
    server.start()


if __name__ == "__main__":
    main()
