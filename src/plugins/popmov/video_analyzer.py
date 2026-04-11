"""
PopMov Video Analyzer - Filter Plugin

Analyzes video metrics from entries and enriches metadata.
"""
import logging
from typing import Dict, Any, Iterator

from ..base import Entry, FilterPlugin

logger = logging.getLogger(__name__)


class Plugin(FilterPlugin):
    """
    A filter plugin that analyzes video metrics and enriches entries.
    """

    @property
    def name(self) -> str:
        return "Filter::PopMov::VideoAnalyzer"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.metrics = self.config.get("metrics", ["views", "likes", "comments"])

    def _calculate_engagement(self, entry: Entry) -> float:
        """Calculate engagement rate from metadata."""
        views = entry.metadata.get("views", 0)
        likes = entry.metadata.get("likes", 0)
        comments = entry.metadata.get("comments", 0)
        if views == 0:
            return 0.0
        return (likes + comments) / views

    def _calculate_performance_score(self, entry: Entry) -> float:
        """Calculate overall performance score (0-10)."""
        views = entry.metadata.get("views", 0)
        engagement = self._calculate_engagement(entry)

        views_score = min(views / 10000, 10)
        engagement_score = min(engagement * 100, 10)
        return round((views_score + engagement_score) / 2, 2)

    def execute(self, entries: Iterator[Entry]) -> Iterator[Entry]:
        """
        Receives entries, analyzes video metrics, and enriches metadata.
        """
        print(f"[VideoAnalyzer] Analyzing {len(list(entries_clone := list(entries)))} entries...")

        for entry in entries_clone:
            engagement = self._calculate_engagement(entry)
            perf_score = self._calculate_performance_score(entry)

            entry.metadata["engagement_rate"] = round(engagement, 4)
            entry.metadata["performance_score"] = perf_score
            entry.metadata["analysis_metrics"] = self.metrics

            rating = "高" if perf_score >= 7 else "中" if perf_score >= 4 else "低"
            entry.metadata["performance_rating"] = rating

            yield entry

        print(f" ✓ Analyzed {len(entries_clone)} video(s)")
