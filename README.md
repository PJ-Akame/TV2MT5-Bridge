# SMCSE

TradingView のシグナルアラートを Webhook で受信し、ローカルで処理するシステム。

## バージョン

| 版 | 位置づけ |
|----|----------|
| **2.0**（現行） | Webhook 受信・`localServer`・Tunnel・**MT5 オーダー**に加え、TradingView 側の **Pine Script**（`PineScripts/SMCExecutionSignal.pine`、`smcse.entry.v1`）まで含めた一式。 |
| 1.0 | Webhook 受信から MT5 へのオーダー機能のみ。 |

## 構成

```
TradingView アラート
    ↓ Webhook (POST)
https://your-hostname.com (Cloudflare Tunnel)
    ↓
localServer (Python) ← localhost:8080
```

---

## 処理フロー

```mermaid
flowchart TB
    subgraph TV["TradingView"]
        A[アラート発火]
        B[Webhook POST 送信]
    end

    subgraph CF["Cloudflare Tunnel"]
        C[HTTPS 受信]
        D[localhost:8080 へ転送]
    end

    subgraph LS["localServer"]
        E[POST 受信]
        F[JSON パース]
        G[ログ出力]
        H{mt5.enabled?}
        I[config 読み込み]
        J[MQL5 パッケージ インポート]
        K[parse_webhook_for_mt5]
        L{注文意図あり?}
        M[EXCHANGE:SYMBOL を SYMBOL に変換済み]
        N[execute_order 呼び出し]
    end

    subgraph MQL5Bridge["MetaTrader 5 オーダー"]
        O[ターミナル起動確認]
        P[アカウント確認]
        Q[ポジション上限・取引禁止時間帯]
        R[成行注文送信]
    end

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H -->|true| I
    H -->|false| S[スキップ]
    I --> J
    J --> K
    K --> L
    L -->|No（No trade 等）| T[スキップ]
    L -->|Yes| M
    M --> N
    N --> O
    O --> P
    P --> Q
    Q --> R
```

### フロー説明

| ステップ | 説明 |
|----------|------|
| 1. TradingView | アラート条件が満たされると、設定した Webhook URL へ POST 送信 |
| 2. Cloudflare Tunnel | HTTPS で受信し、localhost:8080 へ転送 |
| 3. localServer | POST ボディを JSON としてパースし、ログに記録 |
| 4. ジョブ判定 | `config.webhook.job` が `mt5_order` の場合のみ MetaTrader 5 注文処理へ（`log_only` の場合はログのみ） |
| 5. 接続判定 | `config.mt5.enabled` が `true` の場合のみ注文処理へ |
| 6. ペイロード解釈 | `MQL5.webhook_parse.parse_webhook_for_mt5` で `smcse.entry.v1` またはレガシー形式を正規化（`message` / `payload` 等のラップも展開） |
| 7. 注文送信 | `order.execute_order`: ターミナル起動 → アカウント確認 → ポジション上限 → **取引禁止時間帯（`no_trade_windows`）** → `send_order` で成行 |

---

## Webhook POST リファレンス

### エンドポイント

| メソッド | URL | 説明 |
|----------|-----|------|
| POST | `https://your-hostname.com` | Webhook 受信・MetaTrader 5 注文実行 |
| GET | `https://your-hostname.com` | ヘルスチェック（`{"message":"Webhook server is running"}` を返す） |

### リクエスト形式

- **Content-Type**: `application/json`（推奨）
- **Body**: JSON 形式

### ペイロード（現在の想定）

#### 1) `smcse.entry.v1`（`SMCExecutionSignal.pine` / Mxwll Suite のエントリー評価）

TradingView の `alert()` が **有効な JSON 文字列のみ**を本文にすると、Webhook は `application/json` でそのオブジェクトが POST されます。

| 項目 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `schema` | string | 推奨 | 固定値 `"smcse.entry.v1"`。省略時も `result`＋`symbol` 等が揃えば v1 として解釈される |
| `result` | string | ○ | `"Buy"` / `"Sell"` / `"No trade"`（大文字小文字無視。`No trade` 時は MT5 注文しない） |
| `symbol` | string | ○* | 例: `FX:USDJPY`（`syminfo.tickerid`）。`EXCHANGE:SYMBOL` は注文時に `SYMBOL` のみ使用 |
| `upperObRef` | string | - | 上側 OB 参照価格の文字列表現または `"n/a"` |
| `upperObCount` | number | - | 範囲内・上側 OB 件数 |
| `lowerObRef` | string | - | 下側 OB 参照価格または `"n/a"` |
| `lowerObCount` | number | - | 範囲内・下側 OB 件数 |
| `lastPrice` | string | - | 判定時の終値（ミントック形式の文字列） |
| `positionPct` | number \| null | - | 最近 OB 間における価格位置（％）。該当なしは `null` |
| `volume` | number | - | ロット。省略時は `config.mt5.volume` |

