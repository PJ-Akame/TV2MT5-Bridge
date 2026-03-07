# Webhook テスト用 POST スクリプト
# PowerShell のエスケープ問題を回避
# ポートは config/config.json の server.port から読み込み（未設定時は 8080）

$configPath = Join-Path (Split-Path $PSScriptRoot -Parent) "config\config.json"
$port = 8080
if (Test-Path $configPath) {
    $config = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($config.server.port) { $port = $config.server.port }
}

$body = @{
    symbol  = "USDJPY"
    action  = "buy"
    close   = "149.50"
    message = "TradingView test"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:$port" -Method POST -ContentType "application/json" -Body $body
