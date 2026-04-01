# LINE ミニアプリ 設定ガイド

## 概要

PyPer を LINE ミニアプリとして動作させる設定です。ユーザーは LINE 内で簡単に登録・解約できます。

## 構成

```
LINE Mini App
├── フロントエンド (React + LIFF)
│   └── line-minigram/
├── バックエンド (Flask)
│   └── webapp/line_api.py
└── 配信方法
    ├── LINE Notify（個人向け）
    └── LINE Bot API（複数ユーザー向け）
```

## 設定手順

### ステップ 1: LINE Developers 登録

1. [LINE Developers コンソール](https://console.line.me/) にアクセス
2. 新規チャネル作成

### ステップ 2: LIFF チャネル作成

1. 「チャネルを追加」→「LIFF」を選択
2. 基本設定：
   - **LIFF アプリ名**: `PR Times 配信`
   - **LIFF アプリの URL**: `https://pypert-xxx.a.run.app`（Cloud Run URL）
   - **サイズ**: フル

3. LIFF ID を控える（`liff:xxxxxxxxxx`）

### ステップ 3: LINE Bot チャネル作成

1. 「チャネルを追加」→「Bot」を選択
2. 基本設定：
   - **Bot 名**: `PR Times 配信`
   - **説明**: 毎朝 9 時にプレスリリースをお届けします
   - **カテゴリ**: ニュス
   - **サブカテゴリ**: その他

3. 「Messaging API」設定：
   - **アクセストークン**を発行して控える
   - **チャネルシークレット**を控える
   - **Webhook URL**: `https://pypert-xxx.a.run.app/api/line/webhook`
   - Webhook を「利用する」に設定

### ステップ 4: LINE Notify 登録（オプション）

1. [LINE Notify サービス](https://notify-bot.line.me/ja/) にアクセス
2. 「マイページ」→「トークンを発行する」
3. トークン名：`PyPer Daily`
4. 発行したトークンを控える

### ステップ 5: 環境変数設定

Cloud Run に以下の環境変数を設定：

```bash
# LINE 設定
LINE_CHANNEL_SECRET=your_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_access_token
LINE_LIFF_ID=liff_xxxxxxxxxx

# Firestore（自動設定）
PROJECT_ID=your-project-id
```

### ステップ 6: シークレット設定

```bash
# LINE Channel Secret
echo -n "your_channel_secret" | gcloud secrets create LINE_CHANNEL_SECRET --data-file=-

# LINE Access Token
echo -n "your_access_token" | gcloud secrets create LINE_CHANNEL_ACCESS_TOKEN --data-file=-

# LIFF ID
echo -n "liff_xxxxxxxxxx" | gcloud secrets create LINE_LIFF_ID --data-file=-
```

### ステップ 7: デプロイ

```bash
# Cloud Build でデプロイ
gcloud builds submit --config cloudbuild.yaml
```

### ステップ 8: LIFF URL 設定

1. LINE Developers コンソールに戻る
2. LIFF アプリの編集
3. 「LIFF アプリの URL」にデプロイした URL を設定：
   ```
   https://pypert-xxx.a.run.app
   ```

### ステップ 9: 友達追加リンクを取得

1. LINE Developers コンソール
2. Bot チャネルの「基本設定」
3. 「友達追加リンク」をコピー

このリンクをユーザーに共有すると、Bot を追加できます。

## 使い方

### ユーザー登録フロー

1. ユーザーが LIFF アプリを開く
2. LINE ログインで認証
3. 「無料で登録する」ボタンをクリック
4. Firestore にユーザー情報が保存される

### 配信フロー

1. Cloud Scheduler が毎日 9 時に `/api/line/send-daily` を呼び出し
2. 購読中のユーザー一覧を取得
3. 各ユーザーに LINE Notify または Bot API で配信

### Bot からの操作

ユーザーが Bot にメッセージを送信：

- **「登録」**: 配信開始
- **「解除」**: 配信停止
- **「配信」**: 配信状態を確認

## 費用

| リソース | 無料枠 | 目安 |
|----------|--------|------|
| LIFF | 無制限 | 無料 |
| LINE Bot | 月 1,000 リプライ | 小規模なら無料 |
| LINE Notify | 月 1,000 通/トークン | 個人利用なら無料 |
| Cloud Run | 月 200 万リクエスト | 100 ユーザーまで無料 |

## カスタマイズ

### デザイン変更

`line-minigram/src/App.js` の `styles` オブジェクトを編集

### 配信時間変更

Cloud Scheduler のスケジュールを変更：

```bash
gcloud scheduler jobs update http pypert-daily \
  --schedule "0 9 * * *"  # 毎日 9 時（JST）
```

### 配信キーワード変更

`line_api.py` の `fetch_press_releases()` 関数内の URL を変更：

```python
url = 'https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word=%E6%A9%9F%E6%A2%B0%E5%AD%A6%E7%BF%92'
# 「機械学習」に変更
```

## トラブルシューティング

### LIFF が起動しない

- LIFF URL が正しいか確認
- CORS 設定を確認

### 配信されない

- Cloud Scheduler のログを確認
- LINE Notify トークンが有効か確認

### エラーが出る

- Cloud Run のログを確認：
  ```bash
  gcloud run logs read pypert --region asia-northeast1
  ```

## サポート

GitHub Issues: https://github.com/bonsai/PyPer/issues
