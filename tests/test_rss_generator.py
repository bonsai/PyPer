Unit tests for the RSS Generator Filter Plugin.
"""
import unittest
import sys
import os
from io import StringIO
from unittest.mock import patch, MagicMock

# Add 'src' to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from plugins.base import Entry
from plugins.filter_rss_generator import Plugin as RSSGeneratorPlugin


class TestRSSGeneratorPlugin(unittest.TestCase):
    """
    Unit tests for the RSS Generator filter plugin.
    """

    def test_rss_generation(self):
        """
        Tests that the plugin generates valid RSS XML.
        """
        # Create sample entries
        sample_entries = [
            Entry(
                id="test_id_001",
                source="Subscription::PRTimes",
                content="Test press release content 1",
                timestamp=1678886400000,
                metadata={"title": "Test Press Release 1", "url": "https://example.com/1"}
            ),
            Entry(
                id="test_id_002",
                source="Subscription::PRTimes",
                content="Test press release content 2",
                timestamp=1678886500000,
                metadata={"title": "Test Press Release 2", "url": "https://example.com/2"}
            )
        ]

        # Instantiate the plugin
        config = {
            "rss_title": "Test RSS Feed",
            "rss_link": "https://example.com",
            "rss_description": "Test Description",
            "rss_file": "test_feed.xml"
        }
        plugin = RSSGeneratorPlugin(config)

        # Execute the plugin
        entries_iter = iter(sample_entries)
        result_entries = list(plugin.execute(entries_iter))

        # Verify entries are passed through
        self.assertEqual(len(result_entries), 2)
        
        # Verify RSS file was created
        self.assertTrue(os.path.exists("test_feed.xml"))
        
        # Read and verify RSS content
        with open("test_feed.xml", 'r', encoding='utf-8') as f:
            rss_content = f.read()
        
        # Check RSS structure
        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', rss_content)
        self.assertIn('<rss version="2.0">', rss_content)
        self.assertIn('<title>Test RSS Feed</title>', rss_content)
        self.assertIn('<link>https://example.com</link>', rss_content)
        self.assertIn('<description>Test Description</description>', rss_content)
        self.assertIn('<title>Test Press Release 1</title>', rss_content)
        self.assertIn('<title>Test Press Release 2</title>', rss_content)
        self.assertIn('<link>https://example.com/1</link>', rss_content)
        self.assertIn('<link>https://example.com/2</link>', rss_content)
        
        # Cleanup
        if os.path.exists("test_feed.xml"):
            os.remove("test_feed.xml")

    def test_empty_entries(self):
        """
        Tests that the plugin handles empty entry list gracefully.
        """
        config = {
            "rss_title": "Test RSS Feed",
            "rss_file": "test_empty_feed.xml"
        }
        plugin = RSSGeneratorPlugin(config)

        # Execute with empty iterator
        entries_iter = iter([])
        result_entries = list(plugin.execute(entries_iter))

        self.assertEqual(len(result_entries), 0)
        
        # Cleanup if file was created
        if os.path.exists("test_empty_feed.xml"):
            os.remove("test_empty_feed.xml")


if __name__ == '__main__':
    unittest.main()