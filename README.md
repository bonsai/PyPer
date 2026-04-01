# PyPer - PR Times Press Release to Email

PR Times のプレスリリース（検索キーワード：発表会）を取得し、Gmail でメール送信する PyPer パイプラインです。

## 概要

このプロジェクトは、[PyPer](https://github.com/bonsai/PyPer) フレームワークをベースに、以下の機能を実装しています：

- **Subscription::PRTimes**: PR Times から「発表会」関連のプレスリリースを取得
- **Publish::Gmail**: 取得したプレスリリースを HTML メールで送信（OAuth2 対応）

## セットアップ

### 1. 依存関係のインストール

```bash
cd PyPer/src
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
cd PyPer
copy config\envs\.env.example config\envs\.env.local
```

### 3. Gmail OAuth2 認証設定（推奨）

**方法 A: セットアップスクリプトを使用（簡単）**

```bash
python scripts\setup_oauth.py
```

スクリプトの指示に従って認証を行ってください。

**方法 B: 手動設定**

1. **Google Cloud Console でプロジェクト作成**
   - https://console.cloud.google.com/ にアクセス
   - 新規プロジェクトを作成

2. **Gmail API を有効化**
   - 「API とサービス」>「ライブラリ」
   - 「Gmail API」を検索して有効化

3. **OAuth 同意画面を設定**
   - 「API とサービス」>「OAuth 同意画面」
   - 外部ユーザー向けに設定
   - 必要な情報を入力

4. **OAuth 2.0 クライアント ID を作成**
   - 「API とサービス」>「認証情報」
   - 「認証情報を作成」>「OAuth クライアント ID」
   - アプリケーションの種類：**デスクトップアプリ**
   - クライアント ID とクライアントシークレットを控える

5. **リフレッシュトークンを取得**

   以下の URL をブラウザで開く（`YOUR_CLIENT_ID` を置き換えて）:
   ```
   https://accounts.google.com/o/oauth2/auth?client_id=YOUR_CLIENT_ID&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://mail.google.com/&access_type=offline&prompt=consent
   ```

   認証後表示されるコードを控える

6. **`.env.local` を編集**

   ```env
   GMAIL_USERNAME=your_email@gmail.com
   USE_OAUTH=true
   OAUTH_CLIENT_ID=your_client_id
   OAUTH_CLIENT_SECRET=your_client_secret
   OAUTH_REFRESH_TOKEN=your_refresh_token
   ```

### 4. 実行

```powershell
# セットアップから実行まで一括
.\scripts\setup_and_run.ps1

# または、実行のみ
.\scripts\run.ps1

# または Python で直接
python scripts\run_prtimes.py
```

## 設定ファイル

### recipe/prtimes_config.yaml

パイプラインの設定ファイルです。以下を変更できます：

- `limit`: 取得するプレスリリースの数（デフォルト：10）
- `to_addrs`: 送信先メールアドレス
- `subject_template`: メール件名のテンプレート
- `content_template`: メール本文のテンプレート

## 仕組み

1. **Subscription::PRTimes** プラグインが PR Times の検索ページからプレスリリースを取得
2. 既に送信済みの URL は `prtimes_state.txt` で管理され、重複送信を防止
3. **Publish::Gmail** プラグインが HTML メールを生成し、Gmail SMTP で送信（OAuth2 認証）

## ファイル構造

```
PyPer/
├── config/
│   └── envs/
│       ├── .env.example      # 環境変数テンプレート
│       └── .env.local        # 環境変数（gitignore 対象）
├── recipe/
│   └── prtimes_config.yaml   # パイプライン設定
├── scripts/
│   ├── run_prtimes.py        # 実行スクリプト
│   └── setup_oauth.py        # OAuth セットアップスクリプト
├── src/
│   ├── main.py               # メイン実行ファイル
│   ├── requirements.txt      # 依存関係
│   └── plugins/
│       ├── __init__.py
│       ├── base.py           # プラグインベースクラス
│       ├── subscription_prtimes.py  # PR Times 取得プラグイン
│       └── publish_gmail.py         # Gmail 送信プラグイン（OAuth2 対応）
└── prtimes_state.txt         # 送信済み URL 管理（実行時に生成）
```

## 追加プラグインの作成

新しいプラグインを作成するには：

1. `src/plugins/` に新しい Python ファイルを作成
2. `SubscriptionPlugin`、`FilterPlugin`、`PublishPlugin` のいずれかを継承
3. `execute` メソッドを実装

例：`subscription_example.py`

```python
from .base import SubscriptionPlugin, Entry

class Plugin(SubscriptionPlugin):
    def execute(self):
        # データソースから Entry オブジェクトを生成して yield
        yield Entry(
            id="unique_id",
            source="example",
            content="content here",
            metadata={"title": "Example"}
        )
```

## 参考

- [PyPer 本体](https://github.com/bonsai/PyPer)
- [Plagger（元ネタ）](https://github.com/bonsai/plagger)
