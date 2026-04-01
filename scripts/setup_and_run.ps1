#!/usr/bin/env pwsh
# PyPer PR Times セットアップ＆実行スクリプト
# 使用方法：.\scripts\setup_and_run.ps1

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " PyPer PR Times セットアップ＆実行" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ステップ 1: 依存関係のインストール
Write-Host "[ステップ 1] 依存関係のインストール" -ForegroundColor Yellow
Set-Location "$ProjectRoot\src"

if (Test-Path "requirements.txt") {
    Write-Host "pip install -r requirements.txt..." -ForegroundColor Gray
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "エラー：依存関係のインストールに失敗しました" -ForegroundColor Red
        exit 1
    }
    Write-Host " ✓ 依存関係のインストール完了" -ForegroundColor Green
} else {
    Write-Host "警告：requirements.txt が見つかりません" -ForegroundColor Yellow
}

Write-Host ""

# ステップ 2: 環境変数ファイルの準備
Write-Host "[ステップ 2] 環境変数ファイルの準備" -ForegroundColor Yellow
Set-Location $ProjectRoot

$envExample = "$ProjectRoot\config\envs\.env.example"
$envLocal = "$ProjectRoot\config\envs\.env.local"

if (Test-Path $envExample) {
    if (-not (Test-Path $envLocal)) {
        Copy-Item $envExample $envLocal
        Write-Host " ✓ .env.local を作成しました" -ForegroundColor Green
        Write-Host ""
        Write-Host " IMPORTANT: .env.local を編集して認証情報を設定してください" -ForegroundColor Cyan
        Write-Host " $envLocal" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Host " ✓ .env.local は既に存在します" -ForegroundColor Green
    }
} else {
    Write-Host "警告：.env.example が見つかりません" -ForegroundColor Yellow
}

Write-Host ""

# ステップ 3: OAuth 認証チェック
Write-Host "[ステップ 3] OAuth 認証チェック" -ForegroundColor Yellow

if (Test-Path $envLocal) {
    $envContent = Get-Content $envLocal -Raw
    
    $hasClientId = $envContent -match 'OAUTH_CLIENT_ID=.+'
    $hasClientSecret = $envContent -match 'OAUTH_CLIENT_SECRET=.+'
    $hasRefreshToken = $envContent -match 'OAUTH_REFRESH_TOKEN=.+'
    
    if ($hasClientId -and $hasClientSecret -and $hasRefreshToken) {
        Write-Host " ✓ OAuth 認証情報が設定されています" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host " OAuth 認証が必要です。セットアップを実行しますか？" -ForegroundColor Cyan
        Write-Host " (Y/N): " -NoNewline -ForegroundColor Yellow
        
        $response = Read-Host
        if ($response -eq 'Y' -or $response -eq 'y') {
            Write-Host ""
            Write-Host "OAuth セットアップスクリプトを実行中..." -ForegroundColor Gray
            Set-Location $ProjectRoot
            python scripts\setup_oauth.py
            if ($LASTEXITCODE -ne 0) {
                Write-Host "エラー：OAuth セットアップに失敗しました" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "OAuth セットアップをスキップします" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "警告：.env.local が見つかりません" -ForegroundColor Yellow
}

Write-Host ""

# ステップ 4: パイプライン実行
Write-Host "[ステップ 4] パイプライン実行" -ForegroundColor Yellow
Set-Location $ProjectRoot

Write-Host "PR Times からプレスリリースを取得して送信します..." -ForegroundColor Gray
Write-Host ""

python scripts\run_prtimes.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " 完了！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "エラー：パイプラインの実行に失敗しました" -ForegroundColor Red
    exit 1
}

Set-Location $ScriptRoot
