"""
Content Search Agent
Searches for completed content items ready for upload
"""

import os
import json
from pathlib import Path

class ContentSearcher:
    def __init__(self, content_repo_path):
        self.content_repo_path = Path(content_repo_path)
    
    def find_ready_content(self):
        """Find content items that are ready for upload"""
        ready_items = []
        
        content_items_dir = self.content_repo_path / "content-items"
        if not content_items_dir.exists():
            return ready_items
        
        for item_dir in content_items_dir.iterdir():
            if item_dir.is_dir():
                metadata_file = item_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        if metadata.get('status') == 'ready_for_upload':
                            ready_items.append({
                                'path': item_dir,
                                'metadata': metadata
                            })
        
        return ready_items

if __name__ == "__main__":
    searcher = ContentSearcher("../01-content-repository")
    ready_content = searcher.find_ready_content()
    print(f"Found {len(ready_content)} items ready for upload")
    for item in ready_content:
        print(f"- {item['metadata']['title']}")
