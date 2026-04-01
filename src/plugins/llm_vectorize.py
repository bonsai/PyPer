# src/plugins/llm_vectorize.py

from typing import Dict, Any, Iterator
from .base import Entry, FilterPlugin

class Plugin(FilterPlugin):
    """
    A filter plugin to vectorize the content of an entry using an LLM.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = self.config.get("model", "text-embedding-004")

    def execute(self, entries: Iterator[Entry]) -> Iterator[Entry]:
        """
        Receives entries, vectorizes their content, and yields them back.
        This is a mock implementation.
        """
        print(f"Executing LLMVectorizePlugin (using mock for model '{self.model}')...")

        for entry in entries:
            # [MOCK] In a real implementation, this would call the Vertex AI API
            # with entry.content and get back a real embedding vector.
            print(f"  Vectorizing content for entry: {entry.id[:10]}...")

            # Create a deterministic, fixed-size dummy vector for testing.
            # A real text-embedding-004 vector would have 768 dimensions.
            dummy_vector = ([0.1, 0.2, 0.3] * 256)

            entry.vector = dummy_vector
            yield entry
