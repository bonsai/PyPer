# src/plugins/llm_metadata_enricher.py

import google.generativeai as genai
import logging
import json
from typing import Dict, Any, Iterator, Optional
from pydantic import BaseModel, Field, ValidationError
from .base import Entry, FilterPlugin

logger = logging.getLogger(__name__)

class EnrichmentSchema(BaseModel):
    """Structured output for LLM enrichment."""
    x_summary: str = Field(description="Summary for Twitter/X (max 280 chars).")
    blog_summary: str = Field(description="Detailed summary for a blog post.")
    tags: list[str] = Field(default_factory=list, description="Relevant tags/keywords.")
    category: str = Field(default="General", description="Topic category.")

class Plugin(FilterPlugin):
    """
    A filter plugin to enrich entry metadata using Google Gemini API.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = self.config.get("api_key")
        self.model_name = self.config.get("model", "gemini-1.5-flash")

        if not self.api_key:
            raise ValueError("LLMMetadataEnricher requires an 'api_key'.")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

        self.prompt_template = self.config.get("prompt", """
Analyze the following content and provide:
1. A concise summary for Twitter (X) under 280 characters.
2. A detailed summary for a blog post.
3. A list of 5 relevant tags.
4. A single-word category.

Output MUST be in JSON format with keys: x_summary, blog_summary, tags, category.
""")

    def _extract_json(self, text: str) -> Optional[str]:
        """Extracts JSON string from LLM response."""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return text[start:end]
        return None

    def execute(self, entries: Iterator[Entry]) -> Iterator[Entry]:
        """
        Receives entries, calls Gemini API to enrich them, and yields them.
        """
        print(f"Executing LLMMetadataEnricherPlugin: Enriching with '{self.model_name}'...")

        for entry in entries:
            print(f"  Enriching entry: {entry.id[:10]}...")

            prompt = f"{self.prompt_template}\n\nContent:\n{entry.content}"

            try:
                response = self.model.generate_content(prompt)

                if not response.text:
                    logger.warning(f"Empty response from Gemini for entry {entry.id}")
                    yield entry
                    continue

                json_str = self._extract_json(response.text)
                if json_str:
                    try:
                        data = json.loads(json_str)
                        # Validate with Pydantic
                        enriched = EnrichmentSchema(**data)

                        # Update metadata
                        entry.metadata.update(enriched.model_dump())
                        print(f"    Successfully enriched entry {entry.id[:10]}")

                    except (json.JSONDecodeError, ValidationError) as e:
                        logger.error(f"Failed to parse or validate LLM response: {e}")
                else:
                    logger.warning(f"No JSON found in LLM response for entry {entry.id}")

            except Exception as e:
                logger.error(f"Gemini API error for entry {entry.id}: {e}")

            yield entry
