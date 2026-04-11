# Google Colab Setup Guide

## Complete ComfyUI Setup for Kaikai Character Generation

This guide walks you through setting up ComfyUI on Google Colab for generating Kaikai Kiki-style characters.

---

## 📋 Prerequisites

- Google account with Google Drive
- Understanding of Colab runtime limits (typically 12 hours for free tier)
- ~30GB free space in Google Drive for models

---

## 🔧 Step-by-Step Setup

### Cell ①: Environment Setup

```python
#@title 🚀 ComfyUI Setup (Run Once)
#@markdown ### GPU Check → ComfyUI Install → Model Download

import subprocess, os

# --- GPU Check ---
print("=" * 50)
print("🖥️ GPU Information")
print("=" * 50)
!nvidia-smi

# --- Mount Google Drive ---
from google.colab import drive
drive.mount('/content/drive')

# --- Install ComfyUI ---
%cd /content
!git clone https://github.com/comfyanonymous/ComfyUI.git
%cd /content/ComfyUI
!pip install -r requirements.txt
!pip install -q xformers

# --- Install Custom Nodes ---
%cd /content/ComfyUI/custom_nodes

# ComfyUI Manager
!git clone https://github.com/ltdrdata/ComfyUI-Manager.git

# ControlNet Preprocessor
!git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git
%cd comfyui_controlnet_aux
!pip install -r requirements.txt
%cd ..

# IP-Adapter
!git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git

# Impact Pack
!git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack.git

print("\n" + "=" * 50)
print("✅ ComfyUI Installation Complete!")
print("=" * 50)
```

**Expected Time:** ~5 minutes

---

### Cell ②: Model Download

```python
#@title 📦 Model Download
#@markdown ### Select models to download

import os

# Model directories
CKPT_DIR = "/content/ComfyUI/models/checkpoints"
LORA_DIR = "/content/ComfyUI/models/loras"
VAE_DIR = "/content/ComfyUI/models/vae"
CN_DIR = "/content/ComfyUI/models/controlnet"
UPSCALE_DIR = "/content/ComfyUI/models/upscale_models"

os.makedirs(CKPT_DIR, exist_ok=True)
os.makedirs(LORA_DIR, exist_ok=True)
os.makedirs(VAE_DIR, exist_ok=True)
os.makedirs(CN_DIR, exist_ok=True)
os.makedirs(UPSCALE_DIR, exist_ok=True)

#@markdown ---
#@markdown ### Base Models
download_animagine = True  #@param {type:"boolean"}
download_pony = False  #@param {type:"boolean"}
download_sdxl_base = True  #@param {type:"boolean"}

#@markdown ### Additional Models
download_controlnet = True  #@param {type:"boolean"}
download_upscaler = True  #@param {type:"boolean"}
download_vae = True  #@param {type:"boolean"}
download_lora_flat_color = True  #@param {type:"boolean"}

# === Download Functions ===

if download_animagine:
    print("📥 Animagine XL 3.1...")
    !wget -q --show-progress -O {CKPT_DIR}/animagine-xl-3.1.safetensors \
        "https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors"
    print("✅ Animagine XL 3.1 Complete")

if download_sdxl_base:
    print("📥 SDXL Base 1.0...")
    !wget -q --show-progress -O {CKPT_DIR}/sd_xl_base_1.0.safetensors \
        "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"
    print("✅ SDXL Base 1.0 Complete")

if download_controlnet:
    print("\n📥 ControlNet Models...")
    !wget -q --show-progress -O {CN_DIR}/diffusers_xl_depth_full.safetensors \
        "https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors"
    !wget -q --show-progress -O {CN_DIR}/diffusers_xl_canny_full.safetensors \
        "https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors"
    print("✅ ControlNet Complete")

if download_upscaler:
    print("\n📥 Upscaler...")
    !wget -q --show-progress -O {UPSCALE_DIR}/4x-UltraSharp.pth \
        "https://huggingface.co/uwg/upscaler/resolve/main/ESRGAN/4x-UltraSharp.pth"
    print("✅ Upscaler Complete")

if download_vae:
    print("\n📥 VAE...")
    !wget -q --show-progress -O {VAE_DIR}/sdxl_vae.safetensors \
        "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors"
    print("✅ VAE Complete")

if download_lora_flat_color:
    print("\n📥 Flat Color LoRA...")
    !wget -q --show-progress -O {LORA_DIR}/flat_color_style_xl.safetensors \
        "https://civitai.com/api/download/models/198246"
    print("✅ LoRA Complete")

# === Summary ===
print("\n" + "=" * 50)
print("📁 Downloaded Models")
print("=" * 50)

for name, path in [("Checkpoints", CKPT_DIR), ("LoRA", LORA_DIR), 
                    ("VAE", VAE_DIR), ("ControlNet", CN_DIR),
                    ("Upscaler", UPSCALE_DIR)]:
    files = os.listdir(path)
    if files:
        print(f"\n📂 {name}:")
        for f in files:
            size = os.path.getsize(os.path.join(path, f)) / (1024**3)
            print(f"   ✅ {f} ({size:.2f} GB)")
```

