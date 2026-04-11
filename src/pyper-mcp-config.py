#!/usr/bin/env python3
"""
PyPer MCP Config Server v2.0.0 — Full MCP Manager

Complete MCP server lifecycle management via natural language.
Always available as a lightweight manager.

Tools:
  - mcp_status      → Show all MCP server status (table view)
  - mcp_toggle      → Enable/disable an MCP server
  - mcp_bulk_toggle → Enable/disable multiple servers at once
  - mcp_add         → Register a new MCP server
  - mcp_remove      → Unregister an MCP server
  - mcp_edit        → Edit an existing MCP server config
  - mcp_search      → Search MCP servers by keyword (name/description)
  - mcp_discover    → Auto-discover potential MCP servers on disk
  - mcp_validate    → Validate settings.json structure
  - mcp_backup      → Backup current settings.json
  - mcp_restore     → Restore settings.json from backup
  - mcp_suggest     → Suggest servers based on task description
"""
import sys
import os
import json
import shutil
import glob as globmod
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from plugins.mcp_base import MCPServer

# ========== Config ==========
SETTINGS_PATH = Path.home() / ".qwen" / "settings.json"
BACKUP_DIR = Path.home() / ".qwen" / "mcp-backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Auto-discovery scan paths
DISCOVERY_PATHS = [
    Path.home() / "Documents" / "MEGA",
    Path.home() / ".qwen",
    Path.home() / "yao",
]

# Files/patterns that indicate an MCP server
MCP_INDICATORS = [
    "my-mcp-server/index.js",
    "my-mcp-server/index.ts",
    "mcp-server/index.js",
    "mcp-server/index.ts",
    "src/mcp*.py",
    "src/*-mcp*.py",
    "*-mcp-server/index.js",
    "*-mcp-server/index.ts",
    "package.json",  # check for @modelcontextprotocol/sdk dependency
]

# ========== Server ==========
server = MCPServer("pyper-config", "2.0.0")

# ========== Helpers ==========
def _load_settings():
    """Load settings.json, return None if not found."""
    if not SETTINGS_PATH.exists():
        return None
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save_settings(settings):
    """Save settings.json with formatting."""
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def _format_server_table(mcp_servers, filter_fn=None):
    """Format server list as aligned table."""
    items = list(mcp_servers.items())
    if filter_fn:
        items = [(n, c) for n, c in items if filter_fn(n, c)]

    if not items:
        return "  (no servers match)"

    # Calculate column widths
    name_w = max(len(n) for n, _ in items)
    name_w = max(name_w, 14)
    status_w = 4
    cmd_w = max(len(c.get("command", "")) for _, c in items)
    cmd_w = min(max(cmd_w, 10), 20)

    lines = []
    lines.append(f"  {'NAME':<{name_w}}  {'ST'}  {'CMD':<{cmd_w}}  {'STATUS'}  DESCRIPTION")
    lines.append(f"  {'─' * name_w}  {'──'}  {'─' * cmd_w}  {'──────'}  {'─' * 40}")

    for name, cfg in items:
        disabled = cfg.get("disabled", False)
        icon = "⏸" if disabled else "✅"
        cmd = cfg.get("command", "")
        desc = cfg.get("description", "")
        status = "disabled" if disabled else "active"
        lines.append(f"  {name:<{name_w}}  {icon}  {cmd:<{cmd_w}}  {status:<6}  {desc}")

    return "\n".join(lines)

