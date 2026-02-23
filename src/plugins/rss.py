# src/plugins/rss.py

import feedparser
import logging
import hashlib
import os
from typing import Dict, Any, Iterator, List, Optional
from .base import Entry, SubscriptionPlugin

logger = logging.getLogger(__name__)

class Plugin(SubscriptionPlugin):
    """
    A subscription plugin to fetch data from RSS feeds.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = self.config.get("url")
        self.urls = self.config.get("urls", [])
        if self.url:
            self.urls.append(self.url)

        if not self.urls:
            raise ValueError("RSS plugin must have at least one 'url' or 'urls' in config.")

        self.limit = self.config.get("limit", 10)
        self.state_file = self.config.get("state_file")
        self.seen_urls = set()
        if self.state_file and os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.seen_urls = set(line.strip() for line in f if line.strip())
            except Exception as e:
                logger.error(f"Failed to load state file {self.state_file}: {e}")

    def _save_state(self):
        if self.state_file:
            try:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    for url in sorted(self.seen_urls):
                        f.write(f"{url}\n")
            except Exception as e:
                logger.error(f"Failed to save state file {self.state_file}: {e}")

    def execute(self) -> Iterator[Entry]:
        """
        Fetches entries from RSS feeds and yields them as Entry objects.
        """
        for feed_url in self.urls:
            print(f"Executing RSSPlugin: Fetching from '{feed_url}'...")
            try:
                feed = feedparser.parse(feed_url)

                if feed.get('bozo_exception'):
                    logger.warning(f"RSS parsing warning for {feed_url}: {feed.bozo_exception}")

                count = 0
                for entry in feed.entries:
                    if count >= self.limit:
                        break

                    link = entry.get('link', '')
                    if link in self.seen_urls:
                        continue

                    title = entry.get('title', 'No Title')
                    summary = entry.get('summary', '')
                    content = f"{title}\n\n{summary}"

                    entry_id = hashlib.sha256(link.encode()).hexdigest()

                    # Metadata extraction
                    metadata = {
                        "url": link,
                        "title": title,
                        "author": entry.get('author', ''),
                        "published": entry.get('published', ''),
                    }

                    # Handle authors list if available
                    if hasattr(entry, 'authors'):
                        metadata["authors"] = [a.get('name', '') for a in entry.authors]

                    yield Entry(
                        id=entry_id,
                        source=f"{self.name}::{feed_url}",
                        content=content.strip(),
                        timestamp=0, # Could parse published date if needed
                        metadata=metadata,
                    )

                    self.seen_urls.add(link)
                    count += 1

                print(f"  Fetched {count} new entries from {feed_url}")

            except Exception as e:
                logger.error(f"Failed to fetch RSS from {feed_url}: {e}")
                continue

        self._save_state()
