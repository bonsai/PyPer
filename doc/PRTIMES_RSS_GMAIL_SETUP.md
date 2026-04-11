# PR Times マイページ → RSS 生成 → Gmail 送信セットアップガイド

## 概要

PR Times のマイページから最新プレスリリースをスクレイピングし、RSS フィードを生成して Gmail で送信するパイプラインです。

## 機能

1. **PRTIMES マイページ取得**: ログイン後のマイページからプレスリリースを取得
2. **RSS 生成**: 取得したプレスリリースを RSS 2.0 形式で出力
3. **Gmail 送信**: OAuth2 またはアプリパスワードで認証し、HTML メールを送信

## セットアップ手順

### 1. 環境変数の設定

```bash
# config/envs/.env.local を作成
cp config/envs/.env.local.example config/envs/.env.local
```

`.env.local` を編集して以下の設定を入力：

```bash
GMAIL_USERNAME=your-email@gmail.com
USE_OAUTH=true
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret
OAUTH_REFRESH_TOKEN=your-refresh-token
OAUTH_ACCESS_TOKEN=your-access-token
RSS_URL=https://your-domain.com/prtimes_mypage_feed.xml
```

### 2. 依存関係のインストール

```bash
pip install -r src/requirements.txt
```

### 3. 実行方法

```bash
python scripts/run_prtimes.py
```

または、設定ファイルを指定して実行：

```bash
python scripts/run_prtimes.py recipe/prtimes_config.yaml
```

## 出力ファイル

- `prtimes_state.txt`: 既に送信した URL の記録（重複防止）
- `prtimes_mypage_feed.xml`: 生成された RSS フィード

## 設定カスタマイズ

`recipe/prtimes_config.yaml` を編集して以下を変更できます：

- `url`: 取得する PRTIMES の URL
- `limit`: 1 回に取得するプレスリリース数
- `rss_title`: RSS フィードのタイトル
- `rss_file`: 出力する RSS ファイル名
- `to_addrs`: 送信先メールアドレス
- `subject_template`: メール件名のテンプレート
- `content_template`: メール本文の HTML テンプレート

## 注意事項

- PRTIMES のマイページにアクセスするには、事前に PRTIMES でアカウント登録とログインが必要です
- 初回実行時は状態ファイル（`prtimes_state.txt`）が存在しないため、全てのプレスリリースが新規として扱われます
- 2 回目以降は、前回の送信済み URL を記録しているため、新しいプレスリリースのみ送信されます