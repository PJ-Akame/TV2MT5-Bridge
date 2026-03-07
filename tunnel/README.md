# Cloudflare Tunnel

## 起動時の Ingress 設定

`config/config.json` の `tunnel.api_token` を設定すると、起動時に `tunnel.hostname` で指定したホスト名で受信するよう Ingress が自動設定されます。

### API トークンの取得

1. [Cloudflare ダッシュボード](https://dash.cloudflare.com/) にログイン
2. マイプロファイル → API トークン → トークンを作成
3. カスタムトークンを作成し、以下の権限を付与:
   - **Account** - Cloudflare Tunnel - Edit
4. トークンをコピーし、`config/config.json` の `tunnel.api_token` に設定

```json
{
  "tunnel": {
    "token": "コネクタトークン",
    "hostname": "your-subdomain.example.com",
    "api_token": "APIトークン"
  }
}
```

### 注意事項

- `tunnel.hostname` で指定したドメインが Cloudflare に追加され、ネームサーバーが Cloudflare に設定されている必要があります
- `api_token` が未設定の場合、Ingress はダッシュボードで手動設定してください
