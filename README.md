# SMCSE

TradingView のシグナルアラートを Webhook で受信し、ローカルで処理するシステム。

## 構成

```
TradingView アラート
    ↓ Webhook (POST)
https://your-hostname.com (Cloudflare Tunnel)
    ↓
LocalServer (Python) ← localhost:8080
```

## 前提条件

- Python 3.8+
- Cloudflare アカウント
- ドメイン（Cloudflare に追加済み、ネームサーバー設定済み）

---

## 1. 設定ファイルの準備

### config.json の作成

`config/config.json` は Git に含まれません。テンプレートから作成してください。

```powershell
copy config\config.json.example config\config.json
```

### 設定項目

| 項目 | 説明 |
|------|------|
| `server.host` | バインドするホスト（通常は `0.0.0.0`） |
| `server.port` | LocalServer のポート（デフォルト: 8080） |
| `tunnel.token` | Cloudflare コネクタトークン |
| `tunnel.hostname` | 公開するホスト名（例: `smcse.example.com`） |
| `tunnel.api_token` | Cloudflare API トークン（Ingress 更新用） |

### トークンの取得

**コネクタトークン（tunnel.token）**

1. [Cloudflare ダッシュボード](https://dash.cloudflare.com/) → Zero Trust または Networks → Tunnels
2. トンネルを作成
3. インストールコマンドに表示されるトークンをコピー

**API トークン（tunnel.api_token）**

1. Cloudflare ダッシュボード → マイプロファイル → API トークン
2. カスタムトークンを作成
3. 権限: **Account** - **Cloudflare Tunnel** - **Edit**
4. トークンをコピー

---

## 2. LocalServer のセットアップ

Webhook を受信する Python サーバー。

### 起動

```powershell
cd LocalServer
python main.py
```

### 動作確認

別ターミナルで:

```powershell
cd LocalServer
.\test_post.ps1
```

または:

```powershell
$body = '{"symbol":"USDJPY","action":"buy"}'
Invoke-RestMethod -Uri "http://localhost:8080" -Method POST -ContentType "application/json" -Body $body
```

### ログ

受信データは `LocalServer/logs/webhook.log` に記録されます。

---

## 3. Cloudflare Tunnel のセットアップ

### cloudflared のインストール（tunnel 配下）

```powershell
cd tunnel
python install_cloudflared.py
```

### 起動

```powershell
cd tunnel
python main.py
```

### Cloudflare ダッシュボードでの設定

1. **Public Hostname（Ingress）**
   - ダッシュボードで設定するか、`config.json` の `api_token` を設定すると起動時に自動更新
   - ホスト名: `your-subdomain.yourdomain.com`
   - サービス: `http://localhost:8080`

2. **DNS レコード**
   - タイプ: CNAME
   - 名前: `your-subdomain`（またはホスト名のサブドメイン部分）
   - ターゲット: `{トンネルID}.cfargotunnel.com`
   - トンネル ID はダッシュボードの Tunnels で確認

### 疎通確認

```powershell
# DNS 解決の確認
nslookup your-subdomain.yourdomain.com

# 外部 URL へのアクセス確認
Invoke-RestMethod -Uri "https://your-subdomain.yourdomain.com" -Method GET
```

---

## 4. TradingView の設定

### Pine Script の追加

1. TradingView でチャートを開く
2. 下部の「Pine エディター」を開く
3. `PineScripts/one_minute_alert.pine` の内容をコピー＆ペースト
4. 「チャートに追加」をクリック

### アラートの作成

1. チャート上で右クリック → 「アラートを追加」
2. 条件: 「1分毎アラート」（または使用するスクリプトのアラート名）
3. 通知: 「Webhook URL」を選択
4. URL: `https://your-subdomain.yourdomain.com`
5. メッセージ: スクリプトのデフォルト、またはカスタム JSON

---

## 5. 起動順序

1. **LocalServer** を起動
   ```powershell
   cd LocalServer
   python main.py
   ```

2. **Tunnel** を起動
   ```powershell
   cd tunnel
   python main.py
   ```

3. TradingView でアラートを有効化

---

## ディレクトリ構成

```
SMCSE/
├── config/
│   ├── config.json.example   # 設定テンプレート
│   └── config.json           # 実際の設定（Git に含めない）
├── LocalServer/              # Webhook 受信サーバー
├── tunnel/                   # Cloudflare Tunnel
├── PineScripts/              # TradingView 用 Pine Script
└── README.md
```

---

## トラブルシューティング

### ポート 8080 が使用中

```powershell
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

### DNS が解決できない

- Cloudflare ダッシュボードで CNAME レコードを確認
- 反映に数分かかることがあります

### 外部から受信できない

- LocalServer と Tunnel の両方が起動しているか確認
- Cloudflare ダッシュボードでトンネルが Healthy か確認
- Ingress の Service が `http://localhost:8080` になっているか確認
