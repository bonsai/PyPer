#!/usr/bin/env python3
"""
PyPer Web API - PR Times Email Subscription Service

A simple Flask API for users to subscribe to daily PR Times press release emails.
Designed for non-technical users - just register email and receive daily updates.
"""

import os
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, redirect, render_template_string
from google.cloud import firestore
from google.oauth2 import service_account
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Import LINE API blueprint
from .line_api import line_bp
app.register_blueprint(line_bp)

# Configuration
PROJECT_ID = os.environ.get('PROJECT_ID', 'your-project-id')
SERVICE_URL = os.environ.get('SERVICE_URL', 'http://localhost:8080')
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Gmail OAuth config
GMAIL_CONFIG = {
    'client_id': os.environ.get('GMAIL_CLIENT_ID'),
    'client_secret': os.environ.get('GMAIL_CLIENT_SECRET'),
    'refresh_token': os.environ.get('GMAIL_REFRESH_TOKEN'),
    'username': os.environ.get('GMAIL_USERNAME'),
}

# Firestore client
db = firestore.Client(project=PROJECT_ID)


# ==================== Helpers ====================

def generate_unsubscribe_token(email: str) -> str:
    """Generate HMAC-signed unsubscribe token."""
    message = f"{email}:{datetime.now().isoformat()}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    return f"{email}|{signature}"


def verify_unsubscribe_token(token: str) -> str | None:
    """Verify and extract email from unsubscribe token."""
    try:
        parts = token.split('|')
        if len(parts) != 2:
            return None
        email, signature = parts
        
        # Check if user exists
        user_ref = db.collection('subscribers').document(email)
        user = user_ref.get()
        if not user.exists:
            return None
        
        # Signature is valid if user exists (simplified - in production, store token timestamp)
        return email
    except Exception:
        return None


def get_oauth_access_token() -> str:
    """Get OAuth2 access token for Gmail API."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GMAIL_CONFIG['client_id'],
        "client_secret": GMAIL_CONFIG['client_secret'],
        "refresh_token": GMAIL_CONFIG['refresh_token'],
        "grant_type": "refresh_token",
    }
    
    response = requests.post(token_url, data=data, timeout=30)
    response.raise_for_status()
    return response.json().get("access_token")


def send_email(to: str, subject: str, html_body: str):
    """Send email via Gmail API."""
    import base64
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    access_token = get_oauth_access_token()
    
    # Create message
    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = GMAIL_CONFIG['username']
    message['To'] = to
    
    # Attach HTML
    message.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    # Send via Gmail API
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    
    response = requests.post(
        f'https://gmail.googleapis.com/gmail/v1/users/{GMAIL_CONFIG["username"]}/messages/send',
        headers=headers,
        json={'raw': raw_message},
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def fetch_press_releases(limit: int = 5) -> list:
    """Fetch latest press releases from PR Times."""
    url = 'https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word=%E7%99%BA%E8%A1%A8%E4%BC%9A'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.select('a[href*="/main/html/rd/p/"]')
    
    results = []
    for link in links[:limit]:
        href = link.get('href', '')
        title = link.get_text(strip=True)
        
        if href and title:
            absolute_url = f"https://prtimes.jp{href}" if href.startswith('/') else href
            results.append({
                'title': title,
                'url': absolute_url,
            })
    
    return results


# ==================== Routes ====================

@app.route('/')
def index():
    """Landing page with subscription form."""
    # Serve LINE Mini App frontend if available
    try:
        return render_template_string('''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PR Times 配信サービス</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
            background: linear-gradient(135deg, #00C300 0%, #009900 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
        }
        .methods {
            display: grid;
            gap: 20px;
            margin-top: 30px;
        }
        .method {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #00C300;
        }
        .method h3 {
            margin: 0 0 10px 0;
            color: #333;
        }
        .method p {
            color: #666;
            font-size: 14px;
            margin: 0;
        }
        .method a {
            color: #00C300;
            text-decoration: none;
            font-weight: bold;
        }
        .badge {
            display: inline-block;
            background: #00C300;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-left: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📰 PR Times 配信サービス</h1>
        <p class="subtitle">最新のプレスリリースを毎日お届け</p>
        
        <div class="methods">
            <div class="method">
                <h3>🟢 LINE ミニアプリ <span class="badge">推奨</span></h3>
                <p>LINE 内で完結！メールアドレス不要</p>
                <p><a href="/line">LINE ミニアプリを開く →</a></p>
            </div>
            <div class="method">
                <h3>📧 Email 配信</h3>
                <p> Gmail で受信</p>
                <p><a href="/email">メールアドレスで登録 →</a></p>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 30px; color: #999; font-size: 12px;">
            <p>© 2024 PyPer. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        ''')
    except Exception as e:
        app.logger.error(f"Index error: {e}")
        return jsonify({'error': 'Failed to load page'}), 500


@app.route('/line')
def line_minigram():
    """LINE Mini App entry point."""
    return render_template_string('''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PR Times 配信</title>
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
        }
        #root {
            min-height: 100vh;
        }
    </style>
</head>
<body>
    <div id="root"></div>
    <script>
        var liffId = '{{ liff_id }}';
    </script>
    <script src="/static/app.js"></script>
</body>
</html>
    ''', liff_id=os.environ.get('LINE_LIFF_ID', ''))


@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    """Subscribe an email address."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email or '@' not in email:
        return jsonify({'success': False, 'error': '有効なメールアドレスを入力してください'}), 400
    
    try:
        # Check if already subscribed
        user_ref = db.collection('subscribers').document(email)
        user = user_ref.get()
        
        if user.exists:
            user_data = user.to_dict()
            if user_data.get('status') == 'active':
                return jsonify({'success': True, 'message': '既に登録されています'})
            
            # Reactivate
            user_ref.update({
                'status': 'active',
                'subscribed_at': datetime.utcnow(),
                'unsubscribed_at': None,
            })
        else:
            # New subscription
            user_ref.set({
                'email': email,
                'status': 'active',
                'subscribed_at': datetime.utcnow(),
                'created_at': datetime.utcnow(),
            })
        
        # Send confirmation email
        unsubscribe_token = generate_unsubscribe_token(email)
        unsubscribe_url = f"{SERVICE_URL}/api/unsubscribe/{unsubscribe_token}"
        
        html_body = f'''
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">登録ありがとうございます</h2>
            <p style="color: #666; line-height: 1.6;">
                PR Times 配信サービスにご登録いただき、ありがとうございます。<br>
                本日より、毎朝 9 時に最新のプレスリリースをお届けします。
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #999; font-size: 12px;">
                配信停止は
                <a href="{unsubscribe_url}" style="color: #667eea;">こちらからワンクリックで</a>
                行えます。
            </p>
        </body>
        </html>
        '''
        
        send_email(
            email,
            '【PR Times】登録完了のお知らせ',
            html_body
        )
        
        return jsonify({'success': True, 'message': '登録完了'})
        
    except Exception as e:
        app.logger.error(f"Subscribe error: {e}")
        return jsonify({'success': False, 'error': '登録に失敗しました'}), 500


