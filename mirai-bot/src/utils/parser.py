import feedparser
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class PaperEntry(BaseModel):
    """論文エントリーのデータ構造"""
    title: str
    url: str
    summary: Optional[str] = None
    published: Optional[str] = None
    authors: Optional[List[str]] = None
    doi: Optional[str] = None
    
class RSSParser:
    """RSSフィードを解析するクラス"""
    
    def __init__(self, feed_url: str):
        self.feed_url = feed_url
        
    def fetch_latest(self, limit: int = 10) -> List[PaperEntry]:
        """
        最新のエントリーを取得する
        
        Args:
            limit: 取得する最大エントリー数
            
        Returns:
            論文エントリーのリスト
        """
        try:
            feed = feedparser.parse(self.feed_url)
            
            if feed.get('bozo_exception'):
                logger.warning(f"RSS parsing warning: {feed.bozo_exception}")
            
            entries = []
            for entry in feed.entries[:limit]:
                # 著者情報の抽出（フォーマットが複数あるので対応）
                authors = []
                if hasattr(entry, 'authors'):
                    authors = [author.get('name', '') for author in entry.authors]
                elif hasattr(entry, 'author'):
                    authors = [entry.author]
                
                # DOIの抽出（URLから推測することも多い）
                doi = None
                if hasattr(entry, 'id') and 'doi.org' in entry.id:
                    doi = entry.id.split('doi.org/')[-1]
                elif 'doi.org' in entry.link:
                    doi = entry.link.split('doi.org/')[-1]
                
                paper = PaperEntry(
                    title=entry.get('title', 'No Title'),
                    url=entry.get('link', ''),
                    summary=entry.get('summary', ''),
                    published=entry.get('published', ''),
                    authors=authors,
                    doi=doi
                )
                entries.append(paper)
                
            logger.info(f"Fetched {len(entries)} entries from RSS")
            return entries
            
        except Exception as e:
            logger.error(f"Failed to fetch RSS: {e}")
            return []
    
    def extract_pdf_links(self, entry: PaperEntry) -> List[str]:
        """
        論文エントリーからPDFリンクを抽出（Natureの特殊フォーマット対応）
        
        Args:
            entry: 論文エントリー
            
        Returns:
            PDFのURLリスト
        """
        pdf_links = []
        
        # Natureの場合、特定のパターンでPDFが利用可能
        if 'nature.com' in entry.url:
            # 記事URLをPDF URLに変換
            # https://www.nature.com/articles/s41586-023-06724-4 
            # -> https://www.nature.com/articles/s41586-023-06724-4.pdf 
            if '/articles/' in entry.url:
                pdf_url = f"{entry.url}.pdf"
                pdf_links.append(pdf_url)
        
        return pdf_links