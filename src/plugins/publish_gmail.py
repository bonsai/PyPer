# src/plugins/publish_gmail.py
import smtplib
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Iterator, List, Optional
from base import Entry, PublishPlugin

logger = logging.getLogger(__name__)


def get_oauth2_string(email: str, access_token: str) -> str:
    """
    Generate OAuth2 string for SMTP AUTH.
    Format: user={user}\1auth=Bearer {token}\1\1
    """
    auth_string = f"user={email}\1auth=Bearer {access_token}\1\1"
    return base64.b64encode(auth_string.encode()).decode()


class Plugin(PublishPlugin):
    """
    A publish plugin to send entries as email via Gmail SMTP.
    Supports both OAuth2 and app password authentication.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.username = self.config.get("username")
        self.password = self.config.get("password")  # App password (fallback)
        self.from_addr = self.config.get("from_addr", self.username)
        self.to_addrs = self.config.get("to_addrs", [])
        self.subject_template = self.config.get("subject_template", "PR Times: {title}")
        self.content_template = self.config.get("content_template", """
<html>
<body>
<h1>{title}</h1>
<p>{content}</p>
<p><a href="{url}">元記事を読む</a></p>
</body>
</html>
""")
        
        # OAuth2 settings
        self.use_oauth = self.config.get("use_oauth", False)
        self.access_token = self.config.get("oauth_access_token")
        self.client_id = self.config.get("oauth_client_id")
        self.client_secret = self.config.get("oauth_client_secret")
        self.refresh_token = self.config.get("oauth_refresh_token")
        self.token_file = self.config.get("oauth_token_file", "oauth_token.json")
        
        if isinstance(self.to_addrs, str):
            self.to_addrs = [self.to_addrs]
    
    def _refresh_access_token(self) -> Optional[str]:
        """
        Refresh the OAuth2 access token using the refresh token.
        """
        import requests
        
        if not self.refresh_token or not self.client_id or not self.client_secret:
            logger.error("Missing OAuth credentials for token refresh")
            return None
        
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            new_access_token = token_data.get("access_token")
            
            if new_access_token:
                logger.info("Access token refreshed successfully")
                # Save new token to file
                self._save_token(new_access_token)
                return new_access_token
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
        
        return None
    
    def _save_token(self, access_token: str):
        """Save access token to file for caching."""
        import json
        try:
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump({"access_token": access_token}, f)
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
    
    def _load_cached_token(self) -> Optional[str]:
        """Load cached access token from file."""
        import json
        import os
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    token_data = json.load(f)
                    return token_data.get("access_token")
            except Exception as e:
                logger.error(f"Failed to load cached token: {e}")
        return None
    
    def _get_valid_access_token(self) -> Optional[str]:
        """
        Get a valid access token using the following priority:
        1. Cached token
        2. Refresh token
        3. Directly provided token
        """
        # Try cached token first
        cached_token = self._load_cached_token()
        if cached_token:
            logger.info("Using cached access token")
            return cached_token
        
        # Try provided token
        if self.access_token:
            logger.info("Using provided access token")
            return self.access_token
        
        # Try refreshing with refresh token
        if self.refresh_token:
            refreshed_token = self._refresh_access_token()
            if refreshed_token:
                return refreshed_token
        
        logger.error("No valid access token available")
        return None
    
    def execute(self, entries: Iterator[Entry]):
        """
        Receives Entry objects and sends them as emails.
        """
        entries_list = list(entries)
        
        if not entries_list:
            logger.info("No entries to send.")
            return
        
        print(f"Sending {len(entries_list)} press release(s) via Gmail...")
        
        try:
            # SMTP 接続
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.ehlo()
            server.starttls()
            server.ehlo()
            
            # 認証
            if self.use_oauth:
                access_token = self._get_valid_access_token()
                if not access_token:
                    raise RuntimeError("OAuth2 access token is required for OAuth authentication")
                
                auth_string = get_oauth2_string(self.username, access_token)
                server.docmd("AUTH", "XOAUTH2 " + auth_string)
                print(" ✓ Authenticated via OAuth2")
            else:
                # Fallback to app password
                if not self.password:
                    raise RuntimeError("Password or OAuth token is required")
                server.login(self.username, self.password)
                print(" ✓ Authenticated via app password")
            
            for entry in entries_list:
                # メール作成
                msg = MIMEMultipart("alternative")
                msg["Subject"] = self.subject_template.format(
                    title=entry.metadata.get("title", "PR Times Press Release"),
                    source=entry.source,
                )
                msg["From"] = self.from_addr
                msg["To"] = ", ".join(self.to_addrs)
                
                # コンテンツ作成
                title = entry.metadata.get("title", "No Title")
                url = entry.metadata.get("url", "")
                content = entry.content
                
                html_content = self.content_template.format(
                    title=title,
                    content=content,
                    url=url,
                )
                
                # プレーンテキスト版も作成
                text_content = f"{title}\n\n{content}\n\n元記事：{url}"
                
                msg.attach(MIMEText(text_content, "plain", "utf-8"))
                msg.attach(MIMEText(html_content, "html", "utf-8"))
                
                # 送信
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
                print(f" ✓ Sent: {title}")
                logger.info(f"Email sent: {title}")
            
            server.quit()
            print(f"Successfully sent {len(entries_list)} email(s).")
            
        except Exception as e:
            logger.error(f"Failed to send emails: {e}")
            raise
