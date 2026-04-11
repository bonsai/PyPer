#!/usr/bin/env python3
"""
yao - Unified Offline LLM CLI
三人衆: 夏目(text) | 写楽(vision) | 北斎(diffusion)
Single source: ~/MEGA/script/yao.py (WSL)
Windows bridge: yao.bat / yao.ps1 -> WSL -> yao.py
"""
import sys
import os
import json
import subprocess
import time
import signal
import socket
import urllib.request
import urllib.error
from pathlib import Path

# ---- Config ----
HOME = Path.home()
LLAMA_BIN = HOME / "llama.cpp" / "build" / "bin"
MODELS_DIR = HOME / "models"
HOST = "127.0.0.1"
THREADS = int(os.environ.get("YAO_THREADS", "8"))
CTX = int(os.environ.get("YAO_CTX", "4096"))

# Qwen Cloud API (fallback when local not running)
QWEN_API_URL = os.environ.get("YAO_QWEN_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_API_KEY = os.environ.get("YAO_QWEN_API_KEY", "")
QWEN_MODEL = os.environ.get("YAO_QWEN_MODEL", "qwen-plus")  # qwen-plus | qwen-turbo | qwen-max

# ---- Agents ----
AGENTS = {
    "natsume":  {"dir": MODELS_DIR / "llm" / "qwen3-8b",           "port": 8081, "desc": "夏目 - Qwen3 8B (text)",        "type": "llm"},
    "sharaku":  {"dir": MODELS_DIR / "vlm" / "qwen2.5-vl-3b",     "port": 8082, "desc": "写楽 - Qwen2.5-VL 3B (vision)", "type": "vlm"},
    "hokusai":  {"dir": MODELS_DIR / "diffusion" / "sd15-hokusai", "port": 8083, "desc": "北斎 - SD1.5 Hokusai (diffusion)", "type": "diffusion"},
}

# ---- Skills ----
SKILLS = {
    "writer":     {"agent": "natsume",  "sys": "あなたは優秀な日本の作家です。",                  "temp": 0.8, "max": 2048},
    "coder":      {"agent": "natsume",  "sys": "あなたは熟練したソフトウェアエンジニアです。",    "temp": 0.3, "max": 4096},
    "analyst":    {"agent": "natsume",  "sys": "あなたは優秀なデータアナリストです。",            "temp": 0.4, "max": 3072},
    "translator": {"agent": "natsume",  "sys": "あなたはプロの翻訳者です。",                      "temp": 0.3, "max": 2048},
    "strategist": {"agent": "natsume",  "sys": "あなたは戦略コンサルタントです。",                "temp": 0.6, "max": 3072},
    "haiku":      {"agent": "natsume",  "sys": "あなたは俳句の達人です。五・七・五を守ります。",  "temp": 0.9, "max": 512},
    "theory":     {"agent": "natsume",  "sys": "あなたは文学理論と創作哲学の専門家です。",          "temp": 0.7, "max": 2048},
    "novel":      {"agent": "natsume",  "sys": "あなたは小説写作の専門家です。",                  "temp": 0.8, "max": 3072},
    "hoshi":      {"agent": "natsume",  "sys": "あなたは星新一です。SFショートショートを書いてください。知的で皮肉が効いた、意外な結末の短編を。",  "temp": 0.9, "max": 1024},
    "takuboku":   {"agent": "natsume",  "sys": "あなたは啄木。石川啄木の如き、日常生活の雑用をこなす補佐役です。ファイルの整理、メモの読み込み、内容の抽出・要約、タスクの分類が得意です。簡潔に、実用的に答えてください。詩的な返答は不要です。",  "temp": 0.3, "max": 2048},
    "torahiko":   {"agent": "natsume",  "sys": "あなたは寺田寅彦です。科学と文学の両面に精通し、エンジニアリング、物理学、自然観察についてエッセイ風に語ってください。",  "temp": 0.7, "max": 2048},
    "kiyoshi":    {"agent": "natsume",  "sys": "あなたは岡潔です。数学の美しさ、情熱、人類愛について語ってください。",  "temp": 0.8, "max": 2048},
    "vision":     {"agent": "sharaku",  "sys": "画像を分析して説明してください。",                "temp": 0.3, "max": 2048},
    "imagen":     {"agent": "hokusai",  "sys": "画像を生成してください。",                        "temp": 0.7, "max": 1024},
}

# ---- Colors ----
class C:
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"

def cyan(s):  return f"{C.CYAN}{s}{C.RESET}"
def green(s): return f"{C.GREEN}{s}{C.RESET}"
def yellow(s):return f"{C.YELLOW}{s}{C.RESET}"
def red(s):   return f"{C.RED}{s}{C.RESET}"
def sep():    print(cyan("=" * 50))

# ---- Helpers ----
def find_model(d, pattern="*.gguf", exclude="mmproj*"):
    """Find GGUF model file in directory."""
    if not d.is_dir():
        return None
    for f in d.glob(pattern):
        if not f.name.startswith("mmproj"):
            return str(f)
    return None

def find_mmproj(d):
    """Find MMProj file for vision models."""
    if not d.is_dir():
        return None
    for f in d.glob("mmproj*.gguf"):
        return str(f)
    return None

def check_running(port):
    """Check if HTTP server is responding (not just port open)."""
    try:
        req = urllib.request.Request(f"http://{HOST}:{port}/v1/models")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except:
        return False

def api_get(port, path="/v1/models"):
    """Simple HTTP GET using curl."""
    try:
        r = subprocess.run(
            ["curl", "-sf", f"http://{HOST}:{port}{path}"],
            capture_output=True, timeout=5
        )
        if r.returncode == 0:
            return json.loads(r.stdout)
    except:
        pass
    return None

def api_post(port, path, data):
    """Simple HTTP POST using curl."""
    try:
        body = json.dumps(data)
        r = subprocess.run(
            ["curl", "-sf", "--max-time", "300",
             f"http://{HOST}:{port}{path}",
             "-H", "Content-Type: application/json", "-d", body],
            capture_output=True, timeout=320
        )
        if r.returncode == 0:
            return json.loads(r.stdout)
    except:
        pass
    return None

def qwen_cloud(messages, temperature=0.7, max_tokens=2048):
    """Call Qwen Cloud API when local is unavailable."""
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
            return json.loads(resp.read())
    except Exception as e:
        print(red(f"Qwen Cloud error: {e}"))
        return None

def start_process(agent_name):
    """Start an agent server in background."""
    cfg = AGENTS[agent_name]
    port = cfg["port"]

    if check_running(port):
        print(green(f"{cfg['desc']} already running on port {port}"))
        return True

    model_dir = cfg["dir"]
    model = None
    mmproj = None

    if cfg["type"] == "diffusion":
        model = find_model(model_dir)
        if not model:
            print(red(f"GGUF model not found in {model_dir}"))
            print(yellow("Diffusion requires a .gguf model file (safetensors not supported)"))
            return False
    else:
        model = find_model(model_dir)
        if cfg["type"] == "vlm":
            mmproj = find_mmproj(model_dir)

    if not model:
        print(red(f"Model not found: {model_dir}"))
        return False

    print(cyan(f"Starting {cfg['desc']}..."))
    print(cyan(f"  Model: {model}"))
    print(cyan(f"  Port: {port}"))

    if agent_name == "natsume":
        cmd = [str(LLAMA_BIN / "llama-server"),
               "-m", model,
               "--threads", str(THREADS), "--ctx-size", str(CTX),
               "--n-gpu-layers", "0", "--flash-attn", "on", "--jinja",
               "--port", str(port), "--host", HOST]
    elif agent_name == "sharaku":
        cmd = [str(LLAMA_BIN / "llama-server"),
               "-m", model,
               "--threads", str(THREADS), "--ctx-size", str(CTX),
               "--n-gpu-layers", "0", "--flash-attn", "on", "--jinja",
               "--port", str(port), "--host", HOST]
        if mmproj:
            print(cyan(f"  MMProj: {mmproj}"))
            cmd += ["--mmproj", mmproj]
    elif agent_name == "hokusai":
        cmd = [str(LLAMA_BIN / "llama-diffusion-cli"),
               "-m", model,
               "--port", str(port), "--host", HOST]
    else:
        return False

    # Start in background
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for ready (diffusion takes longest)
    max_wait = 90 if cfg["type"] == "diffusion" else 60
    waited = 0
    while waited < max_wait:
        time.sleep(1)
        waited += 1
        # For diffusion, also check if process is alive
        if cfg["type"] == "diffusion":
            if proc.poll() is not None:
                print(red(f"{agent_name} process exited"))
                return False
        if check_running(port):
            # Model endpoint is up, but give it a moment to stabilize
            time.sleep(2)
            # Verify it can actually handle a simple request
            test_resp = api_get(port, "/v1/models")
            if test_resp:
                print(green(f"{cfg['desc']} ready ({waited}s)"))
                return True
        if waited % 5 == 0:
            print(".", end="", flush=True)
    print()
    print(red(f"Timeout starting {agent_name} ({waited}s)"))
    proc.kill()
    return False

def stop_process(agent_name):
    """Stop an agent server."""
    cfg = AGENTS[agent_name]
    port = cfg["port"]
    try:
        # Find PID using ss
        r = subprocess.run(
            ["ss", "-tlnp"], capture_output=True, text=True
        )
        for line in r.stdout.splitlines():
            if f":{port} " in line:
                # Extract PID
                import re
                m = re.search(r'pid=(\d+)', line)
                if m:
                    pid = int(m.group(1))
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                    print(green(f"Stopped {agent_name} (pid {pid})"))
                    return True
        print(yellow(f"{agent_name} not running"))
    except Exception as e:
        print(red(f"Error stopping {agent_name}: {e}"))
    return False

# ---- Commands ----
def cmd_status():
    sep()
    print(cyan("三人衆 - Status"))
    sep()
    for name, cfg in AGENTS.items():
        if check_running(cfg["port"]):
            print(green(f"  ✓ {name} (port {cfg['port']}) RUNNING"))
        else:
            print(yellow(f"  ✗ {name} (port {cfg['port']}) stopped"))
    print()

def cmd_start(target="all"):
    if target == "all":
        for a in AGENTS:
            cmd_start(a)
        return
    if target not in AGENTS:
        print(red(f"Unknown agent: {target}"))
        return
    start_process(target)

def cmd_stop(target="all"):
    if target == "all":
        for a in AGENTS:
            cmd_stop(a)
        return
    if target not in AGENTS:
        print(red(f"Unknown agent: {target}"))
        return
    stop_process(target)

def cmd_chat():
    port = AGENTS["natsume"]["port"]
    if not check_running(port):
        print(yellow("夏目 not running. Starting..."))
        if not start_process("natsume"):
            return

    sep()
    print(cyan("Chat with 夏目"))
    sep()
    print(cyan("Type exit/quit to end"))
    print()

    messages = []
    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print(green("Goodbye!"))
            break

        if user_input in ("exit", "quit"):
            print(green("Goodbye!"))
            break
        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})
        resp = api_post(port, "/v1/chat/completions", {
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.7
        })

        if resp and resp.get("choices"):
            reply = resp["choices"][0]["message"]["content"]
            print()
            print(yellow(f"夏目: {reply}"))
            print()
            messages.append({"role": "assistant", "content": reply})
        else:
            print(red("No response from server"))

