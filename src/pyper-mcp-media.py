#!/usr/bin/env python3
"""
PyPer MCP Media Server

On-demand server for image/video/trend operations.
Start only when needed, exit after processing.

Tools:
  - imagen: kaikai_setup, kaikai_generate, kaikai_gallery
  - yupload: pdf_to_video, video_tool
  - popmov: trend_tracker, video_analyzer
"""
import sys
import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from plugins.mcp_base import MCPServer, MCPTool

# ========== Config ==========
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ========== Server ==========
server = MCPServer("pyper-media", "1.0.0")

# ========== Imagen Tools ==========
server.register_tool(
    name="imagen_kaikai_setup",
    description="Check/setup ComfyUI environment and download models",
    input_schema={
        "properties": {
            "action": {"type": "string", "enum": ["check", "setup", "download"], "default": "check"},
            "model_type": {"type": "string", "default": "animagine_xl3"},
        },
        "required": []
    },
    handler=lambda action="check", model_type="animagine_xl3": _kaikai_setup(action, model_type)
)

def _kaikai_setup(action, model_type):
    """Run KAIKAI setup plugin."""
    Plugin = _load("imagen", "kaikai_setup")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    plugin = Plugin({"action": action, "model_type": model_type})
    entries = list(plugin.execute())
    if entries:
        return entries[0].content
    return "No output"

server.register_tool(
    name="imagen_kaikai_generate",
    description="Generate character images using ComfyUI",
    input_schema={
        "properties": {
            "char_type": {"type": "string", "enum": ["architectural_spirit", "flower_spirit", "eye_creature"], "default": "architectural_spirit"},
            "num": {"type": "integer", "default": 5},
            "model": {"type": "string", "default": "animagine_xl3"},
            "steps": {"type": "integer", "default": 35},
            "cfg": {"type": "number", "default": 7.5},
            "prompt": {"type": "string", "description": "Custom prompt (optional)"},
        },
        "required": []
    },
    handler=lambda char_type="architectural_spirit", num=5, model="animagine_xl3", steps=35, cfg=7.5, prompt=None:
        _kaikai_generate(char_type, num, model, steps, cfg, prompt)
)

def _kaikai_generate(char_type, num, model, steps, cfg, prompt):
    """Run KAIKAI generate plugin."""
    Plugin = _load("imagen", "kaikai_generate")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    config = {
        "char_type": char_type, "num": num, "model": model,
        "steps": steps, "cfg": cfg,
        "output_dir": str(DATA_DIR / "imagen_output"),
    }
    plugin = Plugin(config)

    # Create a mock entry with prompt
    from plugins.base import Entry
    entry = Entry(
        id="mock", source="user",
        content=prompt or char_type,
        metadata={"image_prompt": prompt} if prompt else {}
    )
    entries = list(plugin.execute(iter([entry])))

    if not entries:
        return "No images generated"

    lines = [f"Generated {len(entries)} image(s):"]
    for i, e in enumerate(entries, 1):
        path = e.metadata.get("image_path", "")
        lines.append(f"{i}. {path}")
    return "\n".join(lines)

server.register_tool(
    name="imagen_kaikai_gallery",
    description="Create contact sheet and select images",
    input_schema={
        "properties": {
            "input_dir": {"type": "string", "default": "data/imagen_output"},
            "select": {"type": "array", "items": {"type": "string"}, "description": "Image indices to select (1-based)"},
            "columns": {"type": "integer", "default": 5},
        },
        "required": []
    },
    handler=lambda input_dir="data/imagen_output", select=None, columns=5:
        _kaikai_gallery(input_dir, select or [], columns)
)

def _kaikai_gallery(input_dir, select, columns):
    """Run KAIKAI gallery plugin."""
    Plugin = _load("imagen", "kaikai_gallery")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    from plugins.base import Entry
    config = {
        "input_dir": input_dir,
        "output_dir": str(DATA_DIR / "imagen_selected"),
        "select": select, "columns": columns,
    }
    plugin = Plugin(config)

    # Create mock entries from images in input_dir
    from pathlib import Path
    input_path = Path(input_dir) if os.path.isabs(input_dir) else ROOT_DIR / input_dir
    entries = []
    if input_path.exists():
        for img in input_path.glob("*.png"):
            entries.append(Entry(
                id=img.stem, source="gallery", content=str(img),
                metadata={"image_path": str(img)}
            ))

    plugin.execute(iter(entries))
    return f"Gallery processed. Output: {input_dir}"

