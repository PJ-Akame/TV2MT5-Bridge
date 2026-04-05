"""
Cloudflare Tunnel 実行モジュール
config のポートを参照し、Quick Tunnel または Named Tunnel を起動する
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from config_loader import (
    get_server_port,
    get_tunnel_hostname,
    get_tunnel_token,
    get_tunnel_api_token,
)
from tunnel_config import decode_connector_token, update_tunnel_ingress


def get_local_cloudflared_path() -> Path:
    """tunnel 配下の cloudflared パスを返す（OS に応じたバイナリ名）"""
    tunnel_dir = Path(__file__).resolve().parent
    exe_name = "cloudflared.exe" if sys.platform == "win32" else "cloudflared"
    return tunnel_dir / "bin" / exe_name


def find_cloudflared() -> str | None:
    """cloudflared 実行ファイルのパスを取得する（tunnel/bin を優先）"""
    # 1. tunnel/bin/ 配下を最優先
    local_path = get_local_cloudflared_path()
    if local_path.exists():
        return str(local_path)

    # 2. PATH から検索
    cloudflared = shutil.which("cloudflared")
    if cloudflared:
        return cloudflared

    # 3. Windows: 一般的なインストール場所を確認（ProgramFiles は通常設定済み）
    if sys.platform == "win32":
        program_files = Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
        local_app_data = os.environ.get("LOCALAPPDATA")
        candidates = [
            program_files / "cloudflared" / "cloudflared.exe",
        ]
        if local_app_data:
            candidates.append(Path(local_app_data) / "cloudflared" / "cloudflared.exe")
        for path in candidates:
            if path.exists():
                return str(path)

    return None


def run_tunnel() -> int:
    """
    Cloudflare Tunnel を起動する
    config に token が設定されている場合は Named Tunnel、なければ Quick Tunnel

    Returns:
        終了コード
    """
    cloudflared_path = find_cloudflared()
    if not cloudflared_path:
        local_path = get_local_cloudflared_path()
        print("[エラー] cloudflared が見つかりません。")
        print()
        print("tunnel 配下にインストール:")
        print("  cd tunnel")
        print("  python install_cloudflared.py")
        print()
        print(f"  → {local_path} に配置されます")
        return 1

    token = get_tunnel_token()
    hostname = get_tunnel_hostname()
    api_token = get_tunnel_api_token()
    port = get_server_port()
    service_url = f"http://localhost:{port}"

    if token:
        # Named Tunnel: 既存の Cloudflare アカウントのトンネルを使用
        # 起動時に Ingress を設定（hostname + api_token がある場合）
        if hostname and api_token:
            ids = decode_connector_token(token)
            if ids:
                account_id, tunnel_id = ids
                if update_tunnel_ingress(
                    account_id, tunnel_id, api_token, hostname, service_url
                ):
                    print(f"  Ingress 設定完了: {hostname} → {service_url}")
                else:
                    print("  [注意] Ingress の更新に失敗しました。ダッシュボードで確認してください")
            else:
                print("  [注意] トークンのデコードに失敗しました")
        elif hostname and not api_token:
            print("  [注意] tunnel.api_token が未設定です。Ingress はダッシュボードで設定してください")

        print()
        print("=" * 50)
        print("  Cloudflare Tunnel 起動 (Named Tunnel)")
        print("=" * 50)
        print()
        if hostname:
            print(f"  公開 URL: https://{hostname}")
        else:
            print("  ダッシュボードで設定したホスト名で公開されます")
        print(f"  転送先: {service_url}")
        print()
        print("  Ctrl+C で終了")
        print("=" * 50)
        print()

        cmd = [cloudflared_path, "tunnel", "run", "--token", token]
    else:
        # Quick Tunnel: ランダム URL
        port = get_server_port()
        tunnel_url = f"http://localhost:{port}"

        print()
        print("=" * 50)
        print("  Cloudflare Tunnel 起動 (Quick Tunnel)")
        print("=" * 50)
        print()
        print(f"  転送先: {tunnel_url}")
        print(f"  (localServer が localhost:{port} で起動している必要があります)")
        print()
        print("  config に tunnel.token を設定すると Named Tunnel を利用できます")
        print()
        print("  Ctrl+C で終了")
        print("=" * 50)
        print()

        cmd = [cloudflared_path, "tunnel", "--url", tunnel_url]

    process: subprocess.Popen[bytes] | None = None

    def cleanup() -> None:
        """トンネルプロセスを停止する"""
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            print("\nトンネルを停止しました")

    try:
        process = subprocess.Popen(cmd)
        return process.wait()
    except KeyboardInterrupt:
        cleanup()
        return 0
