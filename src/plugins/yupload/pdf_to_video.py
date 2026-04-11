"""
YUpload PDF to Video - Filter Plugin

Converts PDF to video using LLM script generation + TTS + MoviePy.
"""
import hashlib
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Iterator

from ..base import Entry, FilterPlugin

logger = logging.getLogger(__name__)


class Plugin(FilterPlugin):
    """
    A filter plugin that converts PDF entries to video metadata.
    Prepares all necessary information for downstream video creation.
    """

    @property
    def name(self) -> str:
        return "Filter::YUpload::PDFToVideo"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_model = self.config.get("llm_model", "gemini-1.5-flash")
        self.tts_voice = self.config.get("tts_voice", "ja-JP-KeitaNeural")
        self.target_duration = self.config.get("target_duration", 90)  # seconds
        self.output_dir = self.config.get("output_dir", "data/yupload_output")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        try:
            import pymupdf
            doc = pymupdf.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install pymupdf")
            return ""
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {e}")
            return ""

    def _generate_script(self, pdf_text: str) -> dict:
        """Generate video script from PDF text (mock - replace with LLM call)."""
        # Mock script - in production, use LLM API
        pdf_type = "unknown"
        if any(k in pdf_text.lower() for k in ["投資", "finance", "stock"]):
            pdf_type = "finance"
        elif any(k in pdf_text.lower() for k in ["科学", "science", "research"]):
            pdf_type = "science"

        mock_script = {
            "title": f"PDF動画: {pdf_type}",
            "description": f"{pdf_type}に関する解説動画",
            "segments": [
                {"text": "こんにちは！今日はこのPDFについて解説します！", "duration_sec": 18, "image_prompt": "friendly robot character"},
                {"text": "まず最初のポイントを見ていきましょう。", "duration_sec": 18, "image_prompt": "document analysis"},
                {"text": "重要な発見はこちらです。", "duration_sec": 18, "image_prompt": "light bulb moment"},
                {"text": "次のセクションも面白いですよ！", "duration_sec": 18, "image_prompt": "exciting discovery"},
                {"text": "まとめです。ありがとうございました！", "duration_sec": 18, "image_prompt": "thank you scene"},
            ],
            "bgm_style": "bright upbeat",
            "total_duration": self.target_duration,
        }
        return mock_script

    def execute(self, entries: Iterator[Entry]) -> Iterator[Entry]:
        """
        Receives entries, extracts PDF info, and prepares video metadata.
        """
        print(f"[PDFToVideo] Processing {len(list(entries_clone := list(entries)))} entry/entries...")

        for entry in entries_clone:
            pdf_path = entry.metadata.get("pdf_path")
            if not pdf_path or not Path(pdf_path).exists():
                pdf_path = entry.content  # Try content as path

            pdf_text = self._extract_pdf_text(pdf_path) if pdf_path else entry.content
            script = self._generate_script(pdf_text or entry.content)

            # Create output directory for this video
            video_id = hashlib.sha256(f"{entry.id}_video".encode()).hexdigest()
            video_dir = Path(self.output_dir) / video_id
            video_dir.mkdir(parents=True, exist_ok=True)

            # Save script
            script_path = video_dir / "script.json"
            with open(script_path, 'w', encoding='utf-8') as f:
                json.dump(script, f, ensure_ascii=False, indent=2)

            content = f"動画スクリプト生成完了: {script['title']}\nセグメント数: {len(script['segments'])}\n合計時間: {script['total_duration']}秒"

            metadata = {
                **entry.metadata,
                "video_id": video_id,
                "video_dir": str(video_dir),
                "script_path": str(script_path),
                "video_title": script["title"],
                "video_description": script["description"],
                "video_segments": script["segments"],
                "bgm_style": script["bgm_style"],
                "total_duration": script["total_duration"],
                "tts_voice": self.tts_voice,
                "source": "YUpload PDF-to-Video",
                "timestamp": datetime.now().isoformat(),
            }

            yield Entry(
                id=video_id,
                source=self.name,
                content=content,
                timestamp=0,
                metadata=metadata,
            )

        print(f" ✓ Generated video scripts for {len(entries_clone)} entry/entries")
