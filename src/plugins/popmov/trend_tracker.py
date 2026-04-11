"""
PopMov Trend Tracker - Subscription Plugin

Tracks trending topics/keywords and yields them as Entry objects.
"""
import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Iterator

from ..base import Entry, SubscriptionPlugin

logger = logging.getLogger(__name__)


class Plugin(SubscriptionPlugin):
    """
    A subscription plugin that tracks trending topics.
    Yields trend data as Entry objects for downstream processing.
    """

    @property
    def name(self) -> str:
        return "Subscription::PopMov::TrendTracker"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.keyword = self.config.get("keyword", "")
        self.platform = self.config.get("platform", "youtube")
        self.limit = self.config.get("limit", 10)
        self.state_file = self.config.get("state_file", "data/trend_state.txt")
        self.seen_topics = set()

        if self.state_file and os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.seen_topics = set(line.strip() for line in f if line.strip())
            except Exception as e:
                logger.error(f"Failed to load trend state file: {e}")

    def _save_state(self):
        if self.state_file:
            try:
                os.makedirs(os.path.dirname(self.state_file) if os.path.dirname(self.state_file) else '.', exist_ok=True)
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    for topic in sorted(self.seen_topics):
                        f.write(f"{topic}\n")
            except Exception as e:
                logger.error(f"Failed to save trend state: {e}")

    def _fetch_trends(self) -> Iterator[Dict[str, str]]:
        """
        Fetch trending topics. Mock implementation - replace with actual API calls.
        """
        # Mock trend data - in production, integrate with:
        # - YouTube Trending API
        # - Google Trends
        # - Twitter Trends
        # - TikTok Trends
        mock_trends = [
            {"topic": f"{self.keyword or 'AI'}最新動向", "platform": self.platform, "score": 95},
            {"topic": f"{self.keyword or 'テクノロジー'}ニュース", "platform": self.platform, "score": 87},
            {"topic": f"{self.keyword or 'スタートアップ'}注目", "platform": self.platform, "score": 78},
        ]

        for trend in mock_trends[:self.limit]:
            yield trend

    def execute(self) -> Iterator[Entry]:
        """
        Fetches trending topics and yields them as Entry objects.
        """
        print(f"[TrendTracker] Fetching trends for '{self.keyword}' on {self.platform}...")

        count = 0
        for trend in self._fetch_trends():
            topic = trend["topic"]

            if topic in self.seen_topics:
                continue

            content = f"📈 トレンド: {topic}\nプラットフォーム: {trend['platform']}\nスコア: {trend['score']}"
            entry_id = hashlib.sha256(f"{topic}:{self.platform}".encode()).hexdigest()

            metadata = {
                "topic": topic,
                "platform": trend["platform"],
                "score": trend["score"],
                "source": "PopMov Trend Tracker",
                "timestamp": datetime.now().isoformat(),
            }

            yield Entry(
                id=entry_id,
                source=self.name,
                content=content.strip(),
                timestamp=0,
                metadata=metadata,
            )

            self.seen_topics.add(topic)
            count += 1

        print(f" ✓ Found {count} new trend(s)")
        self._save_state()