\* `symbol` が無い場合は従来どおり `config.mt5.symbol` にフォールバック。

**例**

```json
{
  "schema": "smcse.entry.v1",
  "result": "Buy",
  "symbol": "FX:USDJPY",
  "upperObRef": "1672.646",
  "upperObCount": 2,
  "lowerObRef": "1589.987",
  "lowerObCount": 1,
  "lastPrice": "1650.123",
  "positionPct": 35.42
}
```

#### 2) レガシー（`symbol` + `action`）

| 項目 | 型 | 必須 | 説明 | フォールバック |
|------|-----|------|------|----------------|
| `symbol` | string | ○* | 通貨ペア（例: BTCUSD, USDJPY） | `symbol_name`, `ticker`, `config.mt5.symbol` |
| `action` | string | ○* | 注文方向 `buy` / `sell` | `trade`, `order`, `side`, `"buy"` |
| `volume` | number | - | ロット数 | `quantity`, `config.mt5.volume` (0.01) |

\* symbol はペイロードまたは config のいずれかで必須。action は未指定時 `"buy"`（`smcse.entry.v1` では使わない）。

### シンボル形式

- `BINANCE:BTCUSD` のように `EXCHANGE:SYMBOL` 形式の場合は、`SYMBOL` 部分のみ使用（例: `BTCUSD`）

### ペイロード例（レガシー）

**最小構成（symbol と action）**

```json
{"symbol": "BTCUSD", "action": "buy"}
```

**TradingView アラートの Message 欄用（{{ticker}} が展開される）**

```json
{"symbol": "{{ticker}}", "action": "buy"}
```

**フル指定**

```json
{"symbol": "USDJPY", "action": "sell", "volume": 0.01}
```

### レスポンス

**成功時（200 OK）**

```json
{"status": "ok", "received": { ... 受信したペイロード ... }}
```

### 代替キー名

ペイロードでは以下のキー名も認識されます（優先順）:

- **symbol**: `symbol` → `symbol_name` → `ticker`
- **action**: `action` → `trade` → `order` → `side`
- **volume**: `volume` → `quantity`

また、上位システムが `message`（文字列またはオブジェクト） / `text` / `raw` にネストした JSON を載せる場合、および `payload` / `body` / `data` がオブジェクトの場合、その内容をマージします。POST 本文が「JSON の文字列」がさらに JSON になっている二重エンコードの場合も `webhook_handler` で展開を試みます（`smcse.entry.v1` とレガシーの両方に適用）。

---

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

#### server（localServer）

| 項目 | 型 | 説明 |
|------|-----|------|
| `server.host` | string | バインドするホスト。全インターフェースで受信する場合は `0.0.0.0` |
| `server.port` | number | localServer のポート番号（デフォルト: 8080） |

#### webhook（Webhook 処理）

| 項目 | 型 | 説明 |
|------|-----|------|
| `webhook.job` | string | 受信後の処理ジョブ。`mt5_order`: MetaTrader 5 への成行注文実行 / `log_only`: ログ出力のみ |

#### tunnel（Cloudflare Tunnel）

| 項目 | 型 | 説明 |
|------|-----|------|
| `tunnel.token` | string | Cloudflare コネクタトークン。トンネル作成時にダッシュボードで取得 |
| `tunnel.hostname` | string | 公開するホスト名（例: `smcse.example.com`）。Ingress の Public Hostname に対応 |
| `tunnel.api_token` | string | Cloudflare API トークン。Ingress の起動時自動更新に使用。権限: Account - Cloudflare Tunnel - Edit |

#### mt5（MetaTrader 5）