def cmd_skills():
    sep()
    print(cyan("Available Skills"))
    sep()
    print()
    print(f"{'ID':<12} {'Agent':<8} {'Description'}")
    print(f"{'---':<12} {'-----':<8} {'-----------'}")
    info = {
        "theory":     ("夏目", "Literary theory and writing philosophy"),
        "novel":      ("夏目", "Novel writing advice and techniques"),
        "haiku":      ("夏目", "Japanese poetry"),
        "hoshi":      ("星", "SF short-short stories"),
        "takuboku":   ("啄木", "File org, memo reading, chores"),
        "torahiko":   ("寅彦", "Coding, engineering, science"),
        "kiyoshi":    ("岡潔", "Math beauty and passion"),
        "vision":     ("写楽", "Image analysis, OCR"),
        "imagen":     ("北斎", "Image generation"),
    }
    for sid, (agent, desc) in info.items():
        print(f"{sid:<12} {agent:<8} {desc}")
    print()

def cmd_skill(skill_name, prompt):
    if skill_name not in SKILLS:
        print(red(f"Unknown skill: {skill_name}"))
        cmd_skills()
        return

    sk = SKILLS[skill_name]
    agent = sk["agent"]
    port = AGENTS[agent]["port"]

    if not check_running(port):
        print(yellow(f"Starting {agent}..."))
        if not start_process(agent):
            return

    msgs = []
    if sk["sys"]:
        msgs.append({"role": "system", "content": sk["sys"]})
    msgs.append({"role": "user", "content": prompt})

    resp = api_post(port, "/v1/chat/completions", {
        "messages": msgs,
        "max_tokens": sk["max"],
        "temperature": sk["temp"]
    })

    if resp and resp.get("choices"):
        print(resp["choices"][0]["message"]["content"])
    else:
        print(red("No response"))