# ========== YUpload Tools ==========
server.register_tool(
    name="yupload_pdf_to_video",
    description="Convert PDF entry to video script and metadata",
    input_schema={
        "properties": {
            "pdf_path": {"type": "string", "description": "Path to PDF file"},
            "target_duration": {"type": "integer", "default": 90},
            "tts_voice": {"type": "string", "default": "ja-JP-KeitaNeural"},
        },
        "required": ["pdf_path"]
    },
    handler=lambda pdf_path, target_duration=90, tts_voice="ja-JP-KeitaNeural":
        _pdf_to_video(pdf_path, target_duration, tts_voice)
)

def _pdf_to_video(pdf_path, target_duration, tts_voice):
    """Run PDF to Video plugin."""
    Plugin = _load("yupload", "pdf_to_video")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    from plugins.base import Entry
    config = {
        "target_duration": target_duration,
        "tts_voice": tts_voice,
        "output_dir": str(DATA_DIR / "yupload_output"),
    }
    plugin = Plugin(config)
    entry = Entry(
        id="pdf_input", source="user", content=pdf_path,
        metadata={"pdf_path": pdf_path}
    )
    entries = list(plugin.execute(iter([entry])))

    if not entries:
        return "No video script generated"

    e = entries[0]
    return f"{e.content}\nScript: {e.metadata.get('script_path', '')}"

server.register_tool(
    name="yupload_video_tool",
    description="Video creation tools (slideshow, long video, random concat)",
    input_schema={
        "properties": {
            "mode": {"type": "string", "enum": ["slideshow", "long_video", "random_concat"], "default": "slideshow"},
            "work_dir": {"type": "string", "description": "Working directory with materials"},
            "duration": {"type": "number", "default": 2.0},
            "target_mins": {"type": "integer", "default": 60},
        },
        "required": ["mode", "work_dir"]
    },
    handler=lambda mode, work_dir, duration=2.0, target_mins=60:
        _video_tool(mode, work_dir, duration, target_mins)
)

def _video_tool(mode, work_dir, duration, target_mins):
    """Run video tool."""
    return f"Video tool ({mode}) scheduled for: {work_dir}\nDuration: {duration}s per image, Target: {target_mins}min\n\nNote: Full implementation requires MoviePy and Tkinter."

# ========== PopMov Tools ==========
server.register_tool(
    name="popmov_trend_tracker",
    description="Track trending topics on platforms",
    input_schema={
        "properties": {
            "keyword": {"type": "string", "default": ""},
            "platform": {"type": "string", "default": "youtube"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": []
    },
    handler=lambda keyword="", platform="youtube", limit=10:
        _trend_tracker(keyword, platform, limit)
)

def _trend_tracker(keyword, platform, limit):
    """Run trend tracker plugin."""
    Plugin = _load("popmov", "trend_tracker")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    plugin = Plugin({
        "keyword": keyword, "platform": platform, "limit": limit,
        "state_file": str(DATA_DIR / "trend_state.txt"),
    })
    entries = list(plugin.execute())

    if not entries:
        return "No new trends found"

    lines = [f"Found {len(entries)} new trend(s):"]
    for i, e in enumerate(entries, 1):
        lines.append(f"{i}. {e.content}")
    return "\n".join(lines)

server.register_tool(
    name="popmov_video_analyzer",
    description="Analyze video metrics and enrichment",
    input_schema={
        "properties": {
            "entries_json": {"type": "string", "description": "Entries as JSON array"},
        },
        "required": ["entries_json"]
    },
    handler=lambda entries_json: _video_analyzer(json.loads(entries_json))
)

def _video_analyzer(entries_data):
    """Run video analyzer plugin."""
    Plugin = _load("popmov", "video_analyzer")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    from plugins.base import Entry
    entries = [Entry(**e) for e in entries_data]
    plugin = Plugin({})
    result_entries = list(plugin.execute(iter(entries)))

    lines = [f"Analyzed {len(result_entries)} video(s):"]
    for i, e in enumerate(result_entries, 1):
        score = e.metadata.get("performance_score", "N/A")
        rating = e.metadata.get("performance_rating", "N/A")
        lines.append(f"{i}. Score: {score}/10, Rating: {rating}")
    return "\n".join(lines)

# ========== Helpers ==========
def _load(category, name):
    """Load plugin class."""
    import importlib
    try:
        module_path = f"plugins.{category}.{name}"
        mod = importlib.import_module(module_path)
        return mod.Plugin
    except ImportError as e:
        return f"Import error: {e}"

# ========== Main ==========
GREETING = """
╔══════════════════════════════════════════════╗
║  PyPer MCP Media Server v1.0.0              ║
║  On-demand | Imagen + YUpload + PopMov      ║
╚══════════════════════════════════════════════╝
"""

def main():
    sys.stderr.write(GREETING + "\n")
    sys.stderr.flush()
    server.run()

if __name__ == "__main__":
    main()
