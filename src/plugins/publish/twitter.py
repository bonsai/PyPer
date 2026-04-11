# src/plugins/twitter.py

import tweepy
import logging
from typing import Dict, Any, Iterator
from ..base import Entry, PublishPlugin

logger = logging.getLogger(__name__)

class Plugin(PublishPlugin):
    """
    A publish plugin to post updates to Twitter/X.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.consumer_key = self.config.get("consumer_key")
        self.consumer_secret = self.config.get("consumer_secret")
        self.access_token = self.config.get("access_token")
        self.access_token_secret = self.config.get("access_token_secret")
        self.bearer_token = self.config.get("bearer_token")

        if not (self.consumer_key and self.consumer_secret and self.access_token and self.access_token_secret):
            if not self.bearer_token:
                raise ValueError("Twitter plugin requires OAuth 1.0a keys or a Bearer Token.")

        try:
            # Use Client for v2 API
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret
            )
            print("Twitter client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            raise e

    def execute(self, entries: Iterator[Entry]):
        """
        Receives entries and posts them to Twitter/X.
        It looks for 'x_summary' in metadata, otherwise uses content.
        """
        print(f"Executing TwitterPlugin: Publishing entries...")
        for entry in entries:
            # Prefer x_summary if available
            text = entry.metadata.get("x_summary", entry.content)

            # Twitter limit is 280 characters for v2, but traditionally 140 for some accounts/apps.
            # We'll truncate if necessary, but the LLM should handle this.
            if len(text) > 280:
                text = text[:277] + "..."

            try:
                print(f"  Posting to Twitter: {text[:50]}...")
                # In a real scenario, we might want to avoid duplicate posts.
                # Tweepy v2 post
                self.client.create_tweet(text=text)
                print(f"  Successfully posted entry {entry.id[:10]}")
            except Exception as e:
                logger.error(f"Failed to post to Twitter: {e}")
                continue