def cmd_imagen(prompt):
    port = AGENTS["hokusai"]["port"]
    output = os.environ.get("YAO_IMAGEN_OUTPUT", "output.png")

    if not check_running(port):
        print(yellow("Starting 北斎..."))
        if not start_process("hokusai"):
            return

    print(cyan(f"Generating: {prompt}"))
    print(cyan(f"Output: {output}"))

    try:
        body = json.dumps({"prompt": prompt, "n": 1, "size": "512x512"})
        with open(output, "wb") as f:
            r = subprocess.run(
                ["curl", "-sf", f"http://{HOST}:{port}/v1/images/generations",
                 "-H", "Content-Type: application/json", "-d", body],
                stdout=f, timeout=120
            )
        if os.path.getsize(output) > 0:
            print(green(f"Saved: {output}"))
        else:
            print(red("Failed to generate image"))
    except Exception as e:
        print(red(f"Error: {e}"))

def cmd_health():
    sep()
    print(cyan("Health Check"))
    sep()
    print()

    # llama.cpp version
    try:
        r = subprocess.run(
            [str(LLAMA_BIN / "llama-server"), "--version"],
            capture_output=True, text=True, timeout=5
        )
        ver = (r.stdout.strip() or r.stderr.strip()).split("\n")[0] if (r.stdout or r.stderr) else "unknown"
        print(f"llama.cpp: {ver}")
    except:
        print(f"llama.cpp: NOT FOUND at {LLAMA_BIN}")
    print()

    print(cyan("Models:"))
    for name, cfg in AGENTS.items():
        if cfg["dir"].is_dir():
            print(green(f"  ✓ {name}: {cfg['dir']}"))
        else:
            print(red(f"  ✗ {name}: NOT FOUND ({cfg['dir']})"))
    print()
    cmd_status()

