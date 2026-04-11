#!/usr/bin/env python3
"""
PyPer MCP Core Server

12 core tools for data pipeline operations.
Fast startup (<0.5s), always available.

Tools:
  - pipeline_list, pipeline_execute, pipeline_view, pipeline_create
  - subscribe_prtimes, subscribe_rss
  - publish_gmail, publish_twitter, publish_line_notify
  - state_view, state_clear, config_list
"""
import sys
import os
import json
import hashlib
import glob as globmod
from datetime import datetime
from pathlib import Path
from typing import Iterator, List

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from plugins.mcp_base import MCPServer
from plugins.base import Entry

# ========== Config ==========
ROOT_DIR = Path(__file__).resolve().parents[1]
RECIPE_DIR = ROOT_DIR / "recipe"
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config" / "envs"

# Ensure directories exist
RECIPE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ========== Helpers ==========
def load_plugin_module(category: str, name: str):
    """Dynamically load a plugin module."""
    import importlib
    try:
        module_path = f"plugins.{category}.{name}"
        mod = importlib.import_module(module_path)
        return mod.Plugin
    except ImportError as e:
        return f"Import error: {e}"

def run_pipeline_from_yaml(recipe_path: str):
    """Run a pipeline from YAML config (reuses main.py logic)."""
    import importlib
    main_mod = importlib.import_module("main")
    try:
        main_mod.run_pipeline(recipe_path)
        return f"Pipeline executed: {recipe_path}"
    except Exception as e:
        return f"Pipeline error: {str(e)}"

# ========== Server ==========
server = MCPServer("pyper-core", "1.0.0")

# ========== Pipeline Tools ==========
server.register_tool(
    name="pipeline_list",
    description="List all available pipeline recipes",
    input_schema={"properties": {}, "required": []},
    handler=lambda: "\n".join(
        f"- {p.stem}" for p in RECIPE_DIR.glob("*.yaml")
    ) or "No recipes found"
)

server.register_tool(
    name="pipeline_view",
    description="View the YAML content of a pipeline recipe",
    input_schema={
        "properties": {"recipe_name": {"type": "string", "description": "Recipe filename (without .yaml)"}},
        "required": ["recipe_name"]
    },
    handler=lambda recipe_name: (
        (RECIPE_DIR / f"{recipe_name}.yaml").read_text(encoding="utf-8")
        if (RECIPE_DIR / f"{recipe_name}.yaml").exists()
        else f"Recipe not found: {recipe_name}"
    )
)

server.register_tool(
    name="pipeline_execute",
    description="Execute a pipeline from a YAML recipe",
    input_schema={
        "properties": {"recipe_name": {"type": "string", "description": "Recipe filename (without .yaml)"}},
        "required": ["recipe_name"]
    },
    handler=lambda recipe_name: (
        run_pipeline_from_yaml(str(RECIPE_DIR / f"{recipe_name}.yaml"))
        if (RECIPE_DIR / f"{recipe_name}.yaml").exists()
        else f"Recipe not found: {recipe_name}"
    )
)

server.register_tool(
    name="pipeline_create",
    description="Create a new pipeline recipe from parameters",
    input_schema={
        "properties": {
            "recipe_name": {"type": "string", "description": "New recipe filename (without .yaml)"},
            "subscriptions": {"type": "array", "items": {"type": "string"}, "description": "Subscription plugins"},
            "filters": {"type": "array", "items": {"type": "string"}, "description": "Filter plugins"},
            "publishers": {"type": "array", "items": {"type": "string"}, "description": "Publish plugins"},
            "config": {"type": "object", "description": "Plugin configurations"}
        },
        "required": ["recipe_name"]
    },
    handler=lambda recipe_name, subscriptions=None, filters=None, publishers=None, config=None: _create_recipe(
        recipe_name, subscriptions or [], filters or [], publishers or [], config or {}
    )
)