**Expected Time:** ~10-30 minutes depending on selected models

---

### Cell ③: Start ComfyUI Server

```python
#@title 🟢 Start ComfyUI
#@markdown ### Access via cloudflared tunnel

import subprocess
import threading
import time

# Install cloudflared
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
!dpkg -i cloudflared-linux-amd64.deb

# Start tunnel in background
def run_tunnel():
    subprocess.run([
        "cloudflared", "tunnel", "--url", "http://127.0.0.1:8188"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

tunnel_thread = threading.Thread(target=run_tunnel, daemon=True)
tunnel_thread.start()

time.sleep(3)
print("=" * 50)
print("🌐 Click the URL shown above to access ComfyUI")
print("   (https://xxxxx.trycloudflare.com)")
print("=" * 50)

# Start ComfyUI
%cd /content/ComfyUI
!python main.py --listen 0.0.0.0 --port 8188
```

**Expected Time:** ~1 minute to start, then keeps running

---

### Cell ④: Batch Character Generation

```python
#@title 🎨 Auto-Generate Characters (API Mode)
#@markdown ### Generate via ComfyUI API

import json
import urllib.request
import urllib.parse
import random
import os
import time
from PIL import Image
from io import BytesIO

COMFYUI_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = "/content/generated_characters"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Character prompts
CHARACTER_PROMPTS = {
    "architectural_spirit": {
        "positive": """masterpiece, best quality, high detail,
character design sheet, single character, centered,
cute creature with building-shaped body,
tower-like form with multiple window-eyes,
flowers blooming from the top of head,
colorful facade patterns on body,
flat color style, bold black outlines,
pop art aesthetic, superflat inspired,
vibrant rainbow colors, high saturation,
kawaii but slightly eerie expression,
simple white background,
2d illustration, vector-like clean lines,
contemporary art style, sharp details""",
        "negative": """realistic, photograph, 3d render,
low quality, worst quality, blurry, dark, muted colors,
complex background, gradient shading,
western comic style, sketchy lines,
watermark, text, signature, bad anatomy, deformed,
multiple characters, cropped"""
    },
    "flower_spirit": {
        "positive": """masterpiece, best quality, high detail,
character design, single character, centered,
cute spirit born from colorful flowers,
flower petals forming body and hair,
large expressive eyes, mysterious smile,
body covered in floral patterns,
rainbow gradient coloring,
flat color style, bold outlines,
pop art kawaii aesthetic,
superflat contemporary art style,
vibrant neon colors, high contrast,
simple white background,
2d illustration, clean vector lines""",
        "negative": """realistic, photograph, 3d render,
low quality, worst quality, blurry, dark, muted colors,
complex background, western comic style,
watermark, text, signature, bad anatomy, deformed"""
    },
    "eye_creature": {
        "positive": """masterpiece, best quality, high detail,
character design, single character, centered,
round cute creature with multiple colorful eyes,
tentacle-like cute arms,
psychedelic rainbow coloring,
repeating eye pattern decoration,
flat color style, bold black outlines,
pop art kawaii but creepy aesthetic,
superflat contemporary art,
vibrant fluorescent colors,
simple white background,
2d illustration, vector style, clean lines""",
        "negative": """realistic, photograph, 3d render,
low quality, worst quality, blurry, dark, muted colors,
complex background, horror, scary, gore,
watermark, text, signature, bad anatomy, deformed"""
    }
}

def create_workflow(prompt, negative, seed, model, steps=35, cfg=7.5, width=1024, height=1024):
    workflow = {
        "3": {"inputs": {"seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "dpmpp_2m", 
                        "scheduler": "karras", "denoise": 1.0, "model": ["4", 0], 
                        "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}, 
              "class_type": "KSampler"},
        "4": {"inputs": {"ckpt_name": model}, "class_type": "CheckpointLoaderSimple"},
        "5": {"inputs": {"width": width, "height": height, "batch_size": 1}, 
              "class_type": "EmptyLatentImage"},
        "6": {"inputs": {"text": prompt, "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "7": {"inputs": {"text": negative, "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
        "9": {"inputs": {"filename_prefix": f"character_{seed}", "images": ["8", 0]}, 
              "class_type": "SaveImage"}
    }
    return workflow

def queue_prompt(workflow):
    data = json.dumps({"prompt": workflow}).encode('utf-8')
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data, 
                                  headers={'Content-Type': 'application/json'})
    response = urllib.request.urlopen(req)
    return json.loads(response.read())

def get_history(prompt_id):
    with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as response:
        return json.loads(response.read())

def get_image(filename, subfolder, folder_type):
    params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
    with urllib.request.urlopen(f"{COMFYUI_URL}/view?{params}") as response:
        return response.read()

# === Generation Settings ===
character_type = "architectural_spirit"  #@param ["architectural_spirit", "flower_spirit", "eye_creature"]
model_name = "animagine-xl-3.1.safetensors"  #@param ["animagine-xl-3.1.safetensors", "sd_xl_base_1.0.safetensors"]
num_images = 10  #@param {type:"slider", min:1, max:30, step:1}
steps = 35  #@param {type:"slider", min:20, max:50, step:5}
cfg_scale = 7.5  #@param {type:"slider", min:5, max:12, step:0.5}
width = 1024  #@param [832, 1024, 1152]
height = 1024  #@param [832, 1024, 1152, 1216]
use_random_seed = True  #@param {type:"boolean"}
fixed_seed = 12345  #@param {type:"integer"}

prompts = CHARACTER_PROMPTS[character_type]

print(f"🎨 Type: {character_type}")
print(f"📦 Model: {model_name}")
print(f"🔢 Count: {num_images}")
print(f"⚙️ Steps: {steps} / CFG: {cfg_scale}")
print(f"📐 Size: {width}x{height}")
print("=" * 50)

generation_log = []

for i in range(num_images):
    seed = random.randint(1, 2**32) if use_random_seed else fixed_seed + i
    print(f"\n🖼️ Generating... ({i+1}/{num_images}) Seed: {seed}")
    
    workflow = create_workflow(prompts["positive"], prompts["negative"], seed, model_name, 
                               steps, cfg_scale, width, height)
    
    try:
        result = queue_prompt(workflow)
        prompt_id = result['prompt_id']
        
        while True:
            time.sleep(2)
            history = get_history(prompt_id)
            if prompt_id in history:
                break
        
        outputs = history[prompt_id]['outputs']
        save_path = None
        for node_id in outputs:
            if 'images' in outputs[node_id]:
                for img_info in outputs[node_id]['images']:
                    img_data = get_image(img_info['filename'], img_info['subfolder'], img_info['type'])
                    save_path = os.path.join(OUTPUT_DIR, f"{character_type}_seed{seed}.png")
                    with open(save_path, 'wb') as f:
                        f.write(img_data)
                    print(f"   ✅ Saved: {save_path}")
        
        generation_log.append({"index": i+1, "seed": seed, "character_type": character_type, 
                               "model": model_name, "file": save_path})
    except Exception as e:
        print(f"   ❌ Error: {e}")

log_path = os.path.join(OUTPUT_DIR, "generation_log.json")
with open(log_path, 'w', encoding='utf-8') as f:
    json.dump(generation_log, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 50)
print(f"✅ Generated {num_images} images!")
print(f"📁 Output: {OUTPUT_DIR}")
print("=" * 50)
```

