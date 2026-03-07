"""
SMCSE 統合起動スクリプト
LocalServer（Webhook）と Cloudflare Tunnel を同時に起動する
"""

import signal
import subprocess
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> int:
    """Webhook と Tunnel を起動"""
    print("SMCSE 起動中...")
    print(f"  プロジェクトルート: {_PROJECT_ROOT}")
    print()

    # LocalServer（Webhook）
    webhook_script = _PROJECT_ROOT / "LocalServer" / "main.py"
    if not webhook_script.exists():
        webhook_script = _PROJECT_ROOT / "localServer" / "main.py"
    if not webhook_script.exists():
        print("[エラー] LocalServer/main.py が見つかりません")
        return 1

    # Tunnel
    tunnel_script = _PROJECT_ROOT / "tunnel" / "main.py"
    if not tunnel_script.exists():
        print("[エラー] tunnel/main.py が見つかりません")
        return 1

    procs: list[subprocess.Popen] = []

    def cleanup() -> None:
        for p in procs:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()

    def on_signal(signum: int, frame: object) -> None:
        print("\n終了しています...")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, on_signal)

    try:
        # Webhook 起動
        print("LocalServer（Webhook）を起動...")
        p_webhook = subprocess.Popen(
            [sys.executable, str(webhook_script)],
            cwd=str(_PROJECT_ROOT),
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        procs.append(p_webhook)

        # Tunnel 起動
        print("Cloudflare Tunnel を起動...")
        p_tunnel = subprocess.Popen(
            [sys.executable, str(tunnel_script)],
            cwd=str(_PROJECT_ROOT),
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        procs.append(p_tunnel)

        print()
        print("=" * 50)
        print("  SMCSE 起動完了")
        print("  - Webhook: LocalServer")
        print("  - Tunnel: Cloudflare Tunnel")
        print("  Ctrl+C で終了")
        print("=" * 50)
        print()

        # いずれかが終了するまで待機
        while True:
            for p in procs:
                if p.poll() is not None:
                    print(f"\n[終了] プロセスが終了しました (code={p.returncode})")
                    cleanup()
                    return p.returncode or 1
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n終了しています...")
        cleanup()
        return 0


if __name__ == "__main__":
    sys.exit(main())