def cmd_help():
    sep()
    print(cyan("yao - Unified Offline LLM CLI"))
    sep()
    print()
    print("Usage: yao [command] [args]")
    print()
    print("  (no args)       Start all agents (default)")
    print("  status          Show all agents")
    print("  start [agent]   Start (natsume|sharaku|hokusai|all)")
    print("  stop [agent]    Stop agent")
    print("  chat            Chat with 夏目 (auto-starts)")
    print("  skills          List skills")
    print("  skill <id> <prompt>  Run skill")
    print("  imagen <prompt>      Generate image (北斎)")
    print("  generate <prompt>    Same as imagen")
    print("  health          System health check")
    print("  offline         Qwen Code offline gateway")
    print("  baku [N]        Dream-eater: breed N new ideas from memos")
    print("  baku-scan       Show top memos (meta index)")
    print("  baku-match      Show interesting pairings")
    print("  setup-offline   Config Qwen Code -> local model")
    print("  setup-online    Config Qwen Code -> cloud")
    print("  setup-mcp       Config Qwen Code -> yao MCP (stdio)")
    print("  mcp             Start MCP stdio server")
    print("  help            This message")
    print()
    print("Examples:")
    print("  yao start natsume")
    print("  yao start all")
    print("  yao chat")
    print("  yao skill writer 'Write about spring'")
    print("  yao skill coder 'Write a fibonacci function'")
    print("  yao imagen 'moon over mountain'")
    print()
    print("Env: YAO_THREADS YAO_CTX YAO_IMAGEN_OUTPUT")
    print()