**Expected Time:** ~5-15 minutes for 10 images

---

### Cell ⑤: Gallery View & Selection

```python
#@title 🖼️ Gallery View + Selection

import glob
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib
import shutil
import os

matplotlib.rcParams['font.family'] = 'DejaVu Sans'

OUTPUT_DIR = "/content/generated_characters"
SELECTED_DIR = "/content/selected_characters"
os.makedirs(SELECTED_DIR, exist_ok=True)

images = sorted(glob.glob(f"{OUTPUT_DIR}/*.png"))

if not images:
    print("❌ No images found")
else:
    # Create contact sheet
    cols = 5
    rows = (len(images) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(20, 4 * rows))
    
    if rows == 1:
        axes = [axes]
    
    for idx, img_path in enumerate(images):
        row = idx // cols
        col = idx % cols
        img = Image.open(img_path)
        ax = axes[row][col] if rows > 1 else axes[col]
        ax.imshow(img)
        fname = os.path.basename(img_path)
        ax.set_title(f"#{idx+1}\n{fname}", fontsize=8)
        ax.axis('off')
    
    for idx in range(len(images), rows * cols):
        row = idx // cols
        col = idx % cols
        ax = axes[row][col] if rows > 1 else axes[col]
        ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/contact_sheet.png", dpi=150, bbox_inches='tight')
    plt.show()
    
    print(f"\n📊 Total: {len(images)} images")
    print("=" * 50)

# --- Selection ---
selected_numbers = "1,5,8"  #@param {type:"string"}
selected = [int(n.strip()) - 1 for n in selected_numbers.split(",")]

print("\n🏆 Selected:")
for idx in selected:
    if 0 <= idx < len(images):
        src = images[idx]
        dst = os.path.join(SELECTED_DIR, os.path.basename(src))
        shutil.copy2(src, dst)
        print(f"   ✅ #{idx+1}: {os.path.basename(src)}")

print(f"\n📁 Saved to: {SELECTED_DIR}")
```

**Expected Time:** ~30 seconds

---

## 💡 Tips

1. **Save your Colab** before starting - runtime can disconnect
2. **Download models once** - they persist in Google Drive
3. **Use Animagine XL 3.1** for best kawaii/anime results
4. **Generate 20-30 images** per type for good variety
5. **Keep the workflow JSON** for consistent results

---

## ⚠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| GPU not available | Switch runtime to GPU (Runtime → Change runtime type) |
| Model download fails | Check HuggingFace/Civitai URLs, try again |
| ComfyUI won't start | Re-run cell ①, check for errors |
| API connection fails | Ensure ComfyUI is running (cell ③) |
| Images look wrong | Check prompt, try different seed |
