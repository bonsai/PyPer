# tests/test_gmail.py

import unittest
import sys
import os
from io import StringIO
from unittest.mock import patch

# Add 'src' to path to allow direct import of plugins
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from plugins.base import Entry
from plugins.gmail import Plugin as GmailPlugin

class TestGmailPlugin(unittest.TestCase):
    """
    Unit tests for the Gmail publish plugin.
    """

    def test_config_validation(self):
        """
        Tests that the plugin raises an error if config is invalid.
        """
        with self.assertRaises(ValueError) as context:
            GmailPlugin({}) # Missing 'recipient'

        self.assertIn("must contain a 'recipient'", str(context.exception))

    def test_mock_email_output(self):
        """
        Tests that the plugin correctly formats and prints a mock email.
        """
        # 1. Create a sample entry
        sample_entry = Entry(
            id="test_id_789",
            source="test_source",
            content="This is the email body content.",
            timestamp=1678886400000,
            metadata={"tag": "important", "author": "Jules"}
        )

        # 2. Instantiate the plugin with valid config
        config = {"recipient": "test@example.com"}
        plugin = GmailPlugin(config)

        # 3. Capture stdout to check the output
        captured_output = StringIO()
        with patch('sys.stdout', new=captured_output) as fake_out:
            # 4. Execute the plugin
            plugin.execute(iter([sample_entry]))

        # 5. Get the output and verify its contents
        output = captured_output.getvalue()

        # Check for key parts of the mock email
        self.assertIn("--- MOCK GMAIL SEND ---", output)
        self.assertIn("To: test@example.com", output)
        self.assertIn("Subject: RAG Idea from Source: test_source", output)
        self.assertIn("Content:\nThis is the email body content.", output)
        self.assertIn("'author': 'Jules'", output) # Check metadata
        self.assertIn("GmailPlugin: Processed 1 entries.", output)

if __name__ == '__main__':
    unittest.main()
