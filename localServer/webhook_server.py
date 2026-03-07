"""
Webhook 受信サーバー
HTTP サーバーを起動し、Webhook リクエストを受け付ける
"""

from http.server import HTTPServer
from typing import Type

from webhook_handler import WebhookHandler, init_log


class WebhookServer:
    """Webhook 受信用 HTTP サーバー"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """
        Args:
            host: バインドするホスト（0.0.0.0 で全インターフェース）
            port: リッスンポート
        """
        self._host = host
        self._port = port
        self._server: HTTPServer | None = None

    @property
    def url(self) -> str:
        """サーバーの URL を返す"""
        return f"http://localhost:{self._port}"

    def start(self, handler_class: Type[WebhookHandler] = WebhookHandler) -> None:
        """
        サーバーを起動する

        Args:
            handler_class: 使用するリクエストハンドラクラス
        """
        self._server = HTTPServer((self._host, self._port), handler_class)
        print(f"Webhook サーバー起動: {self.url}")
        ok, log_path = init_log()
        if ok:
            print(f"受信ログ: {log_path}")
        else:
            print(f"[警告] ログファイルの作成に失敗しました: {log_path}")
        print("Ctrl+C で終了")
        print("-" * 40)
        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """サーバーを停止する"""
        if self._server:
            self._server.shutdown()
            self._server = None
            print("\nサーバーを停止しました")
