Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath ".env")) {
    Write-Host "Tip: copy deploy/.env.example to deploy/.env and set OPENROUTER_API_KEY (optional)." -ForegroundColor Yellow
}
docker compose -f docker-compose.yml up --build @args
