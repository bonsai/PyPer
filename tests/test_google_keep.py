# tests/test_google_keep.py

import unittest
import sys
import os
import shutil
import tempfile
import json
from hashlib import sha256

# Add 'src' to path to allow direct import of plugins
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from plugins.google_keep import Plugin as GoogleKeepPlugin

class TestGoogleKeepPluginMetadata(unittest.TestCase):
    """
    Unit tests for the GoogleKeep subscription plugin, focusing on metadata extraction.
    """

    def setUp(self):
        """
        Set up a temporary directory with a fixture file for testing.
        """
        self.test_dir = tempfile.mkdtemp()
        self.fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'keep_note_with_image.json')
        self.note_filename = 'test_note.json'

        # Copy the fixture to the temporary directory
        shutil.copy(self.fixture_path, os.path.join(self.test_dir, self.note_filename))

        # Load fixture data to use in assertions
        with open(self.fixture_path, 'r') as f:
            self.fixture_data = json.load(f)

    def tearDown(self):
        """
        Remove the temporary directory and its contents after the test.
        """
        shutil.rmtree(self.test_dir)

    def test_metadata_extraction(self):
        """
        Tests if the plugin correctly extracts all specified metadata from a JSON file.
        """
        config = {"path": self.test_dir}
        plugin = GoogleKeepPlugin(config)

        # Execute the plugin and collect the results into a list
        entries = list(plugin.execute())

        # 1. Check that exactly one entry was generated
        self.assertEqual(len(entries), 1)
        entry = entries[0]

        # 2. Check basic entry fields
        expected_id = sha256(self.note_filename.encode()).hexdigest()
        self.assertEqual(entry.id, expected_id)
        self.assertEqual(entry.source, "Subscription::GoogleKeep")

        expected_content = f"{self.fixture_data['title']}\\n\\n{self.fixture_data['textContent']}"
        self.assertEqual(entry.content, expected_content)

        # 3. Check the extracted metadata
        metadata = entry.metadata
        self.assertIsNotNone(metadata)

        self.assertEqual(metadata.get("created_timestamp_usec"), self.fixture_data["createdTimestampUsec"])
        self.assertEqual(metadata.get("is_archived"), self.fixture_data["isArchived"])
        self.assertEqual(metadata.get("color"), self.fixture_data["color"].lower())

        # 4. Check the mocked Gemini image description
        self.assertIn("image_content_description", metadata)
        expected_description = "This is a mock description for the image 'test_image.jpg'."
        self.assertEqual(metadata["image_content_description"], expected_description)

if __name__ == '__main__':
    unittest.main()
