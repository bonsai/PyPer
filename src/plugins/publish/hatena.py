# src/plugins/hatena.py

import requests
import logging
import datetime
import hashlib
import base64
import random
import xml.sax.saxutils
from typing import Dict, Any, Iterator
from ..base import Entry, PublishPlugin

logger = logging.getLogger(__name__)

class Plugin(PublishPlugin):
    """
    A publish plugin to post entries to Hatena Blog using AtomPub.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.hatena_id = self.config.get("hatena_id")
        self.blog_id = self.config.get("blog_id")
        self.api_key = self.config.get("api_key")

        if not (self.hatena_id and self.blog_id and self.api_key):
            raise ValueError("Hatena plugin requires 'hatena_id', 'blog_id', and 'api_key'.")

        self.endpoint = f"https://blog.hatena.ne.jp/{self.hatena_id}/{self.blog_id}/atom/entry"

    def _get_wsse_header(self) -> Dict[str, str]:
        """Generates WSSE header for Hatena API."""
        nonce = hashlib.sha1(str(random.random()).encode()).hexdigest()
        created = datetime.datetime.now().isoformat() + "Z"

        digest = hashlib.sha1((nonce + created + self.api_key).encode()).digest()
        password_digest = base64.b64encode(digest).decode()

        wsse = (
            f'UsernameToken Username="{self.hatena_id}", '
            f'PasswordDigest="{password_digest}", '
            f'Nonce="{base64.b64encode(nonce.encode()).decode()}", '
            f'Created="{created}"'
        )
        return {"X-WSSE": wsse}

    def execute(self, entries: Iterator[Entry]):
        """
        Receives entries and posts them to Hatena Blog.
        """
        print(f"Executing HatenaPlugin: Publishing entries to {self.blog_id}...")
        for entry in entries:
            title = entry.metadata.get("title", f"Entry {entry.id[:10]}")
            # Use blog_summary if available
            content_body = entry.metadata.get("blog_summary", entry.content)

            # Escape XML special characters
            escaped_title = xml.sax.saxutils.escape(title)
            escaped_content = xml.sax.saxutils.escape(content_body)

            # Construct Atom XML
            xml_template = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>{escaped_title}</title>
  <author><name>{self.hatena_id}</name></author>
  <content type="text/plain">
{escaped_content}
  </content>
  <updated>{datetime.datetime.now().isoformat()}Z</updated>
  <app:control>
    <app:draft>no</app:draft>
  </app:control>
</entry>
"""
            try:
                print(f"  Posting to Hatena Blog: {title}")
                headers = self._get_wsse_header()
                headers["Content-Type"] = "application/xml"

                response = requests.post(self.endpoint, data=xml_template.encode('utf-8'), headers=headers)

                if response.status_code in (201, 200):
                    print(f"  Successfully posted entry {entry.id[:10]} to Hatena")
                else:
                    logger.error(f"Failed to post to Hatena: {response.status_code} {response.text}")
            except Exception as e:
                logger.error(f"Error posting to Hatena: {e}")
                continue
