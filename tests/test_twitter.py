# tests/test_twitter.py

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add 'src' to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from plugins.base import Entry
from plugins.twitter import Plugin as TwitterPlugin

class TestTwitterPlugin(unittest.TestCase):
    @patch('tweepy.Client')
    def test_twitter_publish(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = {
            "consumer_key": "k",
            "consumer_secret": "s",
            "access_token": "at",
            "access_token_secret": "as"
        }
        plugin = TwitterPlugin(config)

        entry = Entry(
            id="1",
            source="src",
            content="test tweet",
            metadata={"x_summary": "summary tweet"}
        )

        plugin.execute(iter([entry]))

        # Verify that create_tweet was called with x_summary
        mock_client.create_tweet.assert_called_with(text="summary tweet")

if __name__ == '__main__':
    unittest.main()
