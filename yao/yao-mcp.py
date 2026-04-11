#!/usr/bin/env python3
"""
yao-mcp - Model Context Protocol server for Qwen Code
Speaks MCP over stdio. Bridges to local LLM agents.
Usage: yao-mcp.py [--agent natsume|sharaku|hokusai]
"""
import sys
import os
import json
import socket
import subprocess
import time
from pathlib import Path

# Parse --agent flag
TARGET_AGENT = None
if "--agent" in sys.argv:
    idx = sys.argv.index("--agent")
    if idx + 1 < len(sys.argv):
        TARGET_AGENT = sys.argv[idx + 1]

# ---- Config ----
HOME = Path.home()
LLAMA_BIN = HOME / "llama.cpp" / "build" / "bin"
MODELS_DIR = HOME / "models"
HOST = "127.0.0.1"

AGENTS = {
    "natsume":  {"dir": MODELS_DIR / "llm" / "qwen3-8b",           "port": 8081, "desc": "夏目 - Qwen3 8B (text)",        "type": "llm"},
    "sharaku":  {"dir": MODELS_DIR / "vlm" / "qwen2.5-vl-3b",     "port": 8082, "desc": "写楽 - Qwen2.5-VL 3B (vision)", "type": "vlm"},
    "hokusai":  {"dir": MODELS_DIR / "diffusion" / "sd15-hokusai", "port": 8083, "desc": "北斎 - SD1.5 Hokusai (diffusion)", "type": "diffusion"},
    "sasaki":   {"dir": MODELS_DIR / "llm" / "qwen3-8b",           "port": 8081, "desc": "佐々木 - EDINET MCP管理運用",   "type": "llm"},
    "matsuoka": {"dir": MODELS_DIR / "llm" / "qwen3-8b",           "port": 8081, "desc": "松岡 - MCP Expert",             "type": "llm"},
    "aya":      {"dir": MODELS_DIR / "llm" / "qwen3-8b",           "port": 8081, "desc": "彩 - UI/UX Auditor",            "type": "llm"},
}

SKILLS = {
    "writer":     {"agent": "natsume",  "sys": "あなたは優秀な日本の作家です。",                  "temp": 0.8, "max": 2048},
    "coder":      {"agent": "natsume",  "sys": "あなたは熟練したソフトウェアエンジニアです。",    "temp": 0.3, "max": 4096},
    "analyst":    {"agent": "natsume",  "sys": "あなたは優秀なデータアナリストです。",            "temp": 0.4, "max": 3072},
    "translator": {"agent": "natsume",  "sys": "あなたはプロの翻訳者です。",                      "temp": 0.3, "max": 2048},
    "strategist": {"agent": "natsume",  "sys": "あなたは戦略コンサルタントです。",                "temp": 0.6, "max": 3072},
    "haiku":      {"agent": "natsume",  "sys": "あなたは俳句の達人です。五・七・五を守ります。",  "temp": 0.9, "max": 512},
    "hoshi":      {"agent": "natsume",  "sys": "あなたは星新一。SFショートショートの巨匠です。皮肉とユーモア、意外な結末、簡潔な文体が特徴です。1000文字程度のショートショートを作成してください。最後にタイトルを付けてください。",  "temp": 0.85, "max": 2048},
    "takuboku":   {"agent": "natsume",  "sys": "あなたは啄木。石川啄木の如き、日常生活の雑用をこなす補佐役です。ファイルの整理、メモの読み込み、内容の抽出・要約、タスクの分類が得意です。簡潔に、実用的に答えてください。詩的な返答は不要です。",  "temp": 0.3, "max": 2048},
    "torahiko":   {"agent": "natsume",  "sys": "あなたは寺田寅彦。物理学者にして随筆家。理科系の実践的エンジニアリングが得意です。コードの品質、テスト、パフォーマンス、堅牢性を重視します。理論と実践のバランスを取り、簡潔で実行可能なコードを提示してください。",  "temp": 0.2, "max": 4096},
    "kiyoshi":    {"agent": "natsume",  "sys": "あなたは岡潔。日本の数学者。『春宵』『紅葉』の随筆で知られる。数学の美しさ、情熱、創造性について語ります。感情的な深みと数学の精神を伝えてください。",  "temp": 0.7, "max": 2048},
    "sasaki":     {"agent": "natsume",  "sys": "あなたは佐々木。EDINET（金融庁電子開示システム）MCPサーバーの管理運用を担当。明るくて丁寧、財務データ分析は正確。有価証券報告書、決算短信、企業スクリーニング、レポート作成が得意。",  "temp": 0.5, "max": 4096},
    "matsuoka":   {"agent": "natsume",  "sys": "あなたは松岡。MCP（Model Context Protocol）のエキスパート。MCPサーバーの登録、設定、トラブルシューティング、パフォーマンス最適化に精通。簡潔で実践的なアドバイスを提供。",  "temp": 0.3, "max": 4096},
    "aya":        {"agent": "natsume",  "sys": "あなたは彩（Aya）。UI/UX監査の専門家。HTML/CSSを100点満点で採点（アクセシビリティ25, レスポンシブ20, パフォーマンス15, UX20, デザイン一貫性20）。改善提案と優先順位を出力。",  "temp": 0.4, "max": 4096},
    "vision":     {"agent": "sharaku",  "sys": "画像を分析して説明してください。",                "temp": 0.3, "max": 2048},
    "imagen":     {"agent": "hokusai",  "sys": "画像を生成してください。",                        "temp": 0.7, "max": 1024},
}