def cmd_offline():
    """Start Qwen Code offline gateway."""
    script_dir = Path(__file__).parent
    offline_script = script_dir / "offline.py"
    if not offline_script.exists():
        print(red(f"offline.py not found at {offline_script}"))
        return
    subprocess.run([sys.executable, str(offline_script)])

def cmd_baku(n=5):
    """Run baku dream-eater (smart breed from meta index)."""
    import platform
    is_wsl = "microsoft" in platform.release().lower() or "WSL" in platform.release()
    if is_wsl:
        subprocess.run(["python3", str(Path.home() / "baku" / "baku.py"), "breed", str(n)])
    else:
        wsl_cmd = f'python3 ~/baku/baku.py breed {n}'
        subprocess.run(["wsl", "bash", "-c", wsl_cmd])

def cmd_baku_scan():
    """Show memo overview."""
    import platform
    is_wsl = "microsoft" in platform.release().lower() or "WSL" in platform.release()
    if is_wsl:
        subprocess.run(["python3", str(Path.home() / "baku" / "baku.py"), "scan"])
    else:
        subprocess.run(["wsl", "bash", "-c", "python3 ~/baku/baku.py scan"])

def cmd_baku_match():
    """Show interesting pairings."""
    import platform
    is_wsl = "microsoft" in platform.release().lower() or "WSL" in platform.release()
    if is_wsl:
        subprocess.run(["python3", str(Path.home() / "baku" / "baku.py"), "match"])
    else:
        subprocess.run(["wsl", "bash", "-c", "python3 ~/baku/baku.py match"])

