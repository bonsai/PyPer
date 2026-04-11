# Scripts Directory

このディレクトリには、PyPer の実行・設定・デプロイに関するスクリプトが配置されています。

## ファイル構成

```
scripts/
├── README.md              # このファイル
├── setup_oauth.py         # OAuth2 認証設定スクリプト
├── deploy_cloud_run.sh    # Cloud Run デプロイスクリプト
├── run.ps1                # 実行ラッパースクリプト（PowerShell）
└── setup_and_run.ps1      # セットアップ＆実行スクリプト（PowerShell）
```

## 分類

### 実行スクリプト
| ファイル | 説明 |
|---------|------|
| `run.ps1` | Windows 用の実行ラッパー（PowerShell） |

### 設定スクリプト
| ファイル | 説明 |
|---------|------|
| `setup_oauth.py` | Gmail API 用の OAuth2 認証を設定し、トークンを取得する |
| `setup_and_run.ps1` | 依存関係インストールから実行までを一括実行（Windows 用） |

### デプロイスクリプト
| ファイル | 説明 |
|---------|------|
| `deploy_cloud_run.sh` | GCP Cloud Run へのデプロイとインフラ設定を自動化 |

## 使用方法

### 基本的な実行（推奨）

```bash
# Python で直接実行（src/plugins/cli_prtimes_runner.py）
python -m src.plugins.cli_prtimes_runner

# または PowerShell（Windows）
.\scripts\run.ps1
```

### 設定ファイルの指定

```bash
# デフォルト設定（統合設定）
python -m src.plugins.cli_prtimes_runner

# 特定の設定ファイルを指定
python -m src.plugins.cli_prtimes_runner recipe/prtimes_gmail_config.yaml
python -m src.plugins.cli_prtimes_runner recipe/prtimes_local_smtp_config.yaml
```

### 初回セットアップ

```bash
# 1. 依存関係のインストール
cd src
pip install -r requirements.txt

# 2. OAuth2 認証の設定
python scripts/setup_oauth.py

# 3. セットアップ＆実行（Windows 用）
.\scripts\setup_and_run.ps1
```

### Cloud Run デプロイ

```bash
# GCP プロジェクト ID を指定して実行
./scripts/deploy_cloud_run.sh <PROJECT_ID>
```

## 環境変数設定

実行前に `config/envs/.env.local` の設定が必要です。

```bash
# 環境変数ファイル
config/envs/.env.local

# 必要な変数（OAuth2 使用時）
USE_OAUTH=true
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
OAUTH_REFRESH_TOKEN=your_refresh_token
OAUTH_ACCESS_TOKEN=your_access_token
GMAIL_USERNAME=your_email@gmail.com

# ローカル SMTP 使用時
USE_LOCAL_SMTP=true
```

## 関連ディレクトリ

| ディレクトリ | 説明 |
|------------|------|
| `recipe/` | パイプライン設定ファイル（YAML） |
| `config/` | 認証情報・環境設定 |
| `src/` | ソースコード・プラグイン |
| `src/plugins/` | CLI プラグイン（cli_prtimes_runner.py） |
| `data/` | 生成データ（RSS フィード・状態ファイル） |

## プラグインとしての実行

メイン実行ロジックは `src/plugins/cli_prtimes_runner.py` にあります。

```bash
# モジュールとして実行
python -m src.plugins.cli_prtimes_runner

# 直接実行
python src/plugins/cli_prtimes_runner.py