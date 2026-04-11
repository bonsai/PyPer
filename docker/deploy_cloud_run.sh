#!/bin/bash
# =============================================================================
# PyPer Cloud Run デプロイスクリプト
# =============================================================================
# 説明：
#   GCP Cloud Run へのデプロイとインフラ設定を自動化します
#
# 使用方法：
#   ./scripts/deploy_cloud_run.sh <PROJECT_ID>
#
# 例：
#   ./scripts/deploy_cloud_run.sh my-pypert-project
#
# 実行ステップ：
#   1. プロジェクトの作成/選択
#   2. 課金設定の確認
#   3. 必要な API の有効化
#   4. Firestore データベースの作成
#   5. OAuth 認証情報の設定
#   6. Gmail OAuth トークンの取得
#   7. シークレットの保存
#   8. Cloud Run へのデプロイ
#
# 必要なもの：
#   - GCP アカウント
#   - gcloud CLI のインストール
#   - OAuth 2.0 クライアント認証情報
# =============================================================================

set -e

echo "========================================"
echo "PyPer Cloud Run Setup"
echo "========================================"

# 設定
PROJECT_ID="${1:-}"
REGION="asia-northeast1"
SERVICE_NAME="pypert"

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 <PROJECT_ID>"
    echo "Example: $0 my-pypert-project"
    exit 1
fi

echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# -----------------------------------------------------------------------------
# ステップ 1: プロジェクトの作成/選択
# -----------------------------------------------------------------------------
echo "[1/8] Creating/selecting GCP project..."
gcloud projects create "$PROJECT_ID" 2>/dev/null || echo "Project already exists"
gcloud config set project "$PROJECT_ID"

# -----------------------------------------------------------------------------
# ステップ 2: 課金設定の確認
# -----------------------------------------------------------------------------
echo "[2/8] Checking billing..."
BILLING_ENABLED=$(gcloud beta billing projects describe "$PROJECT_ID" --format="value(billingEnabled)" 2>/dev/null || echo "false")
if [ "$BILLING_ENABLED" != "True" ]; then
    echo "⚠️  Billing not enabled. Please enable billing:"
    echo "   https://console.cloud.google.com/billing?project=$PROJECT_ID"
    read -p "Press Enter after enabling billing..."
fi

# -----------------------------------------------------------------------------
# ステップ 3: API の有効化
# -----------------------------------------------------------------------------
echo "[3/8] Enabling APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    scheduler.googleapis.com \
    firestore.googleapis.com \
    gmail.googleapis.com \
    secretmanager.googleapis.com \
    --project "$PROJECT_ID"

# -----------------------------------------------------------------------------
# ステップ 4: Firestore データベースの作成
# -----------------------------------------------------------------------------
echo "[4/8] Creating Firestore database..."
gcloud firestore databases create \
    --location=asia-northeast1 \
    --project "$PROJECT_ID" \
    --type=firestore-native 2>/dev/null || echo "Firestore already exists"

# -----------------------------------------------------------------------------
# ステップ 5: OAuth 認証情報の設定
# -----------------------------------------------------------------------------
echo "[5/8] OAuth Setup"
echo "⚠️  Please create OAuth credentials:"
echo "   1. Go to: https://console.cloud.google.com/apis/credentials"
echo "   2. Click 'Create Credentials' > 'OAuth client ID'"
echo "   3. Application type: Web application"
echo "   4. Authorized redirect URIs: https://accounts.google.com/o/oauth2/callback"
echo "   5. Copy Client ID and Client Secret"
echo ""
read -p "Enter OAuth Client ID: " CLIENT_ID
read -s -p "Enter OAuth Client Secret: " CLIENT_SECRET
echo ""

# -----------------------------------------------------------------------------
# ステップ 6: Gmail OAuth トークンの取得
# -----------------------------------------------------------------------------
echo "[6/8] Gmail OAuth Token Setup"
echo "Running OAuth setup..."
python3 scripts/setup_oauth.py || {
    echo "⚠️  OAuth setup failed. Please run manually:"
    echo "   python3 scripts/setup_oauth.py"
    read -p "Enter Gmail Username: " GMAIL_USERNAME
    read -s -p "Enter OAuth Refresh Token: " REFRESH_TOKEN
    echo ""
}

# -----------------------------------------------------------------------------
# ステップ 7: シークレットの保存
# -----------------------------------------------------------------------------
echo "[7/8] Storing secrets..."
echo -n "$CLIENT_SECRET" | gcloud secrets create GMAIL_CLIENT_SECRET --data-file=- --project "$PROJECT_ID" 2>/dev/null || \
    echo -n "$CLIENT_SECRET" | gcloud secrets versions add GMAIL_CLIENT_SECRET --data-file=- --project "$PROJECT_ID"
echo -n "$REFRESH_TOKEN" | gcloud secrets create GMAIL_REFRESH_TOKEN --data-file=- --project "$PROJECT_ID" 2>/dev/null || \
    echo -n "$REFRESH_TOKEN" | gcloud secrets versions add GMAIL_REFRESH_TOKEN --data-file=- --project "$PROJECT_ID"
echo -n "$GMAIL_USERNAME" | gcloud secrets create GMAIL_USERNAME --data-file=- --project "$PROJECT_ID" 2>/dev/null || \
    echo -n "$GMAIL_USERNAME" | gcloud secrets versions add GMAIL_USERNAME --data-file=- --project "$PROJECT_ID"
echo -n "$(openssl rand -hex 32)" | gcloud secrets create SECRET_KEY --data-file=- --project "$PROJECT_ID" 2>/dev/null || \
    echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add SECRET_KEY --data-file=- --project "$PROJECT_ID"

# Store client ID as environment variable (not secret)
export GMAIL_CLIENT_ID="$CLIENT_ID"

# -----------------------------------------------------------------------------
# ステップ 8: Cloud Run へのデプロイ
# -----------------------------------------------------------------------------
echo "[8/8] Deploying to Cloud Run..."
gcloud builds submit --tag "gcr.io/$PROJECT_ID/pypert" --project "$PROJECT_ID"

gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$PROJECT_ID/pypert" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --set-env-vars "PROJECT_ID=$PROJECT_ID,GMAIL_CLIENT_ID=$CLIENT_ID" \
    --set-secrets "GMAIL_CLIENT_SECRET=GMAIL_CLIENT_SECRET:latest,GMAIL_REFRESH_TOKEN=GMAIL_REFRESH_TOKEN:latest,GMAIL_USERNAME=GMAIL_USERNAME:latest,SECRET_KEY=SECRET_KEY:latest" \
    --project "$PROJECT_ID"

# サービス URL の取得
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --format='value(status.url)' \
    --project "$PROJECT_ID")

echo ""
echo "========================================"
echo "✅ Deployment Complete!"
echo "========================================"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "1. Create Cloud Scheduler job:"
echo "   gcloud scheduler jobs create http pypert-daily \\"
echo "     --schedule '0 0 * * *' \\"
echo "     --uri '$SERVICE_URL/api/send-daily' \\"
echo "     --http-method POST \\"
echo "     --oidc-service-account-email \"scheduler@${PROJECT_ID}.iam.gserviceaccount.com\" \\"
echo "     --oidc-token-audience '$SERVICE_URL'"
echo ""
echo "2. Visit your service: $SERVICE_URL"
echo ""