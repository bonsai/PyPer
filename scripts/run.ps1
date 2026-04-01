#!/usr/bin/env pwsh
# PyPer PR Times 実行スクリプト
# 使用方法：.\scripts\run.ps1

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " PyPer PR Times 実行" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot

# 環境変数ファイルのチェック
$envLocal = "$ProjectRoot\config\envs\.env.local"
if (Test-Path $envLocal) {
    Write-Host "環境変数：$envLocal" -ForegroundColor Gray
} else {
    Write-Host "警告：.env.local が見つかりません" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "PR Times からプレスリリースを取得して送信します..." -ForegroundColor Gray
Write-Host ""

python scripts\run_prtimes.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ 完了！" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "エラー：実行に失敗しました" -ForegroundColor Red
    exit 1
}
