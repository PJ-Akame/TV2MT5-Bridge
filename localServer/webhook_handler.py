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
        decoded = body.decode("utf-8", errors="replace") if body else ""
        try:
            decoded_stripped = decoded.strip()
            # BOM や前後の空白を除去
            if decoded_stripped.startswith("\ufeff"):
                decoded_stripped = decoded_stripped[1:]
            result = json.loads(decoded_stripped) if decoded_stripped else {}
        except json.JSONDecodeError:
            result = {"raw": decoded}

        self._output_to_terminal(result)

        # config.webhook.job で指定されたジョブを実行
        self._run_job(result)

        return result

    def _run_job(self, payload: dict) -> None:
        """config.webhook.job に応じて処理ジョブを実行する"""
        try:
            from config_loader import load_config
            config = load_config()
        except Exception as e:
            _write_log(f"[Job] スキップ: config 読み込みエラー - {e}\n")
            return

        job = config.get("webhook", {}).get("job", "mt5_order")
        if job == "mt5_order":
            self._execute_mt5_order(payload)
        elif job == "log_only":
            pass  # ログ出力のみ（既に _output_to_terminal で実施済み）
        else:
            _write_log(f"[Job] 不明な job: '{job}' (mt5_order / log_only を指定してください)\n")

    def _execute_mt5_order(self, payload: dict) -> None:
        """Webhook ペイロードから MetaTrader 5 注文を実行し、結果をログに記録する"""
        # config で取引が有効か判定
        try:
            from config_loader import load_config
            config = load_config()
            if not config.get("mt5", {}).get("enabled", False):
                _write_log("[MQL5] スキップ: mt5.enabled が false です\n")
                return
        except Exception as e:
            _write_log(f"[MQL5] スキップ: config 読み込みエラー - {e}\n")
            return

        try:
            # プロジェクトルートを path に追加して MQL5 パッケージをインポート
            _root = Path(__file__).resolve().parent.parent
            if str(_root) not in sys.path:
                sys.path.insert(0, str(_root))
            from MQL5.order import execute_order
        except ImportError as e:
            _write_log(f"[MQL5] スキップ: MQL5 モジュールのインポートに失敗 - {e}\n")
            return

        mt5_config = config.get("mt5", {})

        # ペイロードから symbol, action, volume を取得（message が JSON の場合はパース）
        payload_to_use = payload.copy()
        if "message" in payload and isinstance(payload["message"], str):
            try:
                msg_parsed = json.loads(payload["message"])
                if isinstance(msg_parsed, dict):
                    payload_to_use = {**payload_to_use, **msg_parsed}
            except json.JSONDecodeError:
                pass

        # raw が JSON 形式の文字列の場合はパースしてマージ
        if "raw" in payload_to_use and isinstance(payload_to_use["raw"], str):
            raw = payload_to_use["raw"].strip()
            if raw.startswith("{"):
                try:
                    raw_parsed = json.loads(raw)
                    if isinstance(raw_parsed, dict):
                        payload_to_use = {**payload_to_use, **raw_parsed}
                except json.JSONDecodeError:
                    pass

        # POST された JSON から symbol, action, volume を取得（config はフォールバック）
        symbol = payload_to_use.get("symbol") or payload_to_use.get("symbol_name") or payload_to_use.get("ticker") or mt5_config.get("symbol")
        action = payload_to_use.get("action") or payload_to_use.get("trade") or payload_to_use.get("order") or payload_to_use.get("side") or "buy"
        volume = float(payload_to_use.get("volume", payload_to_use.get("quantity", mt5_config.get("volume", 0.01))))

        if not symbol:
            _write_log("[MQL5] スキップ: symbol が指定されていません（ペイロードにも config.mt5.symbol にもありません）\n")
            return

        # {{ticker}} が "EXCHANGE:SYMBOL" 形式の場合はシンボル部分のみ使用
        if ":" in str(symbol):
            symbol = str(symbol).split(":")[-1]

        try:
            order_result = execute_order(symbol=str(symbol), action=str(action), volume=volume)
            mt5_log = (
                f"[MQL5] {'成功' if order_result.success else '失敗'}: {order_result.message}"
                + (f" (order={order_result.order_id})" if order_result.order_id else "")
            )
            _write_log(f"{mt5_log}\n")
            sys.stdout.write(f"\n{mt5_log}\n")
            sys.stdout.flush()
        except Exception as e:
            _write_log(f"[MQL5] 例外: execute_order 実行中 - {e}\n")
            sys.stderr.write(f"[MQL5] 例外: {e}\n")
            sys.stderr.flush()

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
