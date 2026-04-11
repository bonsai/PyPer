# PyPer 初心者向けセットアップガイド

非技術者向けに、3 分で設定できる方法を用意しています。

---

## 3 つの運用方法

### 方法 1: Google Apps Script（推奨・完全無料）
**おすすめ度：★★★★★**

- **費用**: 完全無料
- **設定時間**: 5 分
- **技術力**: 不要（コピペのみ）

**手順:**
1. [script.google.com](https://script.google.com/) にアクセス
2. 「新しいプロジェクト」をクリック
3. `gas/Code.gs` の内容をコピーして貼り付け
4. 「トリガー」→「トリガーを追加」→「時間主導」→「毎日」を選択
5. 初回実行で権限を許可

**メリット:**
- 完全無料（月 6 時間まで）
- サーバー不要
- Gmail と相性抜群

---

### 方法 2: Google Colab（お試し用）
**おすすめ度：★★★☆☆**

- **費用**: 無料
- **設定時間**: 3 分
- **技術力**: 不要

**手順:**
1. [colab.research.google.com](https://colab.research.google.com/) にアクセス
2. `colab/pypert_pipeline.ipynb` をアップロード
3. 各セルを実行

**注意:** ブラウザを開いたままにする必要があります

---

### 方法 3: Cloud Run（本格運用）
**おすすめ度：★★★★☆**

- **費用**: 月 100 円〜（ユーザー数による）
- **設定時間**: 15 分
- **技術力**: 少し必要

**向いている人:**
- 複数人に配信したい
- Web 画面で管理したい
- 自動で解約処理したい

**手順:**
```bash
# 1. セットアップスクリプトを実行
./scripts/deploy_cloud_run.sh YOUR_PROJECT_ID

# 2. 完了！Web 画面でユーザーが登録可能に
```

---

## 方法 1 の詳細手順（Google Apps Script）

### ステップ 1: スクリプトエディターを開く

1. [script.google.com](https://script.google.com/) にアクセス
2. 左上の「新しいプロジェクト」をクリック

### ステップ 2: コードを貼り付け

1. 表示されたエディターに `gas/Code.gs` の内容をコピー
2. 貼り付け

### ステップ 3: 設定を編集

```javascript
const SETTINGS = {
  EMAIL_RECIPIENT: 'your_email@gmail.com',  // ← あなたのメールアドレスに変更
  LIMIT: 3,  // 1 回に取得するプレスリリース数
};
```

### ステップ 4: 保存

1. 左上のフロッピーディスクアイコンをクリック
2. プロジェクト名を「PyPer」などに設定

### ステップ 5: トリガーを設定

1. 左メニューの「トリガー」をクリック（時計アイコン）
2. 「＋トリガーを追加」をクリック
3. 設定:
   - 実行する関数：`main`
   - デプロイ：`Head`
   - イベントソース：`時間主導`
   - 時間ベースタイマー：`日のタイマー` → `午前 9 時〜10 時`
4. 「保存」をクリック

### ステップ 6: 権限を許可

1. 初回実行時に権限画面が表示
2. 「アカウントを選択」
3. 「詳細設定」→「PyPer（安全ではないページ）へ移動」
4. 「許可」をクリック

### 完了！

翌朝 9 時から毎日自動でメールが送られます。

---

## よくある質問

### Q. 配信を止めたい
**A.** Google Apps Script のトリガーを削除してください。

### Q. 複数のメールアドレスに送りたい
**A.** `SETTINGS.EMAIL_RECIPIENT` を配列に変更するか、Cloud Run を使用してください。

### Q. 取得するキーワードを変えたい
**A.** `SETTINGS.PR_TIMES_URL` の `search_word` パラメータを変更してください。
   - 例：「AI」→ `%E6%9C%BA%E6%A2%B0%E5%AD%A6%E7%BF%92`

### Q. エラーが出る
**A.** 以下の原因が考えられます：
- 権限が許可されていない → 再許可
- ネットワークエラー → 再実行
- 取得件数 0 → 検索キーワードを変更

---

## Cloud Run の場合（複数ユーザー向け）

### 完全手順

```bash
# 0. 事前準備
# - Google Cloud アカウント作成
# - gcloud CLI インストール

# 1. プロジェクト作成
export PROJECT_ID="pypert-YOUR_NAME"
gcloud projects create $PROJECT_ID

# 2. 課金設定（手動）
# https://console.cloud.google.com/billing?project=$PROJECT_ID

# 3. API 有効化
gcloud services enable cloudbuild.googleapis.com run.googleapis.com \
  scheduler.googleapis.com firestore.googleapis.com gmail.googleapis.com \
  secretmanager.googleapis.com --project $PROJECT_ID

# 4. OAuth 設定（手動）
# https://console.cloud.google.com/apis/credentials
# - OAuth クライアント ID 作成（Web アプリケーション）
# - リダイレクト URI: https://accounts.google.com/o/oauth2/callback

# 5. OAuth トークン取得
python scripts/setup_oauth.py

# 6. デプロイ
./scripts/deploy_cloud_run.sh $PROJECT_ID

# 7. Cloud Scheduler 設定
SERVICE_URL=$(gcloud run services describe pypert --platform managed \
  --region asia-northeast1 --format='value(status.url)')

gcloud scheduler jobs create http pypert-daily \
  --schedule "0 0 * * *" \
  --uri "$SERVICE_URL/api/send-daily" \
  --http-method POST \
  --oidc-service-account-email "scheduler@${PROJECT_ID}.iam.gserviceaccount.com" \
  --oidc-token-audience "$SERVICE_URL"
```

### 費用内訳

| リソース | 無料枠 | 100 ユーザー/月 |
|----------|--------|-----------------|
| Cloud Run | 200 万リクエスト | $0 |
| Firestore | 1GB/月 | $0 |
| Cloud Scheduler | 3 ジョブ | $0 |
| Gmail API | 20 億リクエスト/日 | $0 |
| **合計** | | **$0** |

※ 100 ユーザーまで完全無料の可能性が高いです

---

## サポート

問題が発生した場合は GitHub Issues で質問してください：
https://github.com/bonsai/PyPer/issues
