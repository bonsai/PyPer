# src/plugins/subscription_prtimes.py
import requests
import hashlib
import logging
import os
from typing import Dict, Any, Iterator
from base import Entry, SubscriptionPlugin

logger = logging.getLogger(__name__)


class Plugin(SubscriptionPlugin):
    """
    A subscription plugin to fetch press releases from PR Times.
    Fetches from the search results page for "発表会" keyword.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = self.config.get(
            "url", 
            "https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word=%E7%99%BA%E8%A1%A8%E4%BC%9A"
        )
        self.limit = self.config.get("limit", 10)
        self.state_file = self.config.get("state_file", "prtimes_state.txt")
        self.seen_urls = set()
        
        if self.state_file and os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.seen_urls = set(line.strip() for line in f if line.strip())
            except Exception as e:
                logger.error(f"Failed to load state file {self.state_file}: {e}")
    
    def _save_state(self):
        if self.state_file:
            try:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    for url in sorted(self.seen_urls):
                        f.write(f"{url}\n")
            except Exception as e:
                logger.error(f"Failed to save state file {self.state_file}: {e}")
    
    def _fetch_press_releases(self) -> Iterator[Dict[str, str]]:
        """
        Fetch press releases from PR Times search page.
        Yields dict with title, url, summary.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
        }
        
        try:
            response = requests.get(self.base_url, headers=headers, timeout=30)
            response.raise_for_status()
            html = response.text
            
            # 簡易 HTML パース（正規表現を使用）
            import re
            
            # 各プレスリリースのエントリーを抽出
            # PR Times の HTML 構造に基づき、タイトルと URL を抽出
            pattern = r'<a[^>]*href="([^"]*\.html)"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, html)
            
            seen_in_session = set()
            count = 0
            
            for url, title in matches:
                if count >= self.limit:
                    break
                
                # 重複チェック
                if url in seen_in_session:
                    continue
                seen_in_session.add(url)
                
                # 既に送信済みの URL はスキップ
                if url in self.seen_urls:
                    continue
                
                # 絶対 URL に変換
                if not url.startswith("http"):
                    url = "https://prtimes.jp" + url if not url.startswith("/") else "https://prtimes.jp" + url
                
                title = title.strip()
                
                # サマリー生成（タイトルの一部を使用）
                summary = f"{title} のプレスリリースが公開されました。"
                
                yield {
                    "title": title,
                    "url": url,
                    "summary": summary,
                }
                count += 1
                
        except Exception as e:
            logger.error(f"Failed to fetch PR Times: {e}")
            raise
    
    def execute(self) -> Iterator[Entry]:
        """
        Fetches press releases from PR Times and yields them as Entry objects.
        """
        print(f"Fetching press releases from PR Times: {self.base_url}")
        
        count = 0
        for item in self._fetch_press_releases():
            title = item["title"]
            url = item["url"]
            summary = item["summary"]
            
            content = f"{title}\n\n{summary}"
            entry_id = hashlib.sha256(url.encode()).hexdigest()
            
            metadata = {
                "url": url,
                "title": title,
                "source": "PR Times",
            }
            
            yield Entry(
                id=entry_id,
                source=f"{self.name}::PR Times",
                content=content.strip(),
                timestamp=0,
                metadata=metadata,
            )
            
            self.seen_urls.add(url)
            count += 1
        
        print(f" ✓ Fetched {count} new press release(s) from PR Times")
        self._save_state()
