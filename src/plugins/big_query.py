# src/plugins/bigquery.py

import json
from typing import Dict, Any, Iterator
from .base import Entry, PublishPlugin

class Plugin(PublishPlugin):
    """
    A publish plugin to send entries to Google BigQuery.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.table_id = self.config.get("table_id")
        if not self.table_id:
            raise ValueError("Config for BigQuery plugin must contain a 'table_id'.")

    def execute(self, entries: Iterator[Entry]):
        """
        Receives Entry objects and prints them to stdout for now.
        The actual implementation will send data to BigQuery.
        """
        print(
            f"Executing BigQueryPlugin: Pretending to send to '{self.table_id}'..."
        )
        count = 0
        for entry in entries:
            # Convert dataclass to a dict for printing
            entry_dict = {
                "id": entry.id,
                "source": entry.source,
                "content": entry.content,
                "timestamp": entry.timestamp,
                "metadata": entry.metadata,
                "vector_preview": f"{str(entry.vector)[:50]}..."
            }
            print(json.dumps(entry_dict, indent=2, ensure_ascii=False))
            count += 1

        print(f"BigQueryPlugin: Processed {count} entries.")
