# PyPer - プレスリリース自動配信サービス

PR Times のプレスリリースを毎日自動で配信するサービスです。

## 🚀 3 分で開始（非技術者向け）

### 方法 1: LINE ミニアプリ（推奨）

**LINE 内で完結！一番簡単**

1. LINE アカウントでログイン
2. メールアドレス登録不要
3. ワンクリックで登録・解約

👉 **設定手順**: [LINE_SETUP.md](LINE_SETUP.md)

**LIFF URL**: `https://miniapp.line.me/2009667759-zoB76U1t` (Developing)

### 方法 2: Google Apps Script

**コピペするだけ！完全無料**

1. [script.google.com](https://script.google.com/) にアクセス
2. `gas/Code.gs` をコピーして貼り付け
3. トリガーを設定

👉 **詳細手順**: [SETUP_GUIDE.md](SETUP_GUIDE.md#方法-1-google-apps-script 推奨完全無料)

### 方法 3: Cloud Run（本格運用）

**複数ユーザー向け Web サービス**

- メールアドレス登録で配信開始
- ワンクリック解約
- 月 100 ユーザーまで無料

👉 **詳細**: [README_CLOUD.md](README_CLOUD.md)

---

## 特徴

- ✅ **完全無料** - 小規模なら費用ゼロ
- ✅ **毎日自動** - 朝 9 時に配信
- ✅ **ワンクリック解約** - ユーザーに優しい
- ✅ **OAuth 対応** - 安全な認証
- ✅ **重複防止** - 同じ記事は 2 回送らない

---

## 開発者向けクイックスタート

### ローカル実行

```bash
# 依存関係インストール
cd PyPer/src
pip install -r requirements.txt

# 環境変数設定
cd ..
copy config\envs\.env.example config\envs\.env.local
# .env.local を編集（Gmail 認証情報）

# OAuth トークン取得
python scripts\setup_oauth.py

# 実行
python scripts\run_prtimes.py
```

### Cloud Run デプロイ

```bash
# 一括セットアップ
./scripts/deploy_cloud_run.sh YOUR_PROJECT_ID
```

---

## ファイル構造

```
PyPer/
├── gas/                        # Google Apps Script 用
│   └── Code.gs
├── colab/                      # Google Colab 用
│   └── pypert_pipeline.ipynb
├── webapp/                     # Cloud Run 用 Web API
│   ├── main.py
│   └── requirements.txt
├── src/plugins/                # プラグイン
│   ├── subscription_prtimes.py
│   └── publish_gmail.py
├── recipe/                     # 設定ファイル
│   └── prt.yaml
├── scripts/
│   ├── run_prtimes.py
│   ├── setup_oauth.py
│   └── deploy_cloud_run.sh
└── SETUP_GUIDE.md              # 初心者向け設定ガイド
```

---

## ドキュメント

- 📘 [初心者向けセットアップガイド](SETUP_GUIDE.md)
- ☁️ [Cloud Run 本格運用ガイド](README_CLOUD.md)

---

## ライセンス

MIT
