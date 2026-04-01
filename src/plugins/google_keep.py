# src/plugins/google_keep.py

import os
import json
import hashlib
from typing import Dict, Any, Iterator, Optional

from .base import Entry, SubscriptionPlugin

class Plugin(SubscriptionPlugin):
    """
    A subscription plugin to fetch data from Google Keep Takeout JSON files.
    It extracts content and rich metadata for later retrieval.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.source_path = self.config.get("path")
        if not self.source_path:
            raise ValueError("Config for GoogleKeep plugin must contain a 'path'.")

    def _describe_image_with_gemini(self, image_path: str) -> Optional[str]:
        """
        [MOCK] Describes the content of an image using a multimodal model.
        In a real implementation, this would call the Vertex AI Gemini API.
        """
        print(f"  [Gemini MOCK] Describing image at: {image_path}")
        # This is a placeholder response.
        return f"This is a mock description for the image '{os.path.basename(image_path)}'."

    def execute(self) -> Iterator[Entry]:
        """
        Reads JSON files from the specified Google Keep takeout directory,
        parses them, extracts metadata, and yields them as Entry objects.
        """
        print(f"Executing GoogleKeepPlugin: Reading from '{self.source_path}'...")

        if not os.path.isdir(self.source_path):
            print(f"Warning: Directory not found: {self.source_path}. Skipping.")
            return

        for filename in os.listdir(self.source_path):
            if not filename.endswith('.json'):
                continue

            file_path = os.path.join(self.source_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                content = data.get('textContent', '')
                title = data.get('title', '')
                if title:
                    content = f"{title}\\n\\n{content}" # Prepend title to content

                # Use a hash of the filename as a stable ID
                entry_id = hashlib.sha256(filename.encode()).hexdigest()

                # Extract desired metadata
                metadata = {
                    "created_timestamp_usec": data.get("createdTimestampUsec"),
                    "is_archived": data.get("isArchived", False),
                    "color": data.get("color", "DEFAULT").lower(),
                    "source_file": filename,
                }

                # Check for image attachments and get descriptions
                image_descriptions = []
                if 'attachments' in data:
                    for attachment in data['attachments']:
                        if attachment.get('mimetype', '').startswith('image/'):
                            # In a real scenario, we might need a full path
                            image_path = attachment.get('filePath')
                            description = self._describe_image_with_gemini(image_path)
                            if description:
                                image_descriptions.append(description)

                if image_descriptions:
                    metadata["image_content_description"] = "\\n".join(image_descriptions)

                yield Entry(
                    id=entry_id,
                    source=self.name,
                    content=content.strip(),
                    timestamp=int(data.get("createdTimestampUsec", 0) / 1000), # to millis
                    metadata=metadata,
                )

            except (IOError, json.JSONDecodeError) as e:
                print(f"Error reading or parsing {file_path}: {e}")
                continue