| 項目 | 型 | 説明 |
|------|-----|------|
| `mt5.enabled` | boolean | MetaTrader 5 への注文を有効にする。`false` の場合は Webhook 受信時も注文しない |
| `mt5.volume` | number | デフォルトロット数。Webhook に volume が含まれない場合に使用（例: 0.01） |
| `mt5.magic` | number | EA ID（マジック番号）。注文・ポジションの識別用。他 EA と重複しない値にする |
| `mt5.comment` | string | 注文コメント。ターミナルでは 31 文字まで |
| `mt5.terminal_path` | string | MetaTrader 5 ターミナルの実行ファイルパス。空の場合は自動検出 |
| `mt5.symbol` | string | 対象シンボル（例: USDJPY, BTCUSD）。ペイロードに symbol がない場合のデフォルト |
| `mt5.position_limit` | number | 同一シンボルあたりのポジション上限。この件数に達すると新規オーダーを拒否。`0` の場合はチェックしない |
| `mt5.account_login` | number | 想定するアカウント番号。一致しないアカウントでログイン中はオーダーを拒否。`0` の場合はチェックしない |
| `mt5.no_trade_windows` | array | 取引禁止の時間帯。各要素は `{ "start": "HH:MM", "end": "HH:MM" }`。`end` が `start` より前の場合は日を跨ぐ区間（例: 23:00–06:00）。空配列 `[]` または未設定で無効 |
| `mt5.no_trade_timezone` | string | 禁止時間の判定に使う IANA タイムゾーン（例: `America/New_York`, `Asia/Tokyo`）。空の場合はサーバーのローカル時刻。`UTC` のみは `UTC` でも可（Python 3.9+ で `zoneinfo` が使える環境を推奨） |

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

## 2. localServer のセットアップ

Webhook を受信する Python サーバー。

### 起動

```powershell
cd localServer
python main.py
```

### ログ

受信データは `localServer/logs/webhook.log` に記録されます。

### MetaTrader 5 注文（オプション・MQL5 パッケージ）

Webhook で受信したシグナルを MetaTrader 5 に成行注文で送信できます。Python モジュールはリポジトリ直下の `MQL5/` にあります（`extras/MQL5/` の `.mq5` ソースとは別）。

**前提条件**

- MetaTrader 5 ターミナルが起動していること
- `pip install -r MQL5/requirements.txt` でパッケージをインストール
- `config.json` の `mt5.enabled` を `true` に設定

詳細は [Webhook POST リファレンス](#webhook-post-リファレンス) を参照。

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
   - ダッシュボードで設定するか、`config.json` の `tunnel.api_token` を設定すると起動時に自動更新
   - ホスト名: `your-subdomain.yourdomain.com`
   - サービス: `http://localhost:8080`

2. **DNS レコード**
   - タイプ: CNAME
   - 名前: `your-subdomain`（またはホスト名のサブドメイン部分）
   - ターゲット: `{トンネルID}.cfargotunnel.com`
   - トンネル ID はダッシュボードの Tunnels で確認

---

## 4. TradingView の設定

### メイン: `SMCExecutionSignal.pine`（Mxwll Suite）

1. TradingView でチャートを開く
2. 「Pine エディター」で `PineScripts/SMCExecutionSignal.pine` を貼り付け、チャートに追加
3. **アラートを作成** → 条件で本インジケーターを選び、`alert()` による通知を有効化（Webhook URL を設定）
4. **`smcse.entry.v1` の JSON** が本文として POST されます（ロット未指定時は `config.mt5.volume`）。詳細は [Webhook POST リファレンス](#webhook-post-リファレンス) の v1 形式を参照

### レガシー検証用（任意）

レガシーの `{"symbol","action"}` だけ試す場合は、同等の JSON をアラートのメッセージに手入力するか、独自の軽量 Pine を用意してください（リポジトリに分足テスト専用の `one_minute_alert.pine` は **含まれていません**。必要なら別途作成してください。）

---

## 5. 起動

### 一括起動（推奨）

```powershell
python smcse.py
```

Webhook と Tunnel を同時に起動します。Ctrl+C で終了。

### 個別起動

1. **Webhook サーバー（`localServer`）** を起動
   ```powershell
   cd localServer
   python main.py
   ```

2. **Tunnel** を起動（別ターミナルで）
   ```powershell
   cd tunnel
   python main.py
   ```

3. TradingView でアラートを有効化

---

## ディレクトリ構成

```
SMCSE/
├── smcse.py                  # 統合起動スクリプト（Webhook + Tunnel）
├── config/
│   ├── config.json.example   # 設定テンプレート
│   └── config.json           # 実際の設定（Git に含めない）
├── localServer/              # Webhook 受信サーバー
├── MQL5/                     # MetaTrader 5 連携（Python）。MQL5 ソースは extras/MQL5/
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

- localServer と Tunnel の両方が起動しているか確認
- Cloudflare ダッシュボードでトンネルが Healthy か確認
- Ingress の Service が `http://localhost:8080` になっているか確認
