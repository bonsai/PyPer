#!/usr/bin/env python3
"""
Character Generation Script for ComfyUI
Generates Kaikai Kiki-style characters via ComfyUI API.
"""

import json
import urllib.request
import urllib.parse
import random
import os
import time
from pathlib import Path


# ComfyUI API endpoint
COMFYUI_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = "/content/generated_characters"


# Character prompt definitions
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


def create_workflow(
    prompt: str,
    negative: str,
    seed: int,
    model: str,
    steps: int = 35,
    cfg: float = 7.5,
    width: int = 1024,
    height: int = 1024
) -> dict:
    """Create ComfyUI API workflow format."""
    
    workflow = {
        "3": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": model
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": negative,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": f"character_{seed}",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }
    return workflow


def queue_prompt(workflow: dict) -> dict:
    """Submit workflow to ComfyUI API."""
    data = json.dumps({"prompt": workflow}).encode('utf-8')
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    response = urllib.request.urlopen(req)
    return json.loads(response.read())


def get_history(prompt_id: str) -> dict:
    """Get generation history from ComfyUI."""
    with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as response:
        return json.loads(response.read())


def get_image(filename: str, subfolder: str, folder_type: str) -> bytes:
    """Download generated image from ComfyUI."""
    params = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": subfolder,
        "type": folder_type
    })
    with urllib.request.urlopen(f"{COMFYUI_URL}/view?{params}") as response:
        return response.read()


def generate_characters(
    character_type: str = "architectural_spirit",
    model_name: str = "animagine-xl-3.1.safetensors",
    num_images: int = 10,
    steps: int = 35,
    cfg_scale: float = 7.5,
    width: int = 1024,
    height: int = 1024,
    use_random_seed: bool = True,
    fixed_seed: int = 12345,
    output_dir: str = None
):
    """Generate character images in batch."""
    
    if output_dir is None:
        output_dir = OUTPUT_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    prompts = CHARACTER_PROMPTS.get(character_type)
    if not prompts:
        print(f"❌ Unknown character type: {character_type}")
        return
    
    print(f"🎨 Character Type: {character_type}")
    print(f"📦 Model: {model_name}")
    print(f"🔢 Images: {num_images}")
    print(f"⚙️ Steps: {steps} / CFG: {cfg_scale}")
    print(f"📐 Size: {width}x{height}")
    print("="*50)
    
    generation_log = []
    
    for i in range(num_images):
        seed = random.randint(1, 2**32) if use_random_seed else fixed_seed + i
        
        print(f"\n🖼️ Generating... ({i+1}/{num_images}) Seed: {seed}")
        
        workflow = create_workflow(
            prompt=prompts["positive"],
            negative=prompts["negative"],
            seed=seed,
            model=model_name,
            steps=steps,
            cfg=cfg_scale,
            width=width,
            height=height
        )
        
        try:
            result = queue_prompt(workflow)
            prompt_id = result['prompt_id']
            
            # Wait for completion
            while True:
                time.sleep(2)
                history = get_history(prompt_id)
                if prompt_id in history:
                    break
            
            # Save images
            outputs = history[prompt_id]['outputs']
            save_path = None
            
            for node_id in outputs:
                if 'images' in outputs[node_id]:
                    for img_info in outputs[node_id]['images']:
                        img_data = get_image(
                            img_info['filename'],
                            img_info['subfolder'],
                            img_info['type']
                        )
                        
                        save_path = os.path.join(
                            output_dir,
                            f"{character_type}_seed{seed}.png"
                        )
                        with open(save_path, 'wb') as f:
                            f.write(img_data)
                        
                        print(f"   ✅ Saved: {save_path}")
            
            # Log generation
            generation_log.append({
                "index": i + 1,
                "seed": seed,
                "character_type": character_type,
                "model": model_name,
                "steps": steps,
                "cfg": cfg_scale,
                "size": f"{width}x{height}",
                "file": save_path
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Save generation log
    log_path = os.path.join(output_dir, "generation_log.json")
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(generation_log, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*50)
    print(f"✅ Generated {num_images} images!")
    print(f"📁 Output: {output_dir}")
    print(f"📋 Log: {log_path}")
    print("="*50)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Kaikai Kiki-style characters')
    parser.add_argument('--type', type=str, default='architectural_spirit',
                       choices=['architectural_spirit', 'flower_spirit', 'eye_creature'],
                       help='Character type')
    parser.add_argument('--model', type=str, default='animagine-xl-3.1.safetensors',
                       help='Base model name')
    parser.add_argument('--num', type=int, default=10, help='Number of images')
    parser.add_argument('--steps', type=int, default=35, help='Sampling steps')
    parser.add_argument('--cfg', type=float, default=7.5, help='CFG scale')
    parser.add_argument('--width', type=int, default=1024, help='Image width')
    parser.add_argument('--height', type=int, default=1024, help='Image height')
    parser.add_argument('--seed', type=int, default=None, help='Fixed seed (optional)')
    parser.add_argument('--output', type=str, default=None, help='Output directory')
    
    args = parser.parse_args()
    
    generate_characters(
        character_type=args.type,
        model_name=args.model,
        num_images=args.num,
        steps=args.steps,
        cfg_scale=args.cfg,
        width=args.width,
        height=args.height,
        use_random_seed=(args.seed is None),
        fixed_seed=args.seed or 12345,
        output_dir=args.output
    )


if __name__ == '__main__':
    main()
