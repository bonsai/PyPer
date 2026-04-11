#!/usr/bin/env python3
"""
Model Downloader for ComfyUI
Downloads base models, LoRAs, ControlNets, and other assets.
"""

import os
import subprocess
from pathlib import Path


# Model directories
CKPT_DIR = "/content/ComfyUI/models/checkpoints"
LORA_DIR = "/content/ComfyUI/models/loras"
VAE_DIR = "/content/ComfyUI/models/vae"
CN_DIR = "/content/ComfyUI/models/controlnet"
UPSCALE_DIR = "/content/ComfyUI/models/upscale_models"


def ensure_dirs():
    """Create model directories if they don't exist."""
    for dir_path in [CKPT_DIR, LORA_DIR, VAE_DIR, CN_DIR, UPSCALE_DIR]:
        os.makedirs(dir_path, exist_ok=True)


def download_file(url: str, output_path: str, description: str):
    """Download a file with progress display."""
    print(f"\n📥 Downloading {description}...")
    cmd = f'wget -q --show-progress -O "{output_path}" "{url}"'
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print(f"   ✅ {description} complete")
        return True
    else:
        print(f"   ❌ {description} failed")
        return False


def download_base_models(
    animagine: bool = True,
    pony: bool = False,
    sdxl_base: bool = True,
    juggernaut: bool = False
):
    """Download base checkpoint models."""
    
    models = {
        'animagine': {
            'url': 'https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors',
            'name': 'animagine-xl-3.1.safetensors',
            'enabled': animagine
        },
        'pony': {
            'url': 'https://huggingface.co/AstraliteHeart/pony-diffusion-v6/resolve/main/v6.safetensors',
            'name': 'ponyDiffusionV6XL.safetensors',
            'enabled': pony
        },
        'sdxl_base': {
            'url': 'https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors',
            'name': 'sd_xl_base_1.0.safetensors',
            'enabled': sdxl_base
        },
        'juggernaut': {
            'url': 'https://huggingface.co/RunDiffusion/Juggernaut-XL-v9/resolve/main/Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors',
            'name': 'juggernautXL_v9.safetensors',
            'enabled': juggernaut
        }
    }
    
    for key, model in models.items():
        if model['enabled']:
            output_path = os.path.join(CKPT_DIR, model['name'])
            if not os.path.exists(output_path):
                download_file(model['url'], output_path, model['name'])
            else:
                print(f"   ⏭️  {model['name']} already exists, skipping")


def download_controlnet():
    """Download ControlNet models for SDXL."""
    print("\n📥 Downloading ControlNet models...")
    
    models = [
        {
            'url': 'https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors',
            'name': 'diffusers_xl_depth_full.safetensors'
        },
        {
            'url': 'https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors',
            'name': 'diffusers_xl_canny_full.safetensors'
        }
    ]
    
    for model in models:
        output_path = os.path.join(CN_DIR, model['name'])
        if not os.path.exists(output_path):
            download_file(model['url'], output_path, model['name'])
        else:
            print(f"   ⏭️  {model['name']} already exists, skipping")


def download_upscaler():
    """Download upscaling models."""
    print("\n📥 Downloading Upscaler models...")
    
    models = [
        {
            'url': 'https://huggingface.co/uwg/upscaler/resolve/main/ESRGAN/4x-UltraSharp.pth',
            'name': '4x-UltraSharp.pth'
        }
    ]
    
    for model in models:
        output_path = os.path.join(UPSCALE_DIR, model['name'])
        if not os.path.exists(output_path):
            download_file(model['url'], output_path, model['name'])
        else:
            print(f"   ⏭️  {model['name']} already exists, skipping")


def download_vae():
    """Download VAE models."""
    print("\n📥 Downloading VAE models...")
    
    models = [
        {
            'url': 'https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors',
            'name': 'sdxl_vae.safetensors'
        }
    ]
    
    for model in models:
        output_path = os.path.join(VAE_DIR, model['name'])
        if not os.path.exists(output_path):
            download_file(model['url'], output_path, model['name'])
        else:
            print(f"   ⏭️  {model['name']} already exists, skipping")


def download_lora():
    """Download LoRA models for style enhancement."""
    print("\n📥 Downloading LoRA models...")
    
    models = [
        {
            'url': 'https://civitai.com/api/download/models/198246',
            'name': 'flat_color_style_xl.safetensors'
        }
    ]
    
    for model in models:
        output_path = os.path.join(LORA_DIR, model['name'])
        if not os.path.exists(output_path):
            download_file(model['url'], output_path, model['name'])
        else:
            print(f"   ⏭️  {model['name']} already exists, skipping")


def list_models():
    """List all downloaded models with sizes."""
    print("\n" + "="*50)
    print("📁 Downloaded Models Summary")
    print("="*50)
    
    dir_names = [
        ("Checkpoints", CKPT_DIR),
        ("LoRA", LORA_DIR),
        ("VAE", VAE_DIR),
        ("ControlNet", CN_DIR),
        ("Upscaler", UPSCALE_DIR)
    ]
    
    for name, path in dir_names:
        if os.path.exists(path):
            files = os.listdir(path)
            if files:
                print(f"\n📂 {name}:")
                for f in sorted(files):
                    file_path = os.path.join(path, f)
                    size_gb = os.path.getsize(file_path) / (1024**3)
                    print(f"   ✅ {f} ({size_gb:.2f} GB)")


def main():
    """Main download routine."""
    print("🚀 Starting Model Download for Kaikai Character Generator")
    
    ensure_dirs()
    
    # Download base models (customize these flags)
    download_base_models(
        animagine=True,
        pony=False,
        sdxl_base=True,
        juggernaut=False
    )
    
    # Download additional models
    download_controlnet()
    download_upscaler()
    download_vae()
    download_lora()
    
    # Show summary
    list_models()
    
    print("\n" + "="*50)
    print("✅ All model downloads complete!")
    print("="*50)


if __name__ == '__main__':
    main()
