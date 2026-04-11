# src/plugins/line_notify.py

import requests
import logging
from typing import Dict, Any, Iterator
from ..base import PublishPlugin, Entry

logger = logging.getLogger(__name__)


class Plugin(PublishPlugin):
    """
    A publish plugin to send entries via LINE Notify.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.notify_token = self.config.get("notify_token")
        
        if not self.notify_token:
            raise ValueError("LINE Notify token is required")

    @property
    def name(self) -> str:
        return "Publish::LINE Notify"

    def execute(self, entries: Iterator[Entry]) -> None:
        """
        Sends entries via LINE Notify.
        """
        entries_list = list(entries)
        
        if not entries_list:
            logger.info("No entries to send via LINE Notify")
            return

        print(f"Sending {len(entries_list)} entries via LINE Notify...")

        for entry in entries_list:
            try:
                self.send_notify(entry)
            except Exception as e:
                logger.error(f"Failed to send LINE Notify: {e}")

    def send_notify(self, entry: Entry):
        """
        Send a single entry via LINE Notify.
        """
        url = "https://notify-api.line.me/api/notify"
        headers = {
            "Authorization": f"Bearer {self.notify_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        title = entry.metadata.get("title", "PR Times")
        url_link = entry.metadata.get("url", "")
        
        message = f"📰 {title}\n\n{entry.content[:100]}..."
        
        data = {
            "message": message,
            "url": url_link,
        }

        response = requests.post(url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            print(f" ✁ELINE Notify sent: {title}")
        else:
            logger.error(f"LINE Notify failed: {response.text}")
