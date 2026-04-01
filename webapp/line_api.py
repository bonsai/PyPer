# LINE Mini App Backend API

from flask import Blueprint, request, jsonify, current_app
from google.cloud import firestore
from datetime import datetime
import hashlib
import hmac
import os
import requests

line_bp = Blueprint('line', __name__)

# Firestore client
db = firestore.Client()

# LINE Bot configuration
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')


def verify_line_signature(signature: str, body: str) -> bool:
    """Verify LINE webhook signature."""
    if not LINE_CHANNEL_SECRET:
        return True  # Skip verification in development
    
    hash_bytes = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    calculated_signature = 'SHA256=' + hash_bytes.hex()
    
    return hmac.compare_digest(signature, calculated_signature)


@line_bp.route('/api/line/check-subscription', methods=['POST'])
def check_subscription():
    """Check if user is subscribed."""
    data = request.get_json()
    user_id = data.get('userId')
    
    if not user_id:
        return jsonify({'error': 'userId is required'}), 400
    
    try:
        user_ref = db.collection('line_subscribers').document(user_id)
        user = user_ref.get()
        
        if user.exists:
            user_data = user.to_dict()
            subscribed = user_data.get('status') == 'active'
            return jsonify({'subscribed': subscribed})
        else:
            return jsonify({'subscribed': False})
            
    except Exception as e:
        current_app.logger.error(f"Check subscription error: {e}")
        return jsonify({'error': 'Failed to check subscription'}), 500


@line_bp.route('/api/line/subscribe', methods=['POST'])
def subscribe():
    """Subscribe a LINE user."""
    data = request.get_json()
    user_id = data.get('userId')
    display_name = data.get('displayName', '')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'userId is required'}), 400
    
    try:
        user_ref = db.collection('line_subscribers').document(user_id)
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
                'display_name': display_name,
            })
        else:
            # New subscription
            user_ref.set({
                'user_id': user_id,
                'display_name': display_name,
                'status': 'active',
                'subscribed_at': datetime.utcnow(),
                'created_at': datetime.utcnow(),
            })
        
        return jsonify({'success': True, 'message': '登録完了！'})
        
    except Exception as e:
        current_app.logger.error(f"Subscribe error: {e}")
        return jsonify({'success': False, 'error': '登録に失敗しました'}), 500


@line_bp.route('/api/line/unsubscribe', methods=['POST'])
def unsubscribe():
    """Unsubscribe a LINE user."""
    data = request.get_json()
    user_id = data.get('userId')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'userId is required'}), 400
    
    try:
        user_ref = db.collection('line_subscribers').document(user_id)
        user_ref.update({
            'status': 'unsubscribed',
            'unsubscribed_at': datetime.utcnow(),
        })
        
        return jsonify({'success': True, 'message': '配信を停止しました'})
        
    except Exception as e:
        current_app.logger.error(f"Unsubscribe error: {e}")
        return jsonify({'success': False, 'error': '解除に失敗しました'}), 500


@line_bp.route('/api/line/send-daily', methods=['POST'])
def send_daily_line():
    """Send daily press releases to LINE subscribers."""
    try:
        # Get active subscribers
        subscribers = db.collection('line_subscribers')\
            .where('status', '==', 'active')\
            .stream()
        
        # Fetch press releases
        press_releases = fetch_press_releases(limit=5)
        
        if not press_releases:
            return jsonify({'sent': 0, 'message': 'No press releases today'})
        
        # Send to each subscriber via LINE Notify
        # Note: In production, you would use LINE Bot API to push messages
        # This is a simplified version using LINE Notify tokens stored per user
        
        sent_count = 0
        failed_count = 0
        
        for doc in subscribers:
            user_data = doc.to_dict()
            user_id = user_data.get('user_id')
            notify_token = user_data.get('line_notify_token')
            
            if not notify_token:
                continue
            
            try:
                # Send via LINE Notify
                for pr in press_releases:
                    send_line_notify(notify_token, pr)
                
                sent_count += 1
                
                # Log send history
                db.collection('line_email_logs').add({
                    'user_id': user_id,
                    'sent_at': datetime.utcnow(),
                    'count': len(press_releases),
                })
                
            except Exception as e:
                current_app.logger.error(f"Failed to send to {user_id}: {e}")
                failed_count += 1
        
        return jsonify({
            'sent': sent_count,
            'failed': failed_count,
            'press_releases': len(press_releases),
        })
        
    except Exception as e:
        current_app.logger.error(f"Send daily LINE error: {e}")
        return jsonify({'error': str(e)}), 500


@line_bp.route('/api/line/webhook', methods=['POST'])
def line_webhook():
    """LINE Bot webhook endpoint."""
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    if not verify_line_signature(signature, body):
        return jsonify({'error': 'Invalid signature'}), 400
    
    try:
        events = request.get_json().get('events', [])
        
        for event in events:
            if event['type'] == 'message' and event['message']['type'] == 'text':
                handle_text_message(event)
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        current_app.logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500


def handle_text_message(event):
    """Handle text messages from users."""
    user_id = event['source']['userId']
    message_text = event['message']['text']
    
    if message_text == '登録':
        # Subscribe user
        db.collection('line_subscribers').document(user_id).set({
            'user_id': user_id,
            'status': 'active',
            'subscribed_at': datetime.utcnow(),
            'created_at': datetime.utcnow(),
        }, merge=True)
        
        reply_message(event['replyToken'], '登録完了しました！毎朝 9 時にプレスリリースをお届けします。')
        
    elif message_text == '解除':
        # Unsubscribe user
        db.collection('line_subscribers').document(user_id).update({
            'status': 'unsubscribed',
            'unsubscribed_at': datetime.utcnow(),
        })
        
        reply_message(event['replyToken'], '配信を停止しました。')
        
    elif message_text == '配信':
        # Check status
        user_ref = db.collection('line_subscribers').document(user_id)
        user = user_ref.get()
        
        if user.exists and user.to_dict().get('status') == 'active':
            reply_message(event['replyToken'], '現在配信中です。「解除」と送信すると停止します。')
        else:
            reply_message(event['replyToken'], '配信停止中です。「登録」と送信すると開始します。')


def reply_message(reply_token: str, message: str):
    """Reply to user message."""
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}',
    }
    
    data = {
        'replyToken': reply_token,
        'messages': [{
            'type': 'text',
            'text': message,
        }]
    }
    
    requests.post(url, headers=headers, json=data, timeout=30)


def send_line_notify(token: str, press_release: dict):
    """Send press release via LINE Notify."""
    url = 'https://notify-api.line.me/api/notify'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    message = f"📰 {press_release['title']}\n{press_release['url']}"
    
    data = {
        'message': message,
        'url': press_release['url'],
    }
    
    response = requests.post(url, headers=headers, data=data, timeout=30)
    response.raise_for_status()


def fetch_press_releases(limit: int = 5) -> list:
    """Fetch latest press releases from PR Times."""
    url = 'https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word=%E7%99%BA%E8%A1%A8%E4%BC%9A'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    from bs4 import BeautifulSoup
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
