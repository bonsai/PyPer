# LINE ミニアプリ 設定ガイド - PR Times 発表会配信

## 設定済み情報

| 項目 | 値 |
|------|-----|
| **チャネル名** | `prt.happyoukai` |
| **LIFF アプリ名** | `prt.happyoukai` |
| **LIFF URL (Developing)** | `https://miniapp.line.me/2009667759-zoB76U1t` |
| **スコープ** | `openid`, `profile` |
| **サイズ** | `full` |

## 残りの設定手順

### ステップ 1: Endpoint URL を Cloud Run に変更

現在の Endpoint URL はダミーです。Cloud Run デプロイ後に更新します：

1. LINE Developers コンソール → 「Web app settings」
2. **Endpoint URL (Developing)** を編集：
   ```
   https://YOUR_PROJECT_ID.a.run.app/line
   ```
3. 「Save」をクリック

### ステップ 2: Cloud Run デプロイ

```bash
# GCP プロジェクト ID を設定
export PROJECT_ID="your-project-id"

# 環境変数を設定
echo -n "ec32181c90163d0940b1b78b127e5255" | gcloud secrets create LINE_CHANNEL_SECRET --data-file=- --project $PROJECT_ID

# デプロイ
./scripts/deploy_cloud_run.sh $PROJECT_ID
```

### ステップ 3: LIFF URL を更新

デプロイ後、再度 LINE Developers コンソールに戻って：

1. **Endpoint URL (Developing)** を実際の Cloud Run URL に変更：
   ```
   https://pypert-xxx.a.run.app/line
   ```

2. LIFF アプリを再度保存

### ステップ 4: 動作確認

1. LINE アプリで以下の URL を開く：
   ```
   https://miniapp.line.me/2009667759-zoB76U1t
   ```

2. LINE ログイン画面が表示されれば成功

## 環境変数一覧

Cloud Run に設定する必要があるシークレット：

```bash
# LINE 設定
LINE_CHANNEL_SECRET=ec32181c90163d0940b1b78b127e5255
LINE_CHANNEL_ACCESS_TOKEN=（Messaging API から取得）
LINE_LIFF_ID=liff_xxxxxxxxxx

# Gmail 設定（オプション）
GMAIL_CLIENT_ID=xxx
GMAIL_CLIENT_SECRET=xxx
GMAIL_REFRESH_TOKEN=xxx
GMAIL_USERNAME=xxx@gmail.com

# その他
PROJECT_ID=your-project-id
SECRET_KEY=（自動生成）
```

## Messaging API Bot の設定（オプション）

Bot からのコマンド操作を有効にする場合：

1. LINE Developers コンソールで「チャネルを追加」→「Bot」
2. Messaging API を有効化
3. アクセストークンを発行
4. Webhook URL を設定：
   ```
   https://YOUR_PROJECT_ID.a.run.app/api/line/webhook
   ```

## 公開フロー

1. **Developing** で動作確認
2. 「Review request」→ 審査申請
3. 審査通過後 **Published** に切り替え
4. LIFF URL も Published 用に変更：
   ```
   https://miniapp.line.me/2009667761-PVctueM5
   ```

## トラブルシューティング

### LIFF が起動しない

- Endpoint URL が正しいか確認
- CORS エラーが出ていないかブラウザの開発者ツールで確認

### ログインエラー

- スコープに `openid` と `profile` が含まれているか確認
- LIFF ID が正しいか確認

### 404 エラー

- Cloud Run がデプロイされているか確認：
  ```bash
  gcloud run services list --project YOUR_PROJECT_ID
  ```

## 次のステップ

1. GCP プロジェクト ID を教えてください
2. デプロイスクリプトを実行します
3. LIFF の Endpoint URL を更新します
4. 動作確認します