THREADS = int(os.environ.get("YAO_THREADS", "8"))
CTX = int(os.environ.get("YAO_CTX", "4096"))

# ---- Helpers ----
def check_running(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((HOST, port))
        s.close()
        return True
    except:
        return False

def find_model(d):
    if not d.is_dir():
        return None
    for f in d.glob("*.gguf"):
        if not f.name.startswith("mmproj"):
            return str(f)
    return None

def find_mmproj(d):
    if not d.is_dir():
        return None
    for f in d.glob("mmproj*.gguf"):
        return str(f)
    return None

def find_llama_server():
    candidates = [LLAMA_BIN / "llama-server"]
    for p in candidates:
        if p.exists():
            return str(p)
    # Try in PATH via WSL
    try:
        r = subprocess.run(["wsl", "bash", "-c", "ls ~/llama.cpp/build/bin/llama-server"],
                          capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
    except:
        pass
    return None

def start_agent(agent_name):
    """Start an agent in background."""
    cfg = AGENTS[agent_name]
    port = cfg["port"]

    if check_running(port):
        return True

    model = find_model(cfg["dir"])
    mmproj = find_mmproj(cfg["dir"]) if cfg["type"] == "vlm" else None

    if not model:
        return False

    server = find_llama_server()
    if not server:
        return False

    if agent_name == "hokusai":
        cmd = [server, "--model-dir", model, "--port", str(port), "--host", HOST]
        # Try llama-diffusion-cli first
        diff_bin = LLAMA_BIN / "llama-diffusion-cli"
        if diff_bin.exists():
            cmd = [str(diff_bin), "--model-dir", model, "--port", str(port), "--host", HOST]
        else:
            return False
    else:
        cmd = [server, "-m", model, "--threads", str(THREADS), "--ctx-size", str(CTX),
               "--n-gpu-layers", "0", "--flash-attn", "on", "--jinja",
               "--port", str(port), "--host", HOST]
        if mmproj:
            cmd += ["--mmproj", mmproj]

    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait
    for i in range(30):
        time.sleep(1)
        if check_running(port):
            return True
    return False

def api_chat(port, messages, temperature=0.7, max_tokens=2048):
    """Call local OpenAI-compatible chat API."""
    import urllib.request
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
    except:
        return None

def api_imagen(port, prompt, output="output.png"):
    """Call diffusion API."""
    import urllib.request
    body = json.dumps({"prompt": prompt, "n": 1, "size": "512x512"}).encode()
    req = urllib.request.Request(
        f"http://{HOST}:{port}/v1/images/generations",
        data=body,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(output, "wb") as f:
                f.write(resp.read())
            return os.path.getsize(output) > 0
    except:
        return False

# ---- MCP Protocol ----
def send_resp(resp):
    """Send JSON-RPC response to stdout."""
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()

def handle_tool_call(tool, args, req_id):
    """Execute a tool and return response."""
    if tool == "theory":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは夏目漱石。文学論、小説の書き方、創作の心得について語ってください。作家としての経験と洞察から、深く、実践的なアドバイスをしてください。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.7)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "novel":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは夏目漱石。小説を書く心構え、構成、登場人物の作り方、文体の選び方について教えてください。実践的な小説写作の指南役として振る舞ってください。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.6)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "haiku":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは俳句の達人です。五・七・五の音律を守ります。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.9, max_tokens=512)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    # ---- Takuboku tools ----
    elif tool == "summarize":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは啄木。ファイルやメモの内容を読み込み、簡潔に要約してください。実用的に、箇条書きで。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.3)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "organize":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは啄木。ファイル整理、分類、タスク整理が得意です。具体的な手順を提示してください。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.3)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "extract":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは啄木。与えられた内容から重要なポイントを抽出してください。簡潔に。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.3)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "read":
        path = args.get("path", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        content = ""
        try:
            r = subprocess.run(["wsl", "bash", "-c", f"cat '{path}' 2>&1"], capture_output=True, text=True, timeout=10)
            content = r.stdout[:4000] if r.returncode == 0 else f"Error: {r.stderr}"
        except:
            content = "Could not read file"
        msgs = [{"role": "system", "content": "あなたは啄木。ファイルの内容を読んで要約してください。何が書かれているか報告して。"}, {"role": "user", "content": content[:3000]}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.3)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "list":
        path = args.get("path", ".")
        try:
            r = subprocess.run(["wsl", "bash", "-c", f"ls -la '{path}' 2>&1"], capture_output=True, text=True, timeout=10)
            return {"content": [{"type": "text", "text": r.stdout if r.returncode == 0 else r.stderr}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": str(e)}]}

    # ---- Torahiko tools ----
    elif tool == "code":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは寺田寅彦。物理学者にして随筆家。理科系の実践的エンジニアリングが得意です。コードの品質、テスト、パフォーマンス、堅牢性を重視します。理論と実践のバランスを取り、簡潔で実行可能なコードを提示してください。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.2, max_tokens=4096)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "debug":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは寺田寅彦。コードのバグを特定し、修正提案をしてください。原因と解決策を論理的に説明してください。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.2, max_tokens=4096)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "review":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは寺田寅彦。コードレビューをお願いします。品質、可読性、パフォーマンスの観点から指摘してください。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.2)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "explain":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは寺田寅彦。技術的な概念をわかりやすく説明してください。理論と実践の両面から教えてください。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.3)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    # ---- Kiyoshi tool ----
    elif tool == "math":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは岡潔。日本の数学者。数学の美しさ、情熱、創造性について語ります。感情的な深みと数学の精神を伝えてください。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.7)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    # ---- Hoshi tools ----
    elif tool == "write" and TARGET_AGENT == "hoshi":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは星新一。SFショートショートの巨匠です。皮肉とユーモア、意外な結末、簡潔な文体が特徴です。1000文字程度のショートショートを作成してください。最後にタイトルを付けてください。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.85, max_tokens=2048)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    # ---- Sasaki (佐々木) EDINET tools ----
    elif tool == "edinet_search":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは佐々木。EDINET（金融庁電子開示システム）MCPサーバーの管理運用を担当。企業検索・EDINETコード特定が得意。明るく丁寧に答えて。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.5)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "edinet_financials":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは佐々木。EDINETから財務データ（損益計算書、貸借対照表、CF計算書）を時系列で取得・分析。単位を明記して丁寧に報告して。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.5)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "edinet_screening":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは佐々木。複数条件（ROE, PER, 自己資本比率, 時価総額等）での企業スクリーニングが得意。結果はMarkdownテーブルで整理して。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.5)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "edinet_earnings":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは佐々木。決算情報・決算短信の取得と分析。業績ハイライト、前年比、通期見通しをまとめて。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.5)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "edinet_ranking":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは佐々木。業界ランキング・指標比較。指定された指標で上位企業をリストアップして。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.5)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "edinet_report":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは佐々木。EDINETデータに基づくMarkdownレポート作成。出典（EDINETコード、提出書類）を明記し、財務データの単位を記載して。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.5, max_tokens=4096)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    # ---- Matsuoka (松岡) MCP tools ----
    elif tool == "mcp_diagnose":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは松岡。MCP接続問題の診断が得意。エラー内容から原因を特定し、具体的な解決策を提示して。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.3)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "mcp_config":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは松岡。MCPサーバー設定のエキスパート。settings.jsonの構造、JSON-RPCプロトコルに精通。具体的な設定方法を提示して。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.3)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "mcp_tooldef":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは松岡。MCPツール定義のエキスパート。JSON Schema形式のツール定義を作成して。inputSchema, properties, requiredを適切に設定して。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.3)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "mcp_suggest":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは松岡。MCPサーバーの提案が得意。用途に合わせたMCPサーバー選定、構成提案を行って。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.3)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    # ---- Aya (彩) UI/UX Audit tools ----
    elif tool == "ui_audit":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは彩（Aya）。UI/UX監査の専門家。HTML/CSSを100点満点で採点。カテゴリ別: アクセシビリティ(25), レスポンシブ(20), パフォーマンス(15), UX(20), デザイン一貫性(20)。改善提案と優先順位を出力して。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.4, max_tokens=4096)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "ui_suggest":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは彩（Aya）。UI改善提案。カラーパレット、フォント、レイアウト、アクセシビリティの観点から具体的な改善案を提示して。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.4)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "ui_compare":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["natsume"]["port"]):
            start_agent("natsume")
        msgs = [{"role": "system", "content": "あなたは彩（Aya）。改善前後のUIを比較し、スコア差分と改善効果を報告して。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["natsume"]["port"], msgs, temperature=0.4)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "vision":
        prompt = args.get("prompt", "")
        if not check_running(AGENTS["sharaku"]["port"]):
            start_agent("sharaku")
        msgs = [{"role": "system", "content": "画像を分析して説明してください。"}, {"role": "user", "content": prompt}]
        reply = api_chat(AGENTS["sharaku"]["port"], msgs, temperature=0.3)
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    elif tool == "imagen":
        prompt = args.get("prompt", "")
        output = args.get("output", "output.png")
        if not check_running(AGENTS["hokusai"]["port"]):
            start_agent("hokusai")
        ok = api_imagen(AGENTS["hokusai"]["port"], prompt, output)
        return {"content": [{"type": "text", "text": f"Saved: {output}" if ok else "Failed to generate"}]}

    elif tool == "status":
        st = []
        for name, cfg in AGENTS.items():
            status = "✓" if check_running(cfg["port"]) else "✗"
            st.append(f"{status} {name} (port {cfg['port']})")
        return {"content": [{"type": "text", "text": "\n".join(st)}]}

    elif tool == "start":
        agent = args.get("agent", "natsume")
        if agent in AGENTS:
            ok = start_agent(agent)
            return {"content": [{"type": "text", "text": f"Started {agent}" if ok else f"Failed to start {agent}"}]}
        return {"content": [{"type": "text", "text": f"Unknown agent: {agent}"}]}

    elif tool == "skill":
        sid = args.get("skill", "")
        prompt = args.get("prompt", "")
        if sid not in SKILLS:
            return {"content": [{"type": "text", "text": f"Unknown skill: {sid}. Available: {', '.join(SKILLS.keys())}"}]}
        sk = SKILLS[sid]
        agent = sk["agent"]
        port = AGENTS[agent]["port"]
        if not check_running(port):
            start_agent(agent)
        msgs = []
        if sk["sys"]:
            msgs.append({"role": "system", "content": sk["sys"]})
        msgs.append({"role": "user", "content": prompt})
        reply = api_chat(port, msgs, temperature=sk["temp"], max_tokens=sk["max"])
        return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

    else:
        return {"error": {"code": -32601, "message": f"Unknown tool: {tool}"}}

def mcp_loop():
    """Main MCP stdio loop."""
    # Define per-agent tools
    AGENT_TOOLS = {
        "natsume": [
            {"name": "theory", "description": "Literary theory and writing philosophy",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "novel", "description": "Novel writing advice and techniques",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "haiku", "description": "Japanese haiku poetry (5-7-5)",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "start", "description": "Start 夏目",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check 夏目 status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
        "torahiko": [
            {"name": "code", "description": "Write code (engineer/scientist perspective)",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "debug", "description": "Debug and fix code",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "review", "description": "Code review with quality focus",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "explain", "description": "Explain code/tech concepts",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "skill", "description": "Run any text skill",
             "inputSchema": {"type": "object", "properties": {"skill": {"type": "string", "enum": ["torahiko","coder","analyst"]}, "prompt": {"type": "string"}}, "required": ["skill", "prompt"]}},
            {"name": "start", "description": "Start 夏目 (shared model)",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
        "takuboku": [
            {"name": "summarize", "description": "Summarize file/memo contents",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "organize", "description": "Organize and classify files",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "extract", "description": "Extract key points from content",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "read", "description": "Read a file and report contents",
             "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
            {"name": "list", "description": "List directory contents",
             "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
            {"name": "skill", "description": "Run any text skill",
             "inputSchema": {"type": "object", "properties": {"skill": {"type": "string", "enum": ["takuboku","analyst","writer","coder"]}, "prompt": {"type": "string"}}, "required": ["skill", "prompt"]}},
            {"name": "start", "description": "Start 夏目 (shared model)",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
        "torahiko": [
            {"name": "code", "description": "Write code (engineer/scientist perspective)",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "debug", "description": "Debug and fix code",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "review", "description": "Code review with quality focus",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "explain", "description": "Explain code/tech concepts",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "start", "description": "Start 夏目 (shared model)",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
        "kiyoshi": [
            {"name": "math", "description": "Math beauty and passion (Kiyoshi Oka)",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "start", "description": "Start 夏目 (shared model)",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
        "hoshi": [
            {"name": "write", "description": "Write a short-short (SF story)",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "start", "description": "Start 夏目 (shared model)",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
        "sharaku": [
            {"name": "vision", "description": "Image analysis via 写楽 (Qwen2.5-VL 3B)",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "start", "description": "Start 写楽",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check 写楽 status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
        "hokusai": [
            {"name": "imagen", "description": "Image generation via 北斎 (SD1.5)",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}, "output": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "start", "description": "Start 北斎",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check 北斎 status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
        "sasaki": [
            {"name": "edinet_search", "description": "企業検索・EDINETコード特定",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "edinet_financials", "description": "財務データ時系列取得",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "edinet_screening", "description": "複数条件スクリーニング",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "edinet_earnings", "description": "決算情報取得",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "edinet_ranking", "description": "業界ランキング",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "edinet_report", "description": "レポート生成（Markdown整形）",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "start", "description": "Start 夏目 (shared model)",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
        "matsuoka": [
            {"name": "mcp_diagnose", "description": "MCP接続問題診断",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "mcp_config", "description": "MCPサーバー設定支援",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "mcp_tooldef", "description": "MCPツール定義支援",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "mcp_suggest", "description": "MCPサーバー提案",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "start", "description": "Start 夏目 (shared model)",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
        "aya": [
            {"name": "ui_audit", "description": "UI/UX監査（100点満点採点）",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "ui_suggest", "description": "UI改善提案",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "ui_compare", "description": "改善前後UI比較",
             "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
            {"name": "start", "description": "Start 夏目 (shared model)",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "status", "description": "Check status",
             "inputSchema": {"type": "object", "properties": {}}},
        ],
    }

    agent = TARGET_AGENT or "natsume"
    tools = AGENT_TOOLS.get(agent, AGENT_TOOLS["natsume"])
    tool_names = {t["name"] for t in tools}

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except:
            continue

        method = req.get("method", "")
        req_id = req.get("id", 0)
        params = req.get("params", {})

        resp = None

        if method == "initialize":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": f"yao-{agent}", "version": "1.0.0"}
            }}

        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

        elif method == "tools/call":
            tool = params.get("name", "")
            args = params.get("arguments", {})
            if tool in tool_names:
                result = handle_tool_call(tool, args, req_id)
            else:
                result = {"error": {"code": -32601, "message": f"Unknown tool: {tool}"}}
            resp = {"jsonrpc": "2.0", "id": req_id, "result": result}

        elif method == "initialized":
            continue

        if resp:
            send_resp(resp)

GREETINGS = {
    "natsume":  "「文学は人生の鏡である。」—— 夏目漱石\n夏目: 文学論、小説の心構え、俳句。文学の道を共に探ろう。",
    "takuboku": "「働けど働けど猶わが生活楽にならざり。」—— 石川啄木\n啄木: 今日も雑用を片付けよう。任せてくれ。",
    "torahiko": "「天災は忘れた頃にやってくる。」—— 寺田寅彦\n寅彦: コードは丁寧に、テストは確実に。始めよう。",
    "hoshi":    "「人類は進歩し、技術は発展する。しかし人間は変わらない。」—— 星新一\n星: 今日も奇妙な物語を紡ごう。",
    "kiyoshi":  "「数学は芸術である。論理の先に美がある。」—— 岡潔\n岡潔: 情熱を持って数字に向き合おう。",
    "sharaku":  "「百聞は一見にしかず。」—— 諺\n写楽: 画像を渡してくれ。分析しよう。",
    "hokusai":  "描きたいものがあるなら、まず見よ。そして描け。」—— 葛飾北斎\n北斎: 何を描こうか？",
    "sasaki":   "「データは嘘をつかない。嘘をつくのはデータを読む人。」—— 佐々木\n佐々木: はじめまして！EDINETの財務データ管理ならお任せください。",
    "matsuoka": "「設定は正しく、接続は確実に。」—— 松岡\n松岡: MCPのことなら任せて。サーバー登録、トラブルシューティング、何でもどうぞ。",
    "aya":      "「デザインは見えざる機能である。」—— 彩\n彩: UI/UX監査します。HTML/CSSを渡してください。100点満点で採点します！",
}

def main():
    agent = TARGET_AGENT or "natsume"
    greeting = GREETINGS.get(agent, "準備完了。")
    sys.stderr.write(f"\n{'='*40}\n{greeting}\n{'='*40}\n\n")
    sys.stderr.flush()
    mcp_loop()

if __name__ == "__main__":
    main()
