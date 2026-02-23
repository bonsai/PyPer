#!/usr/bin/env python3
"""
Project Mirai-Yokai: 論文要約・多動投稿BOT
Phase 1: RSSから最新論文を取得し、未読を検出する
"""

import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.utils.parser import RSSParser
from src.utils.storage import URLStorage

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """メイン実行関数"""
    logger.info("=" * 50)
    logger.info("Project Mirai-Yokai Phase 1 開始")
    logger.info("=" * 50)
    
    # 1. RSSパーサーの初期化
    parser = RSSParser(settings.rss_url)
    
    # 2. 最新論文の取得
    logger.info(f"RSSフィードから取得中: {settings.rss_url}")
    latest_papers = parser.fetch_latest(limit=10)
    
    if not latest_papers:
        logger.error("論文を取得できませんでした")
        return
    
    logger.info(f"✓ {len(latest_papers)}件の論文を取得")
    
    # 3. 既読管理の初期化
    storage = URLStorage(settings.data_dir, settings.seen_urls_file)
    seen_urls = storage.load_seen_urls()
    logger.info(f"✓ 既読URL: {len(seen_urls)}件")
    
    # 4. 新規論文のフィルタリング
    new_papers = []
    for paper in latest_papers:
        if paper.url not in seen_urls:
            new_papers.append(paper)
    
    logger.info(f"✓ 新規論文: {len(new_papers)}件")
    
    # 5. 結果の表示
    if new_papers:
        logger.info("\n📄 新着論文一覧:")
        for i, paper in enumerate(new_papers, 1):
            logger.info(f"\n--- {i}. {paper.title} ---")
            logger.info(f"URL: {paper.url}")
            if paper.authors:
                logger.info(f"著者: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}")
            if paper.doi:
                logger.info(f"DOI: {paper.doi}")
            
            # PDFリンクの取得
            pdf_links = parser.extract_pdf_links(paper)
            if pdf_links:
                logger.info(f"PDF: {pdf_links[0]}")
    else:
        logger.info("\n📭 新着論文はありません")
    
    # 6. 新規URLを保存（実際に処理したものだけを保存）
    if new_papers:
        new_urls = [paper.url for paper in new_papers]
        storage.add_new_urls(new_urls)
        logger.info(f"✓ {len(new_urls)}件の新規URLを保存")
    
    logger.info("=" * 50)
    logger.info("Phase 1 完了")

if __name__ == "__main__":
    main()