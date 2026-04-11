# src/plugins/filter_rss_generator.py
"""
RSS Generator Filter Plugin
Generates RSS feed from entries and includes RSS URL in email.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Iterator
from xml.etree import ElementTree as ET
from ..base import Entry, FilterPlugin

logger = logging.getLogger(__name__)


class Plugin(FilterPlugin):
    """
    A filter plugin that generates an RSS feed from entries.
    Adds the RSS feed URL/content to metadata for email delivery.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.rss_title = self.config.get("rss_title", "PR Times RSS Feed")
        self.rss_link = self.config.get("rss_link", "https://prtimes.jp/")
        self.rss_description = self.config.get("rss_description", "Latest press releases from PR Times")
        self.rss_file = self.config.get("rss_file", "prtimes_feed.xml")
        self.rss_url = self.config.get("rss_url", "")  # Public URL where RSS will be hosted
        self.entries_buffer = []
        
        print(f"RSS Generator initialized: title={self.rss_title}, file={self.rss_file}")
    
    def _generate_rss(self, entries: list) -> str:
        """
        Generate RSS 2.0 XML from entries.
        """
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        
        # Channel metadata
        ET.SubElement(channel, "title").text = self.rss_title
        ET.SubElement(channel, "link").text = self.rss_link
        ET.SubElement(channel, "description").text = self.rss_description
        ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0900")
        ET.SubElement(channel, "generator").text = "PyPer RSS Generator"
        
        # Add items
        for entry in entries:
            item = ET.SubElement(channel, "item")
            
            title = entry.metadata.get("title", "No Title")
            url = entry.metadata.get("url", "")
            summary = entry.content
            
            ET.SubElement(item, "title").text = title
            ET.SubElement(item, "link").text = url
            ET.SubElement(item, "description").text = summary
            ET.SubElement(item, "guid").text = entry.id
            ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0900")
        
        # Pretty print XML
        ET.indent(rss, space="  ")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding='unicode')
    
    def _save_rss(self, rss_content: str):
        """
        Save RSS feed to file.
        """
        try:
            with open(self.rss_file, 'w', encoding='utf-8') as f:
                f.write(rss_content)
            logger.info(f"RSS feed saved to {self.rss_file}")
            print(f" ✁ERSS feed saved to {self.rss_file}")
        except Exception as e:
            logger.error(f"Failed to save RSS feed: {e}")
            raise
    
    def execute(self, entries: Iterator[Entry]) -> Iterator[Entry]:
        """
        Buffers entries, generates RSS, and yields entries with RSS metadata.
        """
        # Buffer all entries
        for entry in entries:
            self.entries_buffer.append(entry)
            yield entry
        
        # Generate RSS if we have entries
        if self.entries_buffer:
            rss_content = self._generate_rss(self.entries_buffer)
            self._save_rss(rss_content)
            
            # Add RSS info to each entry's metadata for email template
            for entry in self.entries_buffer:
                entry.metadata['rss_file'] = self.rss_file
                if self.rss_url:
                    entry.metadata['rss_url'] = self.rss_url
            
            print(f" ✁EGenerated RSS feed with {len(self.entries_buffer)} entries")
        else:
            print("No entries to generate RSS feed")