def _qwen_settings_path():
    """Find Qwen Code settings.json."""
    candidates = [
        HOME / ".qwen" / "settings.json",
        Path("/mnt/c/Users/dance/.qwen/settings.json"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

def cmd_setup_offline():
    """Configure Qwen Code to use local model."""
    settings = _qwen_settings_path()
    if not settings:
        print(red("Qwen Code settings.json not found"))
        return

    with open(settings) as f:
        cfg = json.load(f)

    cfg["security"] = {"auth": {"selectedType": "openai"}}
    cfg["customProviders"] = {
        "local": {
            "baseUrl": f"http://{HOST}:{LOCAL_PORT}/v1",
            "apiKey": "local",
            "models": ["qwen3-8b"]
        }
    }
    cfg["model"] = {"name": "qwen3-8b", "provider": "local"}

    with open(settings, "w") as f:
        json.dump(cfg, f, indent=2)

    print(green(f"Qwen Code configured for offline mode (local: {HOST}:{LOCAL_PORT})"))
    print(yellow("Now run: yao start natsume"))

def cmd_setup_online():
    """Restore Qwen Code to cloud mode."""
    settings = _qwen_settings_path()
    if not settings:
        print(red("Qwen Code settings.json not found"))
        return

    with open(settings) as f:
        cfg = json.load(f)

    cfg["security"] = {"auth": {"selectedType": "qwen-oauth"}}
    cfg.pop("customProviders", None)
    cfg.pop("model", None)

    with open(settings, "w") as f:
        json.dump(cfg, f, indent=2)

    print(green("Qwen Code configured for cloud mode"))

def cmd_setup_mcp():
    """Configure Qwen Code to use three separate yao MCP servers (stdio)."""
    settings = _qwen_settings_path()
    if not settings:
        print(red("Qwen Code settings.json not found"))
        return

    with open(settings) as f:
        cfg = json.load(f)

    cfg.pop("mcpServers", None)
    cfg["mcpServers"] = {
        "natsume": {
            "command": "wsl",
            "args": ["bash", "-c", "python3 ~/yao/yao-mcp.py --agent natsume"],
            "timeout": 300000,
            "trust": True,
            "description": "夏目 - Qwen3 8B 文学論・小説・俳句"
        },
        "takuboku": {
            "command": "wsl",
            "args": ["bash", "-c", "python3 ~/yao/yao-mcp.py --agent takuboku"],
            "timeout": 300000,
            "trust": True,
            "description": "啄木 - Qwen3 8B 雑用・ファイル整理"
        },
        "torahiko": {
            "command": "wsl",
            "args": ["bash", "-c", "~/yao/yao-mcp.py --agent torahiko"],
            "timeout": 300000,
            "trust": True,
            "description": "寅彦 - Qwen3 8B コーディング・理系"
        },
        "kiyoshi": {
            "command": "wsl",
            "args": ["bash", "-c", "~/yao/yao-mcp.py --agent kiyoshi"],
            "timeout": 300000,
            "trust": True,
            "description": "岡潔 - Qwen3 8B 数学の美"
        },
        "hoshi": {
            "command": "wsl",
            "args": ["bash", "-c", "~/yao/yao-mcp.py --agent hoshi"],
            "timeout": 300000,
            "trust": True,
            "description": "星新一 - Qwen3 8B ショートショート"
        },
        "sharaku": {
            "command": "wsl",
            "args": ["bash", "-c", "~/yao/yao-mcp.py --agent sharaku"],
            "timeout": 300000,
            "trust": True,
            "description": "写楽 - Qwen2.5-VL 3B ビジョン"
        },
        "hokusai": {
            "command": "wsl",
            "args": ["bash", "-c", "~/yao/yao-mcp.py --agent hokusai"],
            "timeout": 300000,
            "trust": True,
            "description": "北斎 - SD1.5 画像生成"
        },
    }

    with open(settings, "w") as f:
        json.dump(cfg, f, indent=2)

    print(green("Qwen Code configured with 7 MCP servers: natsume, takuboku, torahiko, kiyoshi, hoshi, sharaku, hokusai"))
    print(yellow("Restart Qwen Code to apply changes."))

def cmd_mcp():
    """Start MCP stdio server for Qwen Code."""
    script_dir = Path(__file__).parent
    mcp_script = script_dir / "yao-mcp.py"
    if not mcp_script.exists():
        print(red(f"yao-mcp.py not found at {mcp_script}"))
        return
    print(cyan("yao - MCP Server (stdio)"))
    print(cyan("Auto-starts agents on demand."))
    print(cyan(f"Agents: 夏目({AGENTS['natsume']['port']}) 写楽({AGENTS['sharaku']['port']}) 北斎({AGENTS['hokusai']['port']})"))
    print()
    subprocess.run([sys.executable, str(mcp_script)])

# ---- Main ----
def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "_start_all"

    dispatch = {
        "_start_all": lambda: cmd_start("all"),
        "status": lambda: cmd_status(),
        "st": lambda: cmd_status(),
        "start": lambda: cmd_start(args[1] if len(args) > 1 else "all"),
        "stop": lambda: cmd_stop(args[1] if len(args) > 1 else "all"),
        "chat": lambda: cmd_chat(),
        "skills": lambda: cmd_skills(),
        "ls": lambda: cmd_skills(),
        "skill": lambda: cmd_skill(args[1], " ".join(args[2:])) if len(args) > 2 else print(red("Usage: yao skill <id> <prompt>")),
        "run": lambda: cmd_skill(args[1], " ".join(args[2:])) if len(args) > 2 else print(red("Usage: yao run <id> <prompt>")),
        "generate": lambda: cmd_imagen(" ".join(args[1:])),
        "gen": lambda: cmd_imagen(" ".join(args[1:])),
        "imagen": lambda: cmd_imagen(" ".join(args[1:])),
        "img": lambda: cmd_imagen(" ".join(args[1:])),
        "offline": lambda: cmd_offline(),
        "baku": lambda: cmd_baku(int(args[1]) if len(args) > 1 and args[1].isdigit() else 5),
        "baku-scan": lambda: cmd_baku_scan(),
        "baku-match": lambda: cmd_baku_match(),
        "setup-offline": lambda: cmd_setup_offline(),
        "setup-online": lambda: cmd_setup_online(),
        "setup-mcp": lambda: cmd_setup_mcp(),
        "health": lambda: cmd_health(),
        "mcp": lambda: cmd_mcp(),
        "help": lambda: cmd_help(),
        "--help": lambda: cmd_help(),
        "-h": lambda: cmd_help(),
    }

    fn = dispatch.get(cmd)
    if fn:
        fn()
    else:
        print(red(f"Unknown: {cmd}"))
        cmd_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