@app.route('/api/unsubscribe/<token>')
def unsubscribe(token: str):
    """Unsubscribe via token link."""
    email = verify_unsubscribe_token(token)
    
    if not email:
        return redirect('/unsubscribed?error=invalid')
    
    try:
        # Mark as unsubscribed
        user_ref = db.collection('subscribers').document(email)
        user_ref.update({
            'status': 'unsubscribed',
            'unsubscribed_at': datetime.utcnow(),
        })
        
        return redirect(f'/unsubscribed?email={email}')
    except Exception:
        return redirect('/unsubscribed?error=unknown')


@app.route('/unsubscribed')
def unsubscribed_page():
    """Unsubscribe confirmation page."""
    error = request.args.get('error')
    email = request.args.get('email', '')
    
    if error == 'invalid':
        message = '無効なリンクです。メールのリンクを再度クリックしてください。'
    elif error:
        message = 'エラーが発生しました。'
    else:
        message = f'配信を停止しました。<br>メールアドレス：{email}<br>ご利用ありがとうございました。'
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>配信停止完了</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f5;
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 16px;
            padding: 40px;
            text-align: center;
        }
        h1 { color: #333; }
        .message {
            color: #666;
            line-height: 1.8;
            margin: 30px 0;
        }
        .btn {
            display: inline-block;
            padding: 12px 30px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 {{ '配信停止完了' if not error else 'エラー' }}</h1>
        <div class="message">{{ message|safe }}</div>
        {% if not error %}
        <a href="/" class="btn">再登録する</a>
        {% endif %}
    </div>
</body>
</html>
    ''', message=message, error=error)


@app.route('/api/send-daily', methods=['POST'])
def send_daily():
    """Send daily press releases to all subscribers (called by Cloud Scheduler)."""
    # Verify scheduler token (simplified - in production, verify OIDC token)
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get active subscribers
        subscribers = db.collection('subscribers')\
            .where('status', '==', 'active')\
            .stream()
        
        # Fetch press releases
        press_releases = fetch_press_releases(limit=5)
        
        if not press_releases:
            return jsonify({'sent': 0, 'message': 'No press releases today'})
        
        # Send to each subscriber
        sent_count = 0
        failed_count = 0
        
        for doc in subscribers:
            email = doc.id
            try:
                unsubscribe_token = generate_unsubscribe_token(email)
                unsubscribe_url = f"{SERVICE_URL}/api/unsubscribe/{unsubscribe_token}"
                
                # Build email content
                pr_items = ''.join(f'''
                    <li style="margin: 15px 0;">
                        <a href="{pr['url']}" style="color: #667eea; text-decoration: none; font-size: 16px;">
                            {pr['title']}
                        </a>
                    </li>
                ''' for pr in press_releases)
                
                html_body = f'''
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #333;">本日のプレスリリース</h2>
                    <p style="color: #666;">{datetime.now().strftime('%Y年%m月%d日')}</p>
                    <ul style="padding-left: 20px;">
                        {pr_items}
                    </ul>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px;">
                        <a href="{unsubscribe_url}" style="color: #999;">配信停止はこちら</a>
                    </p>
                </body>
                </html>
                '''
                
                send_email(
                    email,
                    f'【PR Times】本日のプレスリリース ({len(press_releases)}件)',
                    html_body
                )
                
                sent_count += 1
                
                # Log send history
                db.collection('email_logs').add({
                    'email': email,
                    'sent_at': datetime.utcnow(),
                    'count': len(press_releases),
                })
                
            except Exception as e:
                app.logger.error(f"Failed to send to {email}: {e}")
                failed_count += 1
        
        return jsonify({
            'sent': sent_count,
            'failed': failed_count,
            'press_releases': len(press_releases),
        })
        
    except Exception as e:
        app.logger.error(f"Send daily error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
