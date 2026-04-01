# tests/test_hatena.py

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add 'src' to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from plugins.base import Entry
from plugins.hatena import Plugin as HatenaPlugin

class TestHatenaPlugin(unittest.TestCase):
    @patch('requests.post')
    def test_hatena_publish(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        config = {
            "hatena_id": "user",
            "blog_id": "blog",
            "api_key": "key"
        }
        plugin = HatenaPlugin(config)

        entry = Entry(
            id="1",
            source="src",
            content="test content",
            metadata={"title": "test title", "blog_summary": "detailed summary"}
        )

        plugin.execute(iter([entry]))

        # Verify that requests.post was called
        self.assertTrue(mock_post.called)
        args, kwargs = mock_post.call_args
        self.assertIn("https://blog.hatena.ne.jp/user/blog/atom/entry", args[0])
        self.assertIn("detailed summary", kwargs['data'].decode('utf-8'))
        self.assertIn("test title", kwargs['data'].decode('utf-8'))

if __name__ == '__main__':
    unittest.main()
