"""
Imagen KAIKAI Setup - Subscription Plugin

Checks ComfyUI environment and downloads required models.
"""
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Iterator

from ..base import Entry, SubscriptionPlugin

logger = logging.getLogger(__name__)


class Plugin(SubscriptionPlugin):
    """
    A subscription plugin that sets up the KAIKAI (ComfyUI) environment.
    Yields setup status as Entry objects.
    """

    @property
    def name(self) -> str:
        return "Subscription::Imagen::KAIKAI"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.action = self.config.get("action", "check")  # check, setup, download
        self.comfyui_dir = self.config.get("comfyui_dir", str(Path.home() / "ComfyUI"))
        self.model_type = self.config.get("model_type", "animagine_xl3")
        self.output_dir = self.config.get("output_dir", "data/imagen_output")

    def _check_gpu(self) -> bool:
        """Check if GPU is available."""
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except:
            return False

    def _setup_comfyui(self) -> bool:
        """Setup ComfyUI environment."""
        comfyui_path = Path(self.comfyui_dir)
        if not comfyui_path.exists():
            print(f"  Cloning ComfyUI to {comfyui_dir}...")
            try:
                subprocess.run(
                    ["git", "clone", "https://github.com/comfyanonymous/ComfyUI.git", str(comfyui_path)],
                    check=True, timeout=300
                )
            except Exception as e:
                logger.error(f"Failed to clone ComfyUI: {e}")
                return False

        print(f"  Installing ComfyUI dependencies...")
        try:
            subprocess.run(
                ["pip", "install", "-r", str(comfyui_path / "requirements.txt")],
                check=True, timeout=300
            )
        except Exception as e:
            logger.error(f"Failed to install ComfyUI deps: {e}")
            return False

        return True

    def _download_models(self) -> bool:
        """Download required models."""
        models_dir = Path(self.comfyui_dir) / "models"
        checkpoints_dir = models_dir / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        model_urls = {
            "animagine_xl3": "https://civitai.com/api/download/models/animagine-xl-3.1",
            "sdxl_base": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0",
        }

        url = model_urls.get(self.model_type)
        if not url:
            print(f"  Unknown model type: {self.model_type}")
            return False

        output_path = checkpoints_dir / f"{self.model_type}.safetensors"
        if output_path.exists():
            print(f"  Model already exists: {output_path}")
            return True

        print(f"  Downloading {self.model_type}...")
        try:
            subprocess.run(
                ["curl", "-L", "-o", str(output_path), url],
                check=True, timeout=3600
            )
            return True
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            return False

    def execute(self) -> Iterator[Entry]:
        """
        Sets up the KAIKAI environment and yields status as Entry.
        """
        print(f"[KAIKAI Setup] Action: {self.action}")

        import hashlib
        from datetime import datetime

        if self.action in ("setup", "check"):
            gpu_ok = self._check_gpu()
            print(f"  GPU: {'✓' if gpu_ok else '✗'}")

            comfyui_exists = Path(self.comfyui_dir).exists()
            print(f"  ComfyUI: {'✓' if comfyui_exists else '✗'}")

            if self.action == "setup" and not comfyui_exists:
                setup_ok = self._setup_comfyui()
                print(f"  Setup: {'✓' if setup_ok else '✗'}")
            else:
                setup_ok = comfyui_exists

        if self.action == "download":
            download_ok = self._download_models()
            print(f"  Download: {'✓' if download_ok else '✗'}")
        else:
            download_ok = True

        entry_id = hashlib.sha256(f"kaikai_{self.action}".encode()).hexdigest()
        content = f"KAIKAI Setup Complete\nAction: {self.action}\nGPU: {'OK' if gpu_ok else 'NG'}\nModels: {'OK' if download_ok else 'NG'}"

        metadata = {
            "action": self.action,
            "gpu_available": gpu_ok if 'gpu_ok' in dir() else False,
            "comfyui_installed": setup_ok if 'setup_ok' in dir() else False,
            "models_downloaded": download_ok,
            "source": "Imagen KAIKAI",
            "timestamp": datetime.now().isoformat(),
        }

        yield Entry(
            id=entry_id,
            source=self.name,
            content=content,
            timestamp=0,
            metadata=metadata,
        )
