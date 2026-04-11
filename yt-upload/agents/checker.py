"""
Completion Checker Agent
Verifies that all required assets are present for a content item
"""

import os
import json
from pathlib import Path

class CompletionChecker:
    def __init__(self):
        self.required_files = ['text.md', 'audio.mp3', 'video.mp4']
    
    def check_completion(self, item_path):
        """Check if a content item has all required assets"""
        item_path = Path(item_path)
        missing_files = []
        
        for required_file in self.required_files:
            if not (item_path / required_file).exists():
                missing_files.append(required_file)
        
        # Check if images directory exists and has content
        images_dir = item_path / "images"
        if images_dir.exists():
            image_files = list(images_dir.glob("*"))
            if not image_files:
                missing_files.append("images (directory empty)")
        else:
            missing_files.append("images directory")
        
        return {
            'is_complete': len(missing_files) == 0,
            'missing_files': missing_files
        }

if __name__ == "__main__":
    checker = CompletionChecker()
    result = checker.check_completion("../01-content-repository/content-items/item-001")
    print(f"Completion status: {result}")