def _create_recipe(name, subs, filters, pubs, config):
    """Create a YAML recipe file."""
    import yaml
    recipe = {
        "global": {"timezone": "Asia/Tokyo", "log_level": "info", "max_workers": 1},
        "plugins": []
    }
    for sub in subs:
        recipe["plugins"].append({"module": sub, "config": config.get(sub, {})})
    for f in filters:
        recipe["plugins"].append({"module": f, "config": config.get(f, {})})
    for pub in pubs:
        recipe["plugins"].append({"module": pub, "config": config.get(pub, {})})

    path = RECIPE_DIR / f"{name}.yaml"
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(recipe, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return f"Created: {path}"

# ========== Subscription Tools ==========
server.register_tool(
    name="subscribe_prtimes",
    description="Fetch press releases from PR Times",
    input_schema={
        "properties": {
            "keyword": {"type": "string", "default": "発表会"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": []
    },
    handler=lambda keyword="発表会", limit=10: _fetch_prtimes(keyword, limit)
)

def _fetch_prtimes(keyword, limit):
    """Fetch PR Times press releases."""
    Plugin = load_plugin_module("subscription", "prtimes")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    plugin = Plugin({
        "url": f"https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word={keyword}",
        "limit": limit,
        "state_file": str(DATA_DIR / "prtimes_state.txt"),
    })

    entries = list(plugin.execute())
    if not entries:
        return "No new press releases found"

    lines = [f"Found {len(entries)} press release(s):"]
    for i, e in enumerate(entries, 1):
        title = e.metadata.get("title", "No title")
        url = e.metadata.get("url", "")
        lines.append(f"{i}. {title}\n   {url}")
    return "\n".join(lines)

server.register_tool(
    name="subscribe_rss",
    description="Fetch entries from RSS feeds",
    input_schema={
        "properties": {
            "urls": {"type": "array", "items": {"type": "string"}, "description": "RSS feed URLs"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["urls"]
    },
    handler=lambda urls, limit=10: _fetch_rss(urls, limit)
)

def _fetch_rss(urls, limit):
    """Fetch RSS feed entries."""
    Plugin = load_plugin_module("subscription", "rss")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    plugin = Plugin({"urls": urls, "limit": limit, "state_file": str(DATA_DIR / "rss_state.txt")})
    entries = list(plugin.execute())
    if not entries:
        return "No new RSS entries found"

    lines = [f"Found {len(entries)} RSS entries:"]
    for i, e in enumerate(entries, 1):
        title = e.metadata.get("title", "No title")
        url = e.metadata.get("url", "")
        lines.append(f"{i}. {title}\n   {url}")
    return "\n".join(lines)

# ========== Publish Tools ==========
server.register_tool(
    name="publish_gmail",
    description="Send entries via Gmail (OAuth2)",
    input_schema={
        "properties": {
            "entries_json": {"type": "string", "description": "Entries as JSON array"},
            "to_addrs": {"type": "array", "items": {"type": "string"}, "description": "Recipient emails"},
        },
        "required": ["entries_json"]
    },
    handler=lambda entries_json, to_addrs=None: _publish_gmail(json.loads(entries_json), to_addrs)
)

def _publish_gmail(entries_data, to_addrs):
    """Send entries via Gmail."""
    # Reconstruct Entry objects
    entries = [Entry(**e) for e in entries_data]

    Plugin = load_plugin_module("publish", "gmail")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    config = {"to_addrs": to_addrs or []}
    # Load OAuth config from env
    env_file = CONFIG_DIR / ".env.local"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    plugin = Plugin(config)
    plugin.execute(iter(entries))
    return f"Sent {len(entries)} email(s) via Gmail"

server.register_tool(
    name="publish_twitter",
    description="Post entries to Twitter/X",
    input_schema={
        "properties": {
            "entries_json": {"type": "string", "description": "Entries as JSON array"},
        },
        "required": ["entries_json"]
    },
    handler=lambda entries_json: _publish_twitter(json.loads(entries_json))
)

def _publish_twitter(entries_data):
    """Post entries to Twitter."""
    entries = [Entry(**e) for e in entries_data]

    Plugin = load_plugin_module("publish", "twitter")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    plugin = Plugin({})
    plugin.execute(iter(entries))
    return f"Posted {len(entries)} tweet(s)"

server.register_tool(
    name="publish_line_notify",
    description="Send entries via LINE Notify",
    input_schema={
        "properties": {
            "entries_json": {"type": "string", "description": "Entries as JSON array"},
        },
        "required": ["entries_json"]
    },
    handler=lambda entries_json: _publish_line(json.loads(entries_json))
)

def _publish_line(entries_data):
    """Send entries via LINE Notify."""
    entries = [Entry(**e) for e in entries_data]

    Plugin = load_plugin_module("publish", "line_notify")
    if isinstance(Plugin, str):
        return f"Plugin load failed: {Plugin}"

    plugin = Plugin({})
    plugin.execute(iter(entries))
    return f"Sent {len(entries)} LINE Notify message(s)"

# ========== State Management ==========
server.register_tool(
    name="state_view",
    description="View the content of a state file (seen URLs, etc.)",
    input_schema={
        "properties": {"plugin_name": {"type": "string", "description": "Plugin name (prtimes, rss, etc.)"}},
        "required": ["plugin_name"]
    },
    handler=lambda plugin_name: _state_view(plugin_name)
)

def _state_view(name):
    """View state file contents."""
    state_file = DATA_DIR / f"{name}_state.txt"
    if not state_file.exists():
        return f"No state file: {state_file}"

    urls = state_file.read_text(encoding="utf-8").strip().split("\n")
    return f"State: {name} ({len(urls)} entries)\n" + "\n".join(f"  {u}" for u in urls[:50])

server.register_tool(
    name="state_clear",
    description="Clear a state file (reset deduplication)",
    input_schema={
        "properties": {"plugin_name": {"type": "string", "description": "Plugin name (prtimes, rss, etc.)"}},
        "required": ["plugin_name"]
    },
    handler=lambda plugin_name: _state_clear(plugin_name)
)

def _state_clear(name):
    """Clear state file."""
    state_file = DATA_DIR / f"{name}_state.txt"
    if state_file.exists():
        state_file.write_text("")
        return f"Cleared: {state_file}"
    return f"No state file to clear: {state_file}"

# ========== Config ==========
server.register_tool(
    name="config_list",
    description="List configured environment variables (from .env.local)",
    input_schema={"properties": {}, "required": []},
    handler=lambda: _config_list()
)

def _config_list():
    """List env config keys."""
    env_file = CONFIG_DIR / ".env.local"
    if not env_file.exists():
        return "No .env.local found"

    lines = ["Configured variables:"]
    for line in env_file.read_text().strip().split("\n"):
        if "=" in line and not line.startswith("#"):
            key = line.split("=")[0]
            lines.append(f"  {key}=***")
    return "\n".join(lines)

# ========== Main ==========
GREETING = """
╔══════════════════════════════════════════════╗
║  PyPer MCP Core Server v1.0.0               ║
║  12 tools | Pipeline + Pub/Sub + State       ║
╚══════════════════════════════════════════════╝
"""

def main():
    sys.stderr.write(GREETING + "\n")
    sys.stderr.flush()
    server.run()

if __name__ == "__main__":
    main()
