"""
Imagen KAIKAI Generate - Filter Plugin

Generates images from prompts using ComfyUI API.
"""
import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Iterator

import requests as http_requests

from ..base import Entry, FilterPlugin

logger = logging.getLogger(__name__)

# Character type prompts (from original kaikai)
CHARACTER_PROMPTS = {
    "architectural_spirit": {
        "positive": "building-shaped creature, window eyes, flower crown, pop art style, flat color, bold outlines, kawaii, superflat, vibrant colors, simple white background",
        "negative": "realistic, photo, 3d, shading, gradient, complex background, text, watermark",
    },
    "flower_spirit": {
        "positive": "spirit born from colorful flowers, rainbow gradient coloring, kawaii creature, flat color, bold outlines, superflat, vibrant colors, simple white background",
        "negative": "realistic, photo, 3d, shading, dark, complex background, text, watermark",
    },
    "eye_creature": {
        "positive": "round creature with multiple psychedelic eyes, tentacle arms, kawaii, flat color, bold outlines, superflat, vibrant colors, simple white background",
        "negative": "realistic, photo, 3d, horror, dark, complex background, text, watermark",
    },
}


class Plugin(FilterPlugin):
    """
    A filter plugin that generates images from entry prompts using ComfyUI.
    """

    @property
    def name(self) -> str:
        return "Filter::Imagen::KAIKAI"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.comfyui_url = self.config.get("comfyui_url", "http://127.0.0.1:8188")
        self.model = self.config.get("model", "animagine_xl3")
        self.char_type = self.config.get("char_type", "architectural_spirit")
        self.num_images = self.config.get("num", 5)
        self.steps = self.config.get("steps", 35)
        self.cfg = self.config.get("cfg", 7.5)
        self.seed = self.config.get("seed", -1)
        self.output_dir = self.config.get("output_dir", "data/imagen_output")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def _submit_workflow(self, prompt: str, seed: int) -> str:
        """Submit workflow to ComfyUI API and return generated image path."""
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": self.steps,
                    "cfg": self.cfg,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                }
            },
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": f"{self.model}.safetensors"}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": CHARACTER_PROMPTS[self.char_type]["negative"], "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "pyper_", "images": ["8", 0]}},
        }

        try:
            response = http_requests.post(
                f"{self.comfyui_url}/prompt",
                json=workflow,
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            prompt_id = result.get("prompt_id")

            # Poll for completion
            for _ in range(120):
                time.sleep(2)
                history_resp = http_requests.get(f"{self.comfyui_url}/history/{prompt_id}")
                history = history_resp.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    if outputs:
                        node_output = list(outputs.values())[0]
                        images = node_output.get("images", [])
                        if images:
                            img_info = images[0]
                            img_url = f"{self.comfyui_url}/view?filename={img_info['filename']}&subfolder={img_info.get('subfolder', '')}&type=output"
                            img_data = http_requests.get(img_url).content
                            img_path = Path(self.output_dir) / f"pyper_{seed}.png"
                            img_path.write_bytes(img_data)
                            return str(img_path)
        except Exception as e:
            logger.error(f"ComfyUI generation failed: {e}")
        return None

    def execute(self, entries: Iterator[Entry]) -> Iterator[Entry]:
        """
        Receives entries with prompts, generates images, and enriches metadata.
        """
        print(f"[KAIKAI Generate] Generating {self.num_images} image(s) per entry...")

        entries_list = list(entries)

        for entry in entries_list:
            prompt = entry.metadata.get("image_prompt", entry.content)

            # Use character type prompt if no specific prompt
            if self.char_type in CHARACTER_PROMPTS:
                full_prompt = CHARACTER_PROMPTS[self.char_type]["positive"]
                if prompt and prompt != entry.content:
                    full_prompt = f"{prompt}, {full_prompt}"
            else:
                full_prompt = prompt

            for i in range(self.num_images):
                seed = self.seed if self.seed >= 0 else int(hashlib.md5(f"{entry.id}{i}".encode()).hexdigest()[:8], 16)

                print(f"  Generating image {i+1}/{self.num_images} (seed: {seed})...")
                img_path = self._submit_workflow(full_prompt, seed)

                if img_path:
                    gen_entry_id = hashlib.sha256(f"{entry.id}_img{i}".encode()).hexdigest()
                    content = f"Generated: {Path(img_path).name}\nPrompt: {full_prompt[:100]}..."

                    metadata = {
                        **entry.metadata,
                        "image_path": img_path,
                        "image_filename": Path(img_path).name,
                        "prompt": full_prompt,
                        "seed": seed,
                        "model": self.model,
                        "char_type": self.char_type,
                        "source": "Imagen KAIKAI",
                        "timestamp": datetime.now().isoformat(),
                    }

                    yield Entry(
                        id=gen_entry_id,
                        source=self.name,
                        content=content,
                        timestamp=0,
                        metadata=metadata,
                    )
                else:
                    print(f"  ✗ Failed to generate image {i+1}")

        print(f" ✓ Generated images for {len(entries_list)} entry/entries")
