"""
Cloudflare Tunnel 設定の起動時更新
API を使用して Ingress（ホスト名 → サービス）を設定する
"""

import base64
import json
import urllib.error
import urllib.request
from typing import Any


def decode_connector_token(token: str) -> tuple[str, str] | None:
    """
    コネクタトークンをデコードして account_id, tunnel_id を取得する

    Returns:
        (account_id, tunnel_id) または None
    """
    try:
        # トークンは base64 エンコードされた JSON
        decoded = base64.b64decode(token)
        data: dict[str, Any] = json.loads(decoded.decode("utf-8"))
        account_id = data.get("a")
        tunnel_id = data.get("t")
        if account_id and tunnel_id:
            return account_id, tunnel_id
    except (ValueError, json.JSONDecodeError, KeyError):
        pass
    return None


def update_tunnel_ingress(
    account_id: str,
    tunnel_id: str,
    api_token: str,
    hostname: str,
    service_url: str,
) -> bool:
    """
    Cloudflare API でトンネルの Ingress 設定を更新する

    Returns:
        成功した場合 True
    """
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations"
    payload = {
        "config": {
            "ingress": [
                {
                    "hostname": hostname,
                    "service": service_url,
                    "originRequest": {},
                },
                {"service": "http_status:404"},
            ]
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            return result.get("success", False)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"[警告] Ingress 更新失敗 (HTTP {e.code}): {body}")
        return False
    except urllib.error.URLError as e:
        print(f"[警告] Ingress 更新失敗: {e.reason}")
        return False
    except (json.JSONDecodeError, OSError) as e:
        print(f"[警告] Ingress 更新失敗: {e}")
        return False
