"""
Webhook リクエストハンドラ
TradingView 等からの Webhook リクエストを処理し、結果をターミナルに出力する
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler

# ログファイルパス（スクリプトと同じディレクトリの logs/webhook.log）
_SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = _SCRIPT_DIR / "logs"
LOG_FILE = LOG_DIR / "webhook.log"
_ACTIVE_LOG_FILE: Path = LOG_FILE  # init_log でフォールバック時に更新


def _ensure_log_dir() -> None:
    """ログディレクトリを作成する"""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.stderr.write(f"[ログディレクトリ作成エラー] {LOG_DIR}: {e}\n")
        sys.stderr.flush()
        raise


def _write_log(message: str) -> None:
    """ログファイルに書き込む（ターミナル非表示時も確実に記録）"""
    global _ACTIVE_LOG_FILE
    try:
        _ACTIVE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_ACTIVE_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message)
            f.flush()
    except OSError as e:
        sys.stderr.write(f"[ログ書き込みエラー] {_ACTIVE_LOG_FILE}: {e}\n")
        sys.stderr.flush()


def init_log() -> tuple[bool, Path]:
    """起動時にログを初期化し、書き込み可能か確認する。戻り値: (成功, ログパス)"""
    try:
        _ensure_log_dir()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n--- サーバー起動 {datetime.now().isoformat()} ---\n")
            f.flush()
        return True, LOG_FILE
    except OSError as e:
        # フォールバック: カレントディレクトリに webhook.log を作成
        fallback = Path.cwd() / "webhook.log"
        try:
            with open(fallback, "a", encoding="utf-8") as f:
                f.write(f"\n--- サーバー起動 {datetime.now().isoformat()} (フォールバック) ---\n")
                f.flush()
            global _ACTIVE_LOG_FILE
            _ACTIVE_LOG_FILE = fallback
            sys.stderr.write(f"[注意] ログをフォールバック先に出力: {fallback}\n")
            sys.stderr.flush()
            return True, fallback
        except OSError as e2:
            sys.stderr.write(f"[ログ初期化エラー] {LOG_FILE}: {e}\nフォールバックも失敗: {e2}\n")
            sys.stderr.flush()
            return False, LOG_FILE


class WebhookHandler(BaseHTTPRequestHandler):
    """Webhook の HTTP リクエストを処理するハンドラ"""

    def do_POST(self) -> None:
        """POST リクエストを処理（TradingView は POST で送信）"""
        try:
            content_length = int(self.headers.get("Content-Length") or 0)
        except (ValueError, TypeError):
            content_length = 0

        body = self.rfile.read(content_length) if content_length > 0 else b""

        result = self._parse_and_display(body)
        self._send_success_response(result)

    def do_GET(self) -> None:
        """GET リクエスト（ヘルスチェック等）用"""
        self._send_success_response({"message": "Webhook server is running"})

    def _parse_and_display(self, body: bytes) -> dict:
        """受信ボディをパースし、ターミナルに整形して出力する"""
        result: dict = {}
        try:
            decoded = body.decode("utf-8")
            result = json.loads(decoded) if decoded else {}
        except json.JSONDecodeError:
            result = {"raw": body.decode("utf-8", errors="replace")}

        self._output_to_terminal(result)
        return result

    def _output_to_terminal(self, data: dict) -> None:
        """受信データをターミナルとログファイルに出力する"""
        separator = "=" * 50
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output = (
            f"\n{separator}\n"
            f"  Webhook 受信 [{timestamp}]\n"
            f"{separator}\n"
            f"{json.dumps(data, indent=2, ensure_ascii=False)}\n"
            f"{separator}\n"
        )
        # ログファイルに必ず記録（ターミナルが表示しない場合の対策）
        _write_log(output)
        # ターミナルにも出力
        sys.stdout.write(output)
        sys.stdout.flush()
        sys.stderr.write(output)
        sys.stderr.flush()

    def _send_success_response(self, data: dict) -> None:
        """成功レスポンスを送信する"""
        response_body = json.dumps({"status": "ok", "received": data}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format: str, *args) -> None:
        """アクセスログを抑制"""
        pass
