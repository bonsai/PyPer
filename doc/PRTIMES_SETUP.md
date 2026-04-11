# PR Times プレスリリース→Gmail 送信セットアップガイド

このドキュメントでは、PR Times のプレスリリースを Gmail で受信するための設定手順を説明します。

## 概要

- PR Times から「発表会」キーワードの最新プレスリリースを取得
- Gmail でメール送信（OAuth2 対応）

## 必要なもの

1. Google アカウント（Gmail）
2. Google Cloud プロジェクト（OAuth2 設定用）

## セットアップ手順

### ステップ 1: 依存パッケージのインストール

```bash
pip install -r src/requirements.txt
```

### ステップ 2: 環境変数の設定

`config/envs/.env.local` ファイルを編集します。

#### 方法 A: OAuth2 認証（推奨）

1. Google Cloud Console で OAuth2 認証情報を取得
2. `.env.local` を以下のように編集：

```bash
# Gmail アドレス
GMAIL_USERNAME=your_email@gmail.com

# OAuth2 設定
USE_OAUTH=true
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
OAUTH_REFRESH_TOKEN=your_refresh_token
```

#### 方法 B: アプリパスワード（フォールバック）

OAuth2 設定が難しい場合は、Gmail のアプリパスワードを使用できます。

1. Google アカウントで 2 段階認証を有効化
2. アプリパスワードを生成：https://myaccount.google.com/apppasswords
3. `.env.local` を以下のように編集：

```bash
GMAIL_USERNAME=your_email@gmail.com
USE_OAUTH=false
GMAIL_PASSWORD=your_app_password
```

### ステップ 3: 設定ファイルの確認

`recipe/prtimes_config.yaml` を必要に応じて編集します。

- `limit`: 取得するプレスリリースの数（デフォルト：3）
- `to_addrs`: 送信先メールアドレス
- `subject_template`: メール件名のテンプレート
- `content_template`: メール本文のテンプレート

### ステップ 4: 実行

```bash
python scripts/run_prtimes.py
```

## OAuth2 設定の詳細

### Google Cloud Console での設定

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成または既存のプロジェクトを選択
3. 「API とサービス」→「ライブラリ」で「Gmail API」を有効化
4. 「API とサービス」→「認証情報」で OAuth クライアント ID を作成
5. アプリケーションの種類：「デスクトップアプリ」を選択
6. クライアント ID とクライアントシークレットをメモ

### 認証情報の取得

以下のスクリプトを使用して OAuth2 認証情報を取得できます：

```bash
python scripts/setup_oauth.py
```

このスクリプトは、ブラウザで認証を行い、`refresh_token` を取得します。

## 動作確認

スクリプトを実行すると、以下のような出力が表示されます：

```
.env.local を読み込みました：config/envs/.env.local
PR Times フローを開始します...
設定ファイル：recipe/prtimes_config.yaml

--- Starting Pipeline Execution ---
Fetching press releases from PR Times: https://prtimes.jp/...
 ✓ Fetched 1 new press release(s) from PR Times
Executing publishers with 1 workers...
 ✓ Authenticated via OAuth2
 ✓ Sent: 【タイトル】
Successfully sent 1 email(s).
--- Pipeline Execution Finished ---
```

## トラブルシューティング

### エラー：OAuth2 access token is required

- `OAUTH_REFRESH_TOKEN` が正しく設定されているか確認
- `scripts/setup_oauth.py` を再実行してトークンを更新

### エラー：Authentication failed

- Gmail アカウントで 2 段階認証が有効になっているか確認
- アプリパスワードを使用する場合は `USE_OAUTH=false` に設定

### エラー：No entries to send

- 既に取得済みのプレスリリースのみで新規がない場合
- `prtimes_state.txt` を削除して再実行

## 自動化（オプション）

cron やタスクスケジューラーを使用して定期的に実行できます。

### Windows タスクスケジューラー

```
python C:\path\to\PyPer\scripts\run_prtimes.py
```

### cron（Linux/Mac）

```bash
# 毎日 9 時に実行
0 9 * * * /usr/bin/python3 /path/to/PyPer/scripts/run_prtimes.py
```

## 設定ファイル例

### recipe/prtimes_config.yaml

```yaml
global:
  timezone: Asia/Tokyo
  log_level: info
  max_workers: 1

plugins:
  - module: Subscription::PRTimes
    config:
      url: https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word=%E7%99%BA%E8%A1%A8%E4%BC%9A
      limit: 3
      state_file: prtimes_state.txt

  - module: Publish::Gmail
    config:
      username: ${GMAIL_USERNAME}
      from_addr: ${GMAIL_USERNAME}
      to_addrs:
        - your_email@gmail.com
      use_oauth: ${USE_OAUTH:-true}
      oauth_client_id: ${OAUTH_CLIENT_ID}
      oauth_client_secret: ${OAUTH_CLIENT_SECRET}
      oauth_refresh_token: ${OAUTH_REFRESH_TOKEN}
      oauth_token_file: oauth_token.json
      subject_template: "【PR Times】{title}"