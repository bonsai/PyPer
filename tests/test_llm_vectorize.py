# tests/test_llm_vectorize.py

import unittest
import sys
import os

# Add 'src' to path to allow direct import of plugins
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from plugins.base import Entry
from plugins.llm_vectorize import Plugin as VectorizePlugin

class TestLlmVectorizePlugin(unittest.TestCase):
    """
    Unit tests for the LLMVectorizePlugin filter plugin.
    """

    def test_vectorization_mock(self):
        """
        Tests that the plugin adds the correct mock vector to an entry.
        """
        # 1. Create a sample entry without a vector
        sample_entry = Entry(
            id="test_id_123",
            source="test_source",
            content="This is the content to be vectorized."
        )

        # 2. Instantiate the plugin
        config = {"model": "text-embedding-004"}
        plugin = VectorizePlugin(config)

        # 3. Execute the plugin with the sample entry
        # The execute method expects an iterator, so we pass a list iterator
        processed_entries = list(plugin.execute(iter([sample_entry])))

        # 4. Check that one entry was returned
        self.assertEqual(len(processed_entries), 1)
        processed_entry = processed_entries[0]

        # 5. Verify the vector was added correctly
        self.assertIsNotNone(processed_entry.vector)
        self.assertIsInstance(processed_entry.vector, list)

        # Check the vector's content
        expected_dummy_vector = ([0.1, 0.2, 0.3] * 256)
        self.assertEqual(processed_entry.vector, expected_dummy_vector)

        # 6. Verify other fields were not changed
        self.assertEqual(processed_entry.id, sample_entry.id)
        self.assertEqual(processed_entry.content, sample_entry.content)


if __name__ == '__main__':
    unittest.main()
