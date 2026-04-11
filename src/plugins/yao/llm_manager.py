"""
LLM Manager — yaoの機能をPyPer pluginとして吸収

PyPerのpluginとしてyaoの全機能を統合:
  - llama-server 起動・停止・状態監視
  - OpenAI互換APIプロキシ (ローカルLLM)
  - MCPツール: theory, novel, haiku, code, vision, imagen 等
  - agent persona 管理 (agents/*.md から動的読み込み)

Usage:
  from plugins.yao.llm_manager import LLMManager
  mgr = LLMManager()
  mgr.start_agent("natsume")
  mgr.chat("natsume", "こんにちは")
  mgr.status()
"""
import os
import sys
import json
import time
import socket
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional

# ========== Config ==========
HOME = Path.home()
LLAMA_BIN = HOME / "llama.cpp" / "build" / "bin"
MODELS_DIR = HOME / "models"
HOST = "127.0.0.1"
THREADS = int(os.environ.get("YAO_THREADS", "8"))
CTX = int(os.environ.get("YAO_CTX", "4096"))

# Qwen Cloud API (fallback when local not running)
QWEN_API_URL = os.environ.get("YAO_QWEN_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_API_KEY = os.environ.get("YAO_QWEN_API_KEY", "")
QWEN_MODEL = os.environ.get("YAO_QWEN_MODEL", "qwen-plus")

# Agent definitions
AGENTS_DIR = HOME / ".qwen" / "agents"
SKILLS_CONFIG = Path(__file__).resolve().parent.parent.parent / "yao-skills-config.json"
TOOLS_CONFIG = Path(__file__).resolve().parent.parent.parent / "yao-mcp-tools.json"

# ========== Agent Registry ==========
AGENTS = {
    "natsume":  {"dir": MODELS_DIR / "llm" / "qwen3-8b",           "port": 8081, "desc": "夏目 - Qwen3 8B (text)",        "type": "llm"},
    "sharaku":  {"dir": MODELS_DIR / "vlm" / "qwen2.5-vl-3b",     "port": 8082, "desc": "写楽 - Qwen2.5-VL 3B (vision)", "type": "vlm"},
    "hokusai":  {"dir": MODELS_DIR / "diffusion" / "sd15-hokusai", "port": 8083, "desc": "北斎 - SD1.5 Hokusai (diffusion)", "type": "diffusion"},
}


# ========== Helpers ==========
def _check_running(port: int) -> bool:
    """Check if HTTP server is responding."""
    try:
        req = urllib.request.Request(f"http://{HOST}:{port}/v1/models")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def _find_model(d: Path, pattern: str = "*.gguf", exclude: str = "mmproj*") -> Optional[str]:
    """Find GGUF model file in directory."""
    if not d.is_dir():
        return None
    for f in d.glob(pattern):
        if not f.name.startswith("mmproj"):
            return str(f)
    return None


def _find_mmproj(d: Path) -> Optional[str]:
    """Find MMProj file for vision models."""
    if not d.is_dir():
        return None
    for f in d.glob("mmproj*.gguf"):
        return str(f)
    return None


def _find_llama_server() -> Optional[str]:
    """Find llama-server binary."""
    candidates = [LLAMA_BIN / "llama-server"]
    for p in candidates:
        if p.exists():
            return str(p)
    try:
        r = subprocess.run(["wsl", "bash", "-c", "ls ~/llama.cpp/build/bin/llama-server"],
                          capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def _api_chat(port: int, messages: list, temperature: float = 0.7, max_tokens: int = 2048) -> Optional[str]:
    """Call local OpenAI-compatible chat API."""
    body = json.dumps({
        "model": "local",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }).encode()
    req = urllib.request.Request(
        f"http://{HOST}:{port}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def _qwen_cloud(messages: list, temperature: float = 0.7, max_tokens: int = 2048) -> Optional[str]:
    """Call Qwen Cloud API as fallback."""
    if not QWEN_API_KEY:
        return None
    try:
        body = json.dumps({
            "model": QWEN_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }).encode()
        req = urllib.request.Request(
            f"{QWEN_API_URL}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {QWEN_API_KEY}"
            }
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None


# ========== LLM Manager ==========
class LLMManager:
    """
    PyPer plugin: Local LLM process management + chat orchestration.
    Replaces yao.py + yao-mcp.py functionality.
    """

    def __init__(self):
        self._agents = dict(AGENTS)
        self._load_external_configs()

    def _load_external_configs(self):
        """Load skills config and tools config from JSON files."""
        self._skills_config = {}
        self._tools_config = {}
        if SKILLS_CONFIG.exists():
            with open(SKILLS_CONFIG, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._skills_config = data.get("skills", {})
        if TOOLS_CONFIG.exists():
            with open(TOOLS_CONFIG, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._tools_config = data.get("agents", {})

    # ---- Process Management ----

    def start_agent(self, agent_name: str) -> bool:
        """Start an agent's llama-server in background."""
        cfg = self._agents.get(agent_name)
        if not cfg:
            return False

        port = cfg["port"]
        if _check_running(port):
            return True

        model = _find_model(cfg["dir"])
        if not model:
            return False

        server = _find_llama_server()
        if not server:
            return False

        mmproj = _find_mmproj(cfg["dir"]) if cfg["type"] == "vlm" else None

        if agent_name == "natsume":
            cmd = [server, "-m", model, "--threads", str(THREADS), "--ctx-size", str(CTX),
                   "--n-gpu-layers", "0", "--flash-attn", "on", "--jinja",
                   "--port", str(port), "--host", HOST]
        elif agent_name == "sharaku":
            cmd = [server, "-m", model, "--threads", str(THREADS), "--ctx-size", str(CTX),
                   "--n-gpu-layers", "0", "--flash-attn", "on", "--jinja",
                   "--port", str(port), "--host", HOST]
            if mmproj:
                cmd += ["--mmproj", mmproj]
        elif agent_name == "hokusai":
            diff_bin = LLAMA_BIN / "llama-diffusion-cli"
            if diff_bin.exists():
                cmd = [str(diff_bin), "--model-dir", model, "--port", str(port), "--host", HOST]
            else:
                return False
        else:
            return False

        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        max_wait = 90 if cfg["type"] == "diffusion" else 60
        for i in range(max_wait):
            time.sleep(1)
            if _check_running(port):
                return True
        return False

    def stop_agent(self, agent_name: str) -> bool:
        """Stop an agent's llama-server."""
        cfg = self._agents.get(agent_name)
        if not cfg:
            return False
        port = cfg["port"]
        try:
            r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
            for line in r.stdout.splitlines():
                if f":{port} " in line:
                    import re
                    m = re.search(r'pid=(\d+)', line)
                    if m:
                        pid = int(m.group(1))
                        os.kill(pid, 9)
                        return True
        except Exception:
            pass
        return False

    def status(self) -> Dict[str, dict]:
        """Return status of all agents."""
        result = {}
        for name, cfg in self._agents.items():
            running = _check_running(cfg["port"])
            result[name] = {
                "port": cfg["port"],
                "desc": cfg["desc"],
                "running": running,
            }
        return result

    # ---- Chat Orchestration ----

    def chat(self, agent_name: str, prompt: str, system_prompt: str = "",
             temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> Optional[str]:
        """
        Chat with a specific agent. Auto-starts if not running.
        Falls back to Qwen Cloud if local is unavailable.
        """
        cfg = self._agents.get(agent_name)
        if not cfg:
            return f"Unknown agent: {agent_name}"

        # Determine params
        skill_cfg = self._skills_config.get(agent_name, {})
        temp = temperature if temperature is not None else skill_cfg.get("temperature", 0.7)
        max_tok = max_tokens if max_tokens is not None else skill_cfg.get("max_tokens", 2048)
        sys_prompt = system_prompt or skill_cfg.get("system_prompt", "You are a helpful assistant.")

        # Try local first
        port = cfg["port"]
        if not _check_running(port):
            self.start_agent(agent_name)

        if _check_running(port):
            msgs = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}]
            reply = _api_chat(port, msgs, temperature=temp, max_tokens=max_tok)
            if reply:
                return reply

        # Fallback to cloud
        return _qwen_cloud([{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
                          temperature=temp, max_tokens=max_tok)

    # ---- Tools (MCP-compatible) ----

    def tool_call(self, tool_name: str, **kwargs) -> str:
        """
        Call a tool by name (matches yao-mcp-tools.json).
        This is the entry point for MCP tool calls.
        """
        # Look up tool config for all agents
        for agent_name, agent_tools in self._tools_config.items():
            for tool_def in agent_tools.get("tools", []):
                if tool_def["name"] == tool_name:
                    sys_prompt = tool_def.get("system_prompt", "You are helpful.")
                    temp = tool_def.get("temperature", 0.7)
                    max_tok = tool_def.get("max_tokens", 2048)

                    # Direct command tools
                    if tool_name == "list":
                        path = kwargs.get("path", ".")
                        r = subprocess.run(["wsl", "bash", "-c", f"ls -la '{path}' 2>&1"],
                                          capture_output=True, text=True, timeout=10)
                        return r.stdout if r.returncode == 0 else r.stderr

                    if tool_name == "read":
                        path = kwargs.get("path", "")
                        r = subprocess.run(["wsl", "bash", "-c", f"cat '{path}' 2>&1"],
                                          capture_output=True, text=True, timeout=10)
                        content = r.stdout[:4000] if r.returncode == 0 else f"Error: {r.stderr}"
                        return self.chat(agent_name, content,
                                        system_prompt="ファイルの内容を読んで要約して。",
                                        temperature=0.3)

                    if tool_name == "imagen":
                        prompt = kwargs.get("prompt", "")
                        output = kwargs.get("output", "output.png")
                        return self._generate_image(prompt, output)

                    if tool_name == "status":
                        return self._format_status()

                    if tool_name == "start":
                        ok = self.start_agent(agent_name)
                        return f"Started {agent_name}" if ok else f"Failed to start {agent_name}"

                    # LLM chat tools
                    prompt = kwargs.get("prompt", "")
                    return self.chat(agent_name, prompt,
                                    system_prompt=sys_prompt,
                                    temperature=temp,
                                    max_tokens=max_tok)

        return f"Unknown tool: {tool_name}"

    def _generate_image(self, prompt: str, output: str = "output.png") -> str:
        """Call diffusion API."""
        cfg = self._agents.get("hokusai")
        if not cfg:
            return "hokusai agent not configured"
        port = cfg["port"]
        if not _check_running(port):
            self.start_agent("hokusai")
        if not _check_running(port):
            return "Failed to start hokusai"
        try:
            body = json.dumps({"prompt": prompt, "n": 1, "size": "512x512"}).encode()
            req = urllib.request.Request(
                f"http://{HOST}:{port}/v1/images/generations",
                data=body,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(output, "wb") as f:
                    f.write(resp.read())
                if os.path.getsize(output) > 0:
                    return f"Saved: {output}"
        except Exception as e:
            return f"Error: {e}"
        return "Failed to generate image"

    def _format_status(self) -> str:
        """Format agent status as text."""
        lines = []
        for name, info in self.status().items():
            icon = "✓" if info["running"] else "✗"
            lines.append(f"  {icon} {name} (port {info['port']}) {'RUNNING' if info['running'] else 'stopped'}")
        return "\n".join(lines)


# ========== MCP Server Entry Point ==========
def make_mcp_server() -> 'MCPServer':
    """
    Create an MCP server wrapping the LLMManager.
    This replaces yao-mcp.py.
    """
    from plugins.mcp_base import MCPServer
    mgr = LLMManager()

    server = MCPServer("pyper-llm", "1.0.0")

    # Register tools from config
    for agent_name, agent_cfg in mgr._tools_config.items():
        for tool_def in agent_cfg.get("tools", []):
            tool_name = tool_def["name"]
            # Skip duplicates
            if tool_name in server.tools:
                continue
            server.register_tool(
                name=tool_name,
                description=tool_def.get("description", ""),
                input_schema=tool_def.get("inputSchema", {
                    "type": "object",
                    "properties": {"prompt": {"type": "string"}},
                    "required": ["prompt"]
                }),
                handler=lambda **kw, tn=tool_name: mgr.tool_call(tn, **kw)
            )

    return server


if __name__ == "__main__":
    server = make_mcp_server()
    server.run()
