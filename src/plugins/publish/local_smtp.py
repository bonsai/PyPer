# src/plugins/publish_local_smtp.py
"""
Local SMTP Publish Plugin
Sends emails via local SMTP server.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Iterator, List
from ..base import Entry, PublishPlugin

logger = logging.getLogger(__name__)


class Plugin(PublishPlugin):
    """
    A publisher plugin that sends entries as emails via local SMTP server.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.enabled = self.config.get("enabled", True)
        self.smtp_host = self.config.get("smtp_host", "localhost")
        self.smtp_port = self.config.get("smtp_port", 1025)
        self.from_addr = self.config.get("from_addr", "prtimes@localhost")
        self.to_addrs = self.config.get("to_addrs", ["test@localhost"])
        self.subject_template = self.config.get("subject_template", "PR Times: {title}")
        self.content_template = self.config.get("content_template", """
<html>
<body>
<h1>{title}</h1>
<p>{content}</p>
<p><a href="{url}">允E��事を読む</a></p>
</body>
</html>
""")
        
        if isinstance(self.to_addrs, str):
            self.to_addrs = [self.to_addrs]
        
        print(f"Executing Local SMTP Plugin: Sending via {self.smtp_host}:{self.smtp_port}")
        print(f"From: {self.from_addr}, To: {', '.join(self.to_addrs)}")
    
    def execute(self, entries: Iterator[Entry]):
        """
        Receives Entry objects and sends them as emails via local SMTP.
        """
        if not self.enabled:
            logger.info("Local SMTP plugin is disabled. Skipping...")
            print("\nLocal SMTP plugin is disabled. Skipping...")
            return
        
        entries_list = list(entries)
        
        if not entries_list:
            logger.info("No entries to send.")
            print("No entries to send.")
            return
        
        print(f"\n{'='*60}")
        print(f"Sending {len(entries_list)} press release(s) via Local SMTP...")
        print(f"{'='*60}\n")
        
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            
            for i, entry in enumerate(entries_list, 1):
                title = entry.metadata.get("title", "No Title")
                url = entry.metadata.get("url", "")
                content = entry.content
                timestamp = entry.metadata.get("timestamp", datetime.now().isoformat())
                
                subject = self.subject_template.format(title=title, source=entry.source)
                
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = self.from_addr
                msg["To"] = ", ".join(self.to_addrs)
                
                text_content = f"{title}\n\n{content}\n\n允E��事：{url}"
                msg.attach(MIMEText(text_content, "plain", "utf-8"))
                
                html_content = self.content_template.format(
                    title=title,
                    content=content,
                    url=url,
                    timestamp=timestamp,
                )
                msg.attach(MIMEText(html_content, "html", "utf-8"))
                
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
                print(f" OK Sent Email {i}/{len(entries_list)}: {title}")
                logger.info(f"Email sent: {title}")
            
            server.quit()
            
            print(f"\n{'='*60}")
            print(f"Successfully sent {len(entries_list)} email(s) via Local SMTP.")
            print(f"{'='*60}")
            
        except ConnectionRefusedError:
            error_msg = f"Could not connect to SMTP server at {self.smtp_host}:{self.smtp_port}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            print("\nPlease ensure your local SMTP server is running.")
            raise
        except Exception as e:
            logger.error(f"Failed to send emails: {e}")
            raise