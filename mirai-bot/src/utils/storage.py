import os
from pathlib import Path
from typing import Set, List
import logging

logger = logging.getLogger(__name__)

class URLStorage:
    """既読URLの永続化を管理するクラス"""
    
    def __init__(self, data_dir: str = "data", filename: str = "seen_urls.txt"):
        self.data_dir = Path(data_dir)
        self.filepath = self.data_dir / filename
        self._ensure_dir()
        
    def _ensure_dir(self):
        """データディレクトリの存在を確認"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def load_seen_urls(self) -> Set[str]:
        """既読URLをファイルから読み込む"""
        seen_urls = set()
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    seen_urls = set(line.strip() for line in f if line.strip())
                logger.info(f"Loaded {len(seen_urls)} seen URLs from {self.filepath}")
            except Exception as e:
                logger.error(f"Failed to load seen URLs: {e}")
        return seen_urls
    
    def save_seen_urls(self, urls: Set[str]):
        """既読URLをファイルに保存"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                for url in sorted(urls):
                    f.write(f"{url}\n")
            logger.info(f"Saved {len(urls)} seen URLs to {self.filepath}")
        except Exception as e:
            logger.error(f"Failed to save seen URLs: {e}")
    
    def add_new_urls(self, new_urls: List[str]) -> Set[str]:
        """新しいURLを追加して保存"""
        seen = self.load_seen_urls()
        original_count = len(seen)
        seen.update(new_urls)
        
        if len(seen) > original_count:
            self.save_seen_urls(seen)
            added = len(seen) - original_count
            logger.info(f"Added {added} new URLs to storage")
            
        return seen