def _make_backup():
    """Create timestamped backup of settings.json."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"settings_{ts}.json"
    shutil.copy2(SETTINGS_PATH, backup_path)
    return backup_path

# ========== 1. MCP Status ==========
server.register_tool(
    name="mcp_status",
    description="Show status of all MCP servers with detailed table view",
    input_schema={
        "properties": {
            "filter": {"type": "string", "enum": ["all", "enabled", "disabled"], "default": "all"},
        },
        "required": []
    },
    handler=lambda filter="all": _mcp_status(filter)
)

def _mcp_status(filter="all"):
    settings = _load_settings()
    if not settings:
        return f"❌ Settings not found: {SETTINGS_PATH}"

    mcp_servers = settings.get("mcpServers", {})

    if filter == "enabled":
        fn = lambda n, c: not c.get("disabled", False)
    elif filter == "disabled":
        fn = lambda n, c: c.get("disabled", False)
    else:
        fn = None

    table = _format_server_table(mcp_servers, fn)

    total = len(mcp_servers)
    enabled = sum(1 for c in mcp_servers.values() if not c.get("disabled", False))
    disabled = total - enabled

    return f"📡 MCP Server Status ({enabled} enabled, {disabled} disabled, {total} total)\n\n{table}"

# ========== 2. MCP Toggle ==========
server.register_tool(
    name="mcp_toggle",
    description="Enable, disable, or toggle a single MCP server",
    input_schema={
        "properties": {
            "server_name": {"type": "string", "description": "MCP server name"},
            "action": {"type": "string", "enum": ["enable", "disable", "toggle"], "default": "toggle"},
        },
        "required": ["server_name"]
    },
    handler=lambda server_name, action="toggle": _mcp_toggle(server_name, action)
)

def _mcp_toggle(server_name, action="toggle"):
    settings = _load_settings()
    if not settings:
        return f"❌ Settings not found: {SETTINGS_PATH}"

    mcp_servers = settings.get("mcpServers", {})
    if server_name not in mcp_servers:
        return f"❌ Server '{server_name}' not found.\nAvailable: {', '.join(mcp_servers.keys())}"

    cfg = mcp_servers[server_name]
    current = not cfg.get("disabled", False)

    if action == "toggle":
        new_state = not current
    else:
        new_state = action == "enable"

    if new_state:
        cfg.pop("disabled", None)
        msg = f"✅ Enabled: {server_name}"
    else:
        cfg["disabled"] = True
        msg = f"⏸ Disabled: {server_name}"

    _save_settings(settings)
    return msg

# ========== 3. MCP Bulk Toggle ==========
server.register_tool(
    name="mcp_bulk_toggle",
    description="Enable/disable multiple MCP servers at once",
    input_schema={
        "properties": {
            "targets": {"type": "array", "items": {"type": "string"}, "description": "List of server names, or 'all', 'pyper-*', 'yao-*' patterns"},
            "action": {"type": "string", "enum": ["enable", "disable"], "default": "enable"},
        },
        "required": ["targets", "action"]
    },
    handler=lambda targets, action="enable": _mcp_bulk_toggle(targets, action)
)

def _mcp_bulk_toggle(targets, action="enable"):
    import fnmatch
    settings = _load_settings()
    if not settings:
        return f"❌ Settings not found: {SETTINGS_PATH}"

    mcp_servers = settings.get("mcpServers", {})
    matched = set()

    for target in targets:
        if target == "all":
            matched.update(mcp_servers.keys())
        elif "*" in target:
            # Pattern matching
            for name in mcp_servers:
                if fnmatch.fnmatch(name, target):
                    matched.add(name)
        elif target in mcp_servers:
            matched.add(target)

    if not matched:
        return f"❌ No servers matched. Available: {', '.join(mcp_servers.keys())}"

    results = []
    for name in sorted(matched):
        cfg = mcp_servers[name]
        if action == "enable":
            cfg.pop("disabled", None)
            results.append(f"  ✅ {name}")
        else:
            cfg["disabled"] = True
            results.append(f"  ⏸ {name}")

    _save_settings(settings)
    return f"{'Enabled' if action == 'enable' else 'Disabled'} {len(matched)} server(s):\n" + "\n".join(results)

# ========== 4. MCP Add ==========
server.register_tool(
    name="mcp_add",
    description="Register a new MCP server in settings.json",
    input_schema={
        "properties": {
            "name": {"type": "string", "description": "Unique server name"},
            "command": {"type": "string", "description": "Executable command (node, python, wsl, etc.)"},
            "args": {"type": "array", "items": {"type": "string"}, "description": "Command arguments (file paths, flags)"},
            "description": {"type": "string", "default": "", "description": "Human-readable description"},
            "timeout": {"type": "number", "default": 300000, "description": "Timeout in milliseconds"},
        },
        "required": ["name", "command", "args"]
    },
    handler=lambda name, command, args, description="", timeout=300000: _mcp_add(name, command, args, description, timeout)
)

def _mcp_add(name, command, args, description="", timeout=300000):
    settings = _load_settings()
    if not settings:
        return f"❌ Settings not found: {SETTINGS_PATH}"

    mcp_servers = settings.get("mcpServers", {})

    if name in mcp_servers:
        return f"⚠️ Server '{name}' already exists. Use mcp_edit to modify it."

    # Validate args path if it looks like a file path
    for arg in args:
        if arg.endswith(('.js', '.ts', '.py', '.sh', '.ps1')):
            p = Path(arg)
            if not p.exists() and not p.is_absolute():
                return f"⚠️ File not found: {arg}\nPlease provide an absolute path."

    mcp_servers[name] = {
        "command": command,
        "args": args,
        "timeout": timeout,
        "trust": True,
        "description": description,
    }

    settings["mcpServers"] = mcp_servers
    _save_settings(settings)
    return f"✅ Registered MCP server: {name}\n  Command: {command} {' '.join(args)}\n  Description: {description}"

# ========== 5. MCP Remove ==========
server.register_tool(
    name="mcp_remove",
    description="Unregister an MCP server from settings.json (does not delete files)",
    input_schema={
        "properties": {
            "name": {"type": "string", "description": "Server name to remove"},
        },
        "required": ["name"]
    },
    handler=lambda name: _mcp_remove(name)
)

def _mcp_remove(name):
    settings = _load_settings()
    if not settings:
        return f"❌ Settings not found: {SETTINGS_PATH}"

    mcp_servers = settings.get("mcpServers", {})
    if name not in mcp_servers:
        return f"❌ Server '{name}' not found.\nAvailable: {', '.join(mcp_servers.keys())}"

    desc = mcp_servers[name].get("description", "")
    del mcp_servers[name]
    settings["mcpServers"] = mcp_servers
    _save_settings(settings)
    return f"🗑️ Removed MCP server: {name}\n  Description: {desc}\n  (Files on disk are not deleted)"

# ========== 6. MCP Edit ==========
server.register_tool(
    name="mcp_edit",
    description="Edit an existing MCP server's configuration",
    input_schema={
        "properties": {
            "name": {"type": "string", "description": "Server name to edit"},
            "command": {"type": "string", "description": "New command (optional)"},
            "args": {"type": "array", "items": {"type": "string"}, "description": "New arguments (optional)"},
            "description": {"type": "string", "description": "New description (optional)"},
            "timeout": {"type": "number", "description": "New timeout in ms (optional)"},
        },
        "required": ["name"]
    },
    handler=lambda name, command=None, args=None, description=None, timeout=None: _mcp_edit(name, command, args, description, timeout)
)

def _mcp_edit(name, command=None, args=None, description=None, timeout=None):
    settings = _load_settings()
    if not settings:
        return f"❌ Settings not found: {SETTINGS_PATH}"

    mcp_servers = settings.get("mcpServers", {})
    if name not in mcp_servers:
        return f"❌ Server '{name}' not found.\nAvailable: {', '.join(mcp_servers.keys())}"

    cfg = mcp_servers[name]
    changes = []

    if command is not None:
        cfg["command"] = command
        changes.append(f"command → {command}")
    if args is not None:
        cfg["args"] = args
        changes.append(f"args → {' '.join(args)}")
    if description is not None:
        cfg["description"] = description
        changes.append(f"description → {description}")
    if timeout is not None:
        cfg["timeout"] = timeout
        changes.append(f"timeout → {timeout}ms")

    if not changes:
        return f"⚠️ No changes specified for '{name}'."

    settings["mcpServers"] = mcp_servers
    _save_settings(settings)
    return f"✏️ Updated '{name}':\n  " + "\n  ".join(changes)

# ========== 7. MCP Search ==========
server.register_tool(
    name="mcp_search",
    description="Search MCP servers by keyword in name or description",
    input_schema={
        "properties": {
            "query": {"type": "string", "description": "Search keyword"},
        },
        "required": ["query"]
    },
    handler=lambda query: _mcp_search(query)
)

def _mcp_search(query):
    settings = _load_settings()
    if not settings:
        return f"❌ Settings not found: {SETTINGS_PATH}"

    mcp_servers = settings.get("mcpServers", {})
    query_lower = query.lower()

    matched = {}
    for name, cfg in mcp_servers.items():
        desc = cfg.get("description", "").lower()
        if query_lower in name.lower() or query_lower in desc:
            matched[name] = cfg

    if not matched:
        return f"🔍 No servers match '{query}'."

    table = _format_server_table(matched)
    return f"🔍 Search results for '{query}' ({len(matched)} found):\n\n{table}"

# ========== 8. MCP Discover ==========
server.register_tool(
    name="mcp_discover",
    description="Auto-discover potential MCP servers by scanning common directories",
    input_schema={
        "properties": {
            "scan_paths": {"type": "array", "items": {"type": "string"}, "description": "Custom paths to scan (optional, uses defaults if omitted)"},
        },
        "required": []
    },
    handler=lambda scan_paths=None: _mcp_discover(scan_paths)
)

def _mcp_discover(scan_paths=None):
    paths_to_scan = [Path(p) for p in scan_paths] if scan_paths else DISCOVERY_PATHS

    # Filter to existing paths
    paths_to_scan = [p for p in paths_to_scan if p.exists()]

    if not paths_to_scan:
        return "❌ No valid scan paths found."

    found = []
    already_registered = set()

    settings = _load_settings()
    if settings:
        for name, cfg in settings.get("mcpServers", {}).items():
            for arg in cfg.get("args", []):
                already_registered.add(arg.lower())

    for base_path in paths_to_scan:
        # Look for package.json with MCP SDK dependency
        for pkg_json in globmod.glob(str(base_path / "**/package.json"), recursive=True):
            p = Path(pkg_json)
            # Skip node_modules
            if "node_modules" in str(p):
                continue
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "@modelcontextprotocol/sdk" in deps:
                    mcp_dir = p.parent
                    rel = mcp_dir.relative_to(base_path) if str(mcp_dir).startswith(str(base_path)) else mcp_dir
                    is_registered = str(mcp_dir).lower() in already_registered or str(p).lower() in already_registered
                    status = "✅ registered" if is_registered else "🆕 not registered"
                    found.append(f"  {status}  {mcp_dir}")
            except Exception:
                continue

        # Look for Python MCP scripts
        for py_file in globmod.glob(str(base_path / "**/*-mcp*.py"), recursive=True):
            p = Path(py_file)
            if "site-packages" in str(p) or ".qwen\\skills" in str(p):
                continue
            is_registered = str(p).lower() in already_registered
            status = "✅ registered" if is_registered else "🆕 not registered"
            found.append(f"  {status}  {p}")

    if not found:
        return "🔍 No unregistered MCP servers discovered."

    return f"🔍 MCP Server Discovery ({len(found)} found):\n\n" + "\n".join(found) + "\n\nUse mcp_add to register any server."

# ========== 9. MCP Validate ==========
server.register_tool(
    name="mcp_validate",
    description="Validate settings.json structure and check for issues",
    input_schema={"properties": {}, "required": []},
    handler=lambda: _mcp_validate()
)

def _mcp_validate():
    settings = _load_settings()
    if not settings:
        return f"❌ Settings not found: {SETTINGS_PATH}"

    issues = []
    mcp_servers = settings.get("mcpServers", {})

    # Check structure
    if not isinstance(mcp_servers, dict):
        issues.append("mcpServers is not an object")
        return f"❌ Invalid settings structure:\n  " + "\n  ".join(issues)

    for name, cfg in mcp_servers.items():
        prefix = f"  [{name}]"

        if not cfg.get("command"):
            issues.append(f"{prefix} missing 'command'")
        if not cfg.get("args"):
            issues.append(f"{prefix} missing 'args'")
        if not cfg.get("description"):
            issues.append(f"{prefix} missing 'description' (cosmetic)")

        # Check if executable path exists
        for arg in cfg.get("args", []):
            p = Path(arg)
            if p.suffix in ('.js', '.ts', '.py', '.sh', '.ps1') and p.exists() is False:
                issues.append(f"{prefix} file not found: {arg}")

        # Check timeout reasonableness
        timeout = cfg.get("timeout", 30000)
        if timeout < 1000:
            issues.append(f"{prefix} timeout seems too low: {timeout}ms")
        elif timeout > 600000:
            issues.append(f"{prefix} timeout seems high: {timeout}ms")

    # Check for duplicate descriptions
    descs = [cfg.get("description", "") for cfg in mcp_servers.values()]
    if len(descs) != len(set(descs)):
        issues.append("Some descriptions appear to be duplicated")

    if not issues:
        return f"✅ settings.json is valid ({len(mcp_servers)} servers configured)"

    return f"⚠️ Found {len(issues)} issue(s):\n" + "\n".join(issues)

# ========== 10. MCP Backup ==========
server.register_tool(
    name="mcp_backup",
    description="Create a backup of the current settings.json",
    input_schema={"properties": {}, "required": []},
    handler=lambda: _mcp_backup()
)

def _mcp_backup():
    if not SETTINGS_PATH.exists():
        return f"❌ Settings not found: {SETTINGS_PATH}"

    backup_path = _make_backup()
    size_kb = backup_path.stat().st_size / 1024
    return f"💾 Backup created: {backup_path} ({size_kb:.1f} KB)"

# ========== 11. MCP Restore ==========
server.register_tool(
    name="mcp_restore",
    description="Restore settings.json from a backup file",
    input_schema={
        "properties": {
            "backup_file": {"type": "string", "description": "Path to backup file, or 'latest' for most recent"},
        },
        "required": ["backup_file"]
    },
    handler=lambda backup_file: _mcp_restore(backup_file)
)

def _mcp_restore(backup_file):
    if backup_file == "latest":
        backups = sorted(BACKUP_DIR.glob("settings_*.json"))
        if not backups:
            return "❌ No backups found."
        backup_path = backups[-1]
    else:
        backup_path = Path(backup_file)
        if not backup_path.exists():
            return f"❌ Backup not found: {backup_path}"

    # Validate it's valid JSON
    try:
        with open(backup_path, 'r', encoding='utf-8') as f:
            json.load(f)
    except json.JSONDecodeError as e:
        return f"❌ Invalid backup file: {e}"

    shutil.copy2(backup_path, SETTINGS_PATH)
    return f"♻️ Restored settings from: {backup_path}\n  Restart Qwen Code to apply."

# ========== 12. MCP Suggest ==========
server.register_tool(
    name="mcp_suggest",
    description="Suggest which MCP servers to enable based on your task",
    input_schema={
        "properties": {
            "task": {"type": "string", "description": "What you want to do"},
        },
        "required": ["task"]
    },
    handler=lambda task: _mcp_suggest(task)
)

def _mcp_suggest(task):
    suggestions = {
        "画像": ["pyper-media", "natsume"],
        "image": ["pyper-media", "natsume"],
        "動画": ["pyper-media"],
        "video": ["pyper-media"],
        "trend": ["pyper-media"],
        "トレンド": ["pyper-media"],
        "生成": ["pyper-media"],
        "fall": ["pyper-core"],
        "プレス": ["pyper-core"],
        "press": ["pyper-core"],
        "Gmail": ["pyper-core"],
        "mail": ["pyper-core"],
        "戦略": ["pyper-advisor"],
        "strategy": ["pyper-advisor"],
        "法律": ["pyper-advisor"],
        "law": ["pyper-advisor"],
        "コード": ["pyper-core", "pyper-advisor"],
        "code": ["pyper-core", "pyper-advisor"],
        "review": ["pyper-advisor"],
        "skill": ["pyper-advisor"],
        "チャット": ["natsume", "takuboku"],
        "chat": ["natsume", "takuboku"],
        "vision": ["sharaku"],
        "OCR": ["sharaku"],
        "画像生成": ["hokusai"],
        "file": ["plagger"],
        "ファイル": ["plagger"],
        "計算": ["plagger"],
        "calc": ["plagger"],
        "add": ["plagger"],
        "足し": ["plagger"],
    }

    task_lower = task.lower()
    matched = set()
    for keyword, servers in suggestions.items():
        if keyword.lower() in task_lower:
            matched.update(servers)

    if not matched:
        return f"No specific recommendation for: '{task}'\nDefault: pyper-core (always enabled)"

    lines = [f"📌 Recommended for '{task}':"]
    for s in sorted(matched):
        lines.append(f"  → {s}")

    return "\n".join(lines) + "\n\nEnable with: mcp_toggle(server_name, 'enable')"

# ========== Main ==========
GREETING = """
╔══════════════════════════════════════════════════════╗
║  PyPer MCP Config Server v2.0.0                     ║
║  Full MCP Manager — 12 tools                        ║
║  status, toggle, bulk_toggle, add, remove, edit,     ║
║  search, discover, validate, backup, restore, suggest ║
╚══════════════════════════════════════════════════════╝
"""

def main():
    sys.stderr.write(GREETING + "\n")
    sys.stderr.flush()
    server.run()

if __name__ == "__main__":
    main()
