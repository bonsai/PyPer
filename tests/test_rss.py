# tests/test_rss.py

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add 'src' to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from plugins.rss import Plugin as RSSPlugin

class TestRSSPlugin(unittest.TestCase):
    def test_rss_fetch(self):
        mock_feed = MagicMock()
        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda k, default='': {
            'link': 'http://example.com/1',
            'title': 'Test Title',
            'summary': 'Test Summary',
            'author': 'Test Author',
            'published': '2023-01-01'
        }.get(k, default)
        mock_feed.entries = [mock_entry]
        mock_feed.get.return_value = None # No bozo exception

        with patch('feedparser.parse', return_value=mock_feed):
            config = {"url": "http://example.com/rss", "limit": 5}
            plugin = RSSPlugin(config)
            entries = list(plugin.execute())

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].metadata['url'], 'http://example.com/1')
            self.assertEqual(entries[0].metadata['title'], 'Test Title')
            self.assertIn('Test Title', entries[0].content)
            self.assertIn('Test Summary', entries[0].content)

if __name__ == '__main__':
    unittest.main()
