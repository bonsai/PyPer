"""
Imagen KAIKAI Gallery - Publish Plugin

Creates contact sheets from generated images and manages selection.
"""
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Iterator

from ..base import Entry, PublishPlugin

logger = logging.getLogger(__name__)


class Plugin(PublishPlugin):
    """
    A publish plugin that creates contact sheets from generated images
    and manages selected images.
    """

    @property
    def name(self) -> str:
        return "Publish::Imagen::Gallery"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.input_dir = self.config.get("input_dir", "data/imagen_output")
        self.output_dir = self.config.get("output_dir", "data/imagen_selected")
        self.columns = self.config.get("columns", 5)
        self.select = self.config.get("select", [])  # List of indices to select
        self.contact_sheet_name = self.config.get("contact_sheet_name", "contact_sheet")

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def _create_contact_sheet(self, images: list) -> str:
        """Create a matplotlib contact sheet from images."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.image as mpimg
            import math

            if not images:
                return None

            num_images = len(images)
            rows = math.ceil(num_images / self.columns)
            fig, axes = plt.subplots(rows, self.columns, figsize=(self.columns * 3, rows * 3))

            if rows == 1 and self.columns == 1:
                axes = [axes]
            elif rows == 1:
                axes = list(axes)
            else:
                axes = axes.flatten()

            for i, img_path in enumerate(images):
                if i < len(axes):
                    try:
                        img = mpimg.imread(img_path)
                        axes[i].imshow(img)
                        axes[i].axis("off")
                        axes[i].set_title(f"#{i+1}", fontsize=10)
                    except Exception as e:
                        axes[i].text(0.5, 0.5, f"Error\n{e}", ha="center", va="center", fontsize=10)
                        axes[i].axis("off")

            for i in range(len(images), len(axes)):
                axes[i].axis("off")

            plt.tight_layout()
            contact_path = Path(self.input_dir) / f"{self.contact_sheet_name}.png"
            plt.savefig(contact_path, dpi=150, bbox_inches="tight")
            plt.close()

            return str(contact_path)
        except ImportError:
            logger.error("matplotlib not installed. Install with: pip install matplotlib")
            return None

    def execute(self, entries: Iterator[Entry]):
        """
        Receives entries with image paths, creates contact sheet, copies selected.
        """
        entries_list = list(entries)
        images = []

        for entry in entries_list:
            img_path = entry.metadata.get("image_path")
            if img_path and Path(img_path).exists():
                images.append(img_path)

        if not images:
            print("[Gallery] No images found to process")
            return

        print(f"[Gallery] Creating contact sheet with {len(images)} image(s)...")

        # Create contact sheet
        contact_path = self._create_contact_sheet(images)
        if contact_path:
            print(f" ✓ Contact sheet saved: {contact_path}")

        # Copy selected images
        if self.select:
            print(f"[Gallery] Selecting {len(self.select)} image(s)...")
            selected_dir = Path(self.output_dir)
            selected_dir.mkdir(parents=True, exist_ok=True)

            for idx in self.select:
                idx = int(idx) - 1  # 1-indexed
                if 0 <= idx < len(images):
                    src = Path(images[idx])
                    dst = selected_dir / src.name
                    shutil.copy2(src, dst)
                    print(f"  ✓ Selected: {src.name}")

            print(f" ✓ {len(self.select)} image(s) copied to {self.output_dir}")
        else:
            print(f"  No selection specified. All {len(images)} images available.")

        print(f" ✓ Gallery processing complete")
