#!/usr/bin/env python3
"""
ComfyUI Setup Script for Google Colab and Local Environments
Initializes the environment and installs ComfyUI with custom nodes.
"""

import subprocess
import os
import sys
from pathlib import Path


# Base directory for local setups (parent dir of this script)
BASE_DIR = Path(__file__).resolve().parent.parent


def is_colab():
    """Check if the code is running in Google Colab."""
    return 'google.colab' in sys.modules or os.path.exists('/content')


def run_command(cmd, description):
    """Run a shell command with progress indication."""
    print(f"\n{'='*50}")
    print(f"🔧 {description}")
    print(f"{'='*50}")
    result = subprocess.run(cmd, shell=isinstance(cmd, str))
    return result.returncode == 0


def check_gpu():
    """Display GPU information."""
    print("\n" + "="*50)
    print("🖥️ GPU Information")
    print("="*50)
    subprocess.run("nvidia-smi", shell=True)


def mount_drive():
    """Mount Google Drive for model storage if in Colab."""
    if is_colab():
        print("\n📁 Mounting Google Drive...")
        from google.colab import drive
        drive.mount('/content/drive')
    else:
        print("\n📁 Skipping Google Drive mount (Running locally, not in Colab).")


def install_comfyui():
    """Install ComfyUI from GitHub."""
    target_dir = '/content' if is_colab() else str(BASE_DIR)
    os.chdir(target_dir)
    
    if not os.path.exists('ComfyUI'):
        run_command(
            'git clone https://github.com/comfyanonymous/ComfyUI.git',
            'Cloning ComfyUI repository'
        )
    
    comfy_dir = '/content/ComfyUI' if is_colab() else str(BASE_DIR / 'ComfyUI')
    os.chdir(comfy_dir)
    
    run_command('pip install -r requirements.txt', 'Installing ComfyUI dependencies')
    run_command('pip install -q xformers', 'Installing xformers optimization')


def install_custom_nodes():
    """Install essential custom nodes."""
    comfy_dir = '/content/ComfyUI' if is_colab() else str(BASE_DIR / 'ComfyUI')
    custom_nodes_dir = os.path.join(comfy_dir, 'custom_nodes')
    os.makedirs(custom_nodes_dir, exist_ok=True)
    os.chdir(custom_nodes_dir)
    
    nodes = [
        {
            'name': 'ComfyUI Manager',
            'url': 'https://github.com/ltdrdata/ComfyUI-Manager.git',
            'dir': 'ComfyUI-Manager',
            'requirements': False
        },
        {
            'name': 'ControlNet Aux',
            'url': 'https://github.com/Fannovel16/comfyui_controlnet_aux.git',
            'dir': 'comfyui_controlnet_aux',
            'requirements': True
        },
        {
            'name': 'IP Adapter Plus',
            'url': 'https://github.com/cubiq/ComfyUI_IPAdapter_plus.git',
            'dir': 'ComfyUI_IPAdapter_plus',
            'requirements': False
        },
        {
            'name': 'Impact Pack',
            'url': 'https://github.com/ltdrdata/ComfyUI-Impact-Pack.git',
            'dir': 'ComfyUI-Impact-Pack',
            'requirements': False
        }
    ]
    
    for node in nodes:
        if not os.path.exists(node['dir']):
            run_command(f"git clone {node['url']}", f"Installing {node['name']}")
            if node['requirements']:
                req_path = f"{node['dir']}/requirements.txt"
                if os.path.exists(req_path):
                    run_command(f"pip install -r {req_path}", f"Installing {node['name']} dependencies")


def main():
    """Main setup routine."""
    print("🚀 Starting ComfyUI Setup for Kaikai Character Generator")
    
    # Check GPU
    check_gpu()
    
    # Mount Drive
    mount_drive()
    
    # Install ComfyUI
    install_comfyui()
    
    # Install custom nodes
    install_custom_nodes()
    
    print("\n" + "="*50)
    print("✅ ComfyUI setup complete!")
    print("="*50)
    print("\nNext steps:")
    print("1. Run download_models.py to get required models")
    print("2. Run start_server.py to launch ComfyUI")


if __name__ == '__main__':
    main()
