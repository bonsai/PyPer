# PyPer Web API - PR Times Email Subscription Service

A simple web API service for non-technical users to subscribe to daily PR Times press release emails.

## Features

- **Email Registration**: Users can subscribe with just their email address
- **Daily Delivery**: One email per day with latest press releases
- **One-Click Unsubscribe**: Easy cancellation via email link
- **Cloud Run**: Deploy on Google Cloud Run (cheapest tier - free for low usage)

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   User      │────▶│  Cloud Run   │────▶│  Firestore  │
│  Browser    │     │  (Flask API) │     │  (Database) │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Cloud       │
                    │  Scheduler   │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Gmail API   │
                    │  (Send Email)│
                    └──────────────┘
```

## Quick Start

### 1. Setup Google Cloud Project

```bash
# Create project
gcloud projects create YOUR_PROJECT_ID

# Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com \
  scheduler.googleapis.com firestore.googleapis.com gmail.googleapis.com

# Create Firestore database (in production mode)
gcloud firestore databases create --location=asia-northeast1 --project=YOUR_PROJECT_ID
```

### 2. Configure OAuth for Gmail

```bash
# Create OAuth credentials
# https://console.cloud.google.com/apis/credentials
# Application type: Web application
# Authorized redirect URIs: https://accounts.google.com/o/oauth2/callback
```

### 3. Deploy to Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/pypert
gcloud run deploy pypert \
  --image gcr.io/YOUR_PROJECT_ID/pypert \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

### 4. Setup Cloud Scheduler

```bash
# Create service account
gcloud iam service-accounts create pypert-scheduler \
  --display-name "PyPer Scheduler"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:pypert-scheduler@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Create scheduled job (daily at 9 AM JST)
gcloud scheduler jobs create http pypert-daily \
  --schedule "0 0 * * *" \
  --uri "https://pypert-xxx.a.run.app/api/send-daily" \
  --http-method POST \
  --oidc-service-account-email "pypert-scheduler@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --oidc-token-audience "https://pypert-xxx.a.run.app"
```

## API Endpoints

### Subscribe
```
POST /api/subscribe
Content-Type: application/json

{"email": "user@example.com"}

Response: {"success": true, "message": "Subscription confirmed"}
```

### Unsubscribe
```
GET /api/unsubscribe/{token}

Response: Redirect to success page
```

### Send Daily Emails (internal)
```
POST /api/send-daily
Authorization: Bearer <scheduler token>

Response: {"sent": 5, "failed": 0}
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GMAIL_CLIENT_ID` | OAuth Client ID |
| `GMAIL_CLIENT_SECRET` | OAuth Client Secret |
| `GMAIL_REFRESH_TOKEN` | OAuth Refresh Token |
| `GMAIL_USERNAME` | Gmail address |
| `PROJECT_ID` | GCP Project ID |
| `SERVICE_URL` | Cloud Run service URL |

## Pricing (Cloud Run)

- **Free tier**: 2 million requests/month
- **Typical usage**: ~100 subscribers = ~3000 requests/month (FREE)
- **Cost estimate**: $0-5/month for small scale

## Security

- Unsubscribe tokens are HMAC-signed (cannot be forged)
- CORS enabled for web frontend
- Rate limiting on subscription endpoint
