# Kaikai Kiki Character Generator

AI-powered character generation pipeline using ComfyUI on Google Colab, designed for creating Kaikai Kiki-style artwork (contemporary pop art with kawaii creatures).

## 📁 Project Structure

```
kaikai/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── config/
│   └── settings.yaml      # Model and generation settings
├── scripts/
│   ├── setup.py           # Environment setup script
│   ├── download_models.py # Model downloader
│   ├── generate.py        # Batch character generation
│   └── gallery.py         # Image viewer and selector
├── workflows/
│   └── character_gen.json # ComfyUI workflow template
├── docs/
│   └── colab_setup.md     # Google Colab setup guide
└── output/                # Generated images
```

## 🚀 Quick Start (Google Colab)

### Step 1: Open Google Colab
1. Go to [Google Colab](https://colab.research.google.com/)
2. Create a new notebook
3. Set runtime type to **GPU** (Runtime → Change runtime type → GPU)

### Step 2: Copy & Run Cells

Copy the following code blocks into separate cells:

| Cell | Purpose | Run Time |
|------|---------|----------|
| ① | Environment setup + ComfyUI installation | ~5 min |
| ② | Model download | ~10-30 min |
| ③ | Start ComfyUI server | ~1 min |
| ④ | Batch character generation | ~5-15 min |
| ⑤ | Gallery view + selection | ~30 sec |

### Step 3: Access ComfyUI
After running cell ③, click the cloudflare URL to open ComfyUI in your browser.

## 🎨 Character Types

| Type | Description |
|------|-------------|
| `architectural_spirit` | Building-shaped creature with window-eyes and flower crown |
| `flower_spirit` | Spirit born from colorful flowers with petal body |
| `eye_creature` | Round creature with multiple psychedelic eyes |

## 📦 Models

### Recommended Base Models
- **Animagine XL 3.1** - Best for anime/kawaii style (default)
- **SDXL Base 1.0** - General purpose
- **Pony Diffusion V6** - Alternative style

### Required Models
- Checkpoint (base model)
- VAE (variational autoencoder)
- ControlNet (optional, for pose/depth control)
- LoRA (optional, for style enhancement)

## ⚙️ Generation Settings

| Parameter | Recommended | Description |
|-----------|-------------|-------------|
| Steps | 35 | Higher = better quality, slower |
| CFG Scale | 7.5 | Prompt adherence strength |
| Resolution | 1024x1024 | SDXL native resolution |
| Sampler | DPM++ 2M Karras | Best quality/speed balance |

## 📝 Workflow API

The generation script uses ComfyUI's API format:

```json
{
  "3": {"class_type": "KSampler"},
  "4": {"class_type": "CheckpointLoaderSimple"},
  "5": {"class_type": "EmptyLatentImage"},
  "6": {"class_type": "CLIPTextEncode"},
  "7": {"class_type": "CLIPTextEncode"},
  "8": {"class_type": "VAEDecode"},
  "9": {"class_type": "SaveImage"}
}
```

## 🔧 Local Setup (Alternative)

If you want to run ComfyUI locally instead of Colab:

```bash
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install dependencies
pip install -r requirements.txt

# Install custom nodes
cd custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git

# Start server
python main.py
```

## 📊 Output Format

Generated files are saved as:
- `output/character_{seed}.png` - Generated images
- `output/generation_log.json` - Generation metadata
- `output/contact_sheet.png` - Preview grid
- `selected/` - Curated best images

## 🎯 Tips for Best Results

1. **Use Animagine XL 3.1** for kawaii/anime style
2. **Generate 20-30 images** per character type for good variety
3. **Adjust CFG 7-9** for stronger prompt adherence
4. **Use fixed seeds** to reproduce favorite results
5. **Check contact sheet** before selecting final images

## 📄 License

This project is for educational and personal art creation purposes.

## 🙏 Credits

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - Stable Diffusion GUI
- [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) - Node management
- [Animagine XL](https://huggingface.co/cagliostrolab/animagine-xl-3.1) - Base model
