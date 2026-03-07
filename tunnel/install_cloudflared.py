"""
cloudflared を tunnel/bin/ 配下にダウンロード・インストールする
"""

import sys
import urllib.request
from pathlib import Path

# GitHub の最新リリース（Windows amd64）
DOWNLOAD_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"


def get_bin_dir() -> Path:
    """tunnel/bin のパスを返す"""
    return Path(__file__).resolve().parent / "bin"


def install() -> bool:
    """
    cloudflared をダウンロードして tunnel/bin/ に配置する

    Returns:
        成功した場合 True
    """
    bin_dir = get_bin_dir()
    output_path = bin_dir / "cloudflared.exe"

    print("cloudflared を tunnel 配下にインストールします")
    print(f"  保存先: {output_path}")
    print()

    try:
        bin_dir.mkdir(parents=True, exist_ok=True)

        print("ダウンロード中...")
        with urllib.request.urlopen(DOWNLOAD_URL, timeout=60) as response:
            data = response.read()

        output_path.write_bytes(data)
        print("インストール完了")
        print()
        print("実行方法:")
        print("  python main.py")
        print("  または run_tunnel.bat")
        return True

    except urllib.error.URLError as e:
        print(f"[エラー] ダウンロードに失敗しました: {e}")
        print()
        print("手動インストール:")
        print("  1. https://github.com/cloudflare/cloudflared/releases にアクセス")
        print("  2. cloudflared-windows-amd64.exe をダウンロード")
        print(f"  3. {output_path} にリネームして配置")
        return False
    except OSError as e:
        print(f"[エラー] ファイルの書き込みに失敗しました: {e}")
        return False


def main() -> int:
    """メイン処理"""
    success = install()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
