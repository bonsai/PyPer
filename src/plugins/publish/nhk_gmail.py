# src/plugins/publish/nhk_gmail.py
"""NHK News向け Gmail 送信プラグイン"""

import logging
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Iterator, List
from ..base import Entry, PublishPlugin

logger = logging.getLogger(__name__)


class Plugin(PublishPlugin):
    """NHK NewsをHTMLメールでGmail送信"""

    @property
    def name(self) -> str:
        return "Publish::NHKGmail"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.to = config.get("to", "onsen.bonsai@gmail.com")
        self.from_addr = config.get("from", "onsen.bonsai@gmail.com")
        self.subject_template = config.get("subject_template", "📰 NHK News Top {count}")
        self.template = config.get("template", self._default_template())
        
        # SMTP設定
        self.smtp_server = config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username")
        self.password = config.get("password")
        # Empty string → None for proper OAuth fallback
        if self.password == "":
            self.password = None
        self.use_oauth = config.get("use_oauth", False)
        self.oauth_token_file = config.get("oauth_token_file")

    def _default_template(self) -> str:
        return """<html>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
    <h2 style="color:#1a73e8;border-bottom:2px solid #1a73e8;padding-bottom:10px;">
        📰 NHK News Top {count}
    </h2>
    <p style="color:#666;font-size:12px;">{date}</p>
    {entries}
    <hr style="border:none;border-top:1px solid #ddd;margin-top:30px;">
    <p style="color:#999;font-size:11px;text-align:center;">
        via PyPer/Plagger 🤖
    </p>
</body>
</html>"""

    def _render_entry(self, entry: Entry, index: int) -> str:
        title = entry.metadata.get("title", "No title")
        url = entry.metadata.get("url", "")
        summary = entry.metadata.get("summary", entry.content[:200])
        
        # LLM enrichがあれば使う
        x_summary = entry.metadata.get("x_summary", "")
        tags = entry.metadata.get("tags", [])
        sentiment = entry.metadata.get("sentiment", "")
        
        sentiment_emoji = {"positive": "😊", "neutral": "😐", "negative": "😢"}.get(sentiment, "")
        
        html = f"""<div style="margin:15px 0;padding:12px;border-left:4px solid #1a73e8;background:#f8f9fa;">
        <h3 style="margin:0 0 5px;">
            <a href="{url}" style="color:#1a73e8;text-decoration:none;">
                {index}. {title}
            </a> {sentiment_emoji}
        </h3>
        <p style="color:#666;font-size:13px;margin:5px 0;">{summary}</p>"""
        
        if x_summary:
            html += f"""<p style="color:#1a73e8;font-size:12px;margin:5px 0;">
            🐦 {x_summary}</p>"""
        
        if tags:
            html += f"""<p style="margin:5px 0;">{" ".join([f'<span style="background:#e3f2fd;padding:2px 6px;border-radius:3px;font-size:11px;color:#1565c0;">#{t}</span>' for t in tags[:3]])}</p>"""
        
        html += "</div>"
        return html

    def execute(self, entries: Iterator[Entry]):
        entries_list = list(entries)
        if not entries_list:
            logger.info("No entries to send")
            return

        count = len(entries_list)
        date = entries_list[0].metadata.get("published", "")
        
        # Render entries
        entries_html = "".join([
            self._render_entry(e, i+1) for i, e in enumerate(entries_list)
        ])
        
        # Build email
        html = self.template.format(
            count=count,
            date=date,
            entries=entries_html
        )
        
        subject = self.subject_template.format(count=count, date=date)
        
        msg = MIMEMultipart("alternative")
        msg["To"] = self.to
        msg["From"] = self.from_addr
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html", "utf-8"))
        
        # Send
        print(f"📤 Sending NHK News email to {self.to}...")
        
        # Always use Gmail API (more reliable than SMTP OAuth)
        self._send_via_gmail_api(msg)
        print(f"✅ Sent! Message: {subject}")
        logger.info(f"Email sent: {subject}")

    def _get_access_token(self) -> str:
        """OAuth2トークン取得（pickle形式）"""
        import pickle
        import os
        
        if self.oauth_token_file and os.path.exists(self.oauth_token_file):
            with open(self.oauth_token_file, 'rb') as f:
                creds = pickle.load(f)
                if hasattr(creds, 'token'):
                    return creds.token
                elif isinstance(creds, dict):
                    return creds.get('access_token', '')
        
        raise RuntimeError("No OAuth token available")

    def _send_via_gmail_api(self, msg):
        """Gmail API直接送信（OAuth使用）"""
        import pickle
        import os
        import requests
        import base64
        
        # トークン取得
        access_token = self._get_access_token()
        
        # メッセージエンコード
        raw = base64.urlsafe_b64encode(msg.as_string().encode()).decode()
        
        # API送信
        resp = requests.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers={'Authorization': f'Bearer {access_token}'},
            json={'raw': raw}
        )
        
        if resp.status_code == 200:
            msg_id = resp.json().get('id', 'unknown')
            print(f"✅ Sent via Gmail API! Message ID: {msg_id}")
        else:
            raise RuntimeError(f"Gmail API error: {resp.status_code} - {resp.text}")
