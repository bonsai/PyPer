#!/usr/bin/env python3
"""
PyPer MCP Advisor Server

On-demand server for LLM, law, and strategic advisor operations.
Start only when needed.

Tools:
  - yao: status, start, chat, skill, imagen
  - law: get_article, search, check_updates
  - advisor: sunzi, musashi, seven_sages
  - monju: deliberate
  - skill: writer, cleaner, file_ops, task_mgmt, journal, ocr, code_review, misc
"""
import sys
import os
import json
import subprocess
import urllib.request
import socket
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from plugins.mcp_base import MCPServer

# ========== Config ==========
HOME = Path.home()
HOST = "127.0.0.1"
YAO_DIR = Path(__file__).resolve().parents[2] / "yao"  # PyPer/yao
YAO_MCP = YAO_DIR / "yao-mcp.py"

AGENTS = {
    "natsume": {"port": 8081, "desc": "夏目 - Qwen3 8B (text)"},
    "sharaku": {"port": 8082, "desc": "写楽 - Qwen2.5-VL 3B (vision)"},
    "hokusai": {"port": 8083, "desc": "北斎 - SD1.5 (diffusion)"},
}

# ========== Server ==========
server = MCPServer("pyper-advisor", "1.0.0")

# ========== Yao Tools ==========
server.register_tool(
    name="yao_status",
    description="Check status of local LLM agents (夏目/写楽/北斎)",
    input_schema={"properties": {}, "required": []},
    handler=lambda: _yao_status()
)

def _yao_status():
    """Check which agents are running."""
    lines = []
    for name, cfg in AGENTS.items():
        running = _check_port(cfg["port"])
        status = "✓ RUNNING" if running else "✗ stopped"
        lines.append(f"{name} (port {cfg['port']}): {status}")
    return "\n".join(lines)

server.register_tool(
    name="yao_start",
    description="Start a local LLM agent",
    input_schema={
        "properties": {"agent": {"type": "string", "enum": ["natsume", "sharaku", "hokusai"], "default": "natsume"}},
        "required": []
    },
    handler=lambda agent="natsume": _yao_start(agent)
)

def _yao_start(agent):
    """Start an agent via yao.py."""
    yao_script = YAO_DIR / "yao.py"
    if not yao_script.exists():
        return f"yao.py not found at {YAO_DIR}"

    try:
        result = subprocess.run(
            [sys.executable, str(yao_script), "start", agent],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Failed to start {agent}: {str(e)}"

server.register_tool(
    name="yao_chat",
    description="Chat with 夏目 (local Qwen3 8B)",
    input_schema={
        "properties": {"prompt": {"type": "string", "description": "Message to send"}},
        "required": ["prompt"]
    },
    handler=lambda prompt: _yao_chat(prompt)
)

def _yao_chat(prompt):
    """Chat with natsume agent."""
    port = AGENTS["natsume"]["port"]
    if not _check_port(port):
        _yao_start("natsume")

    return _api_chat(port, [{"role": "user", "content": prompt}])

server.register_tool(
    name="yao_skill",
    description="Run a skill with 夏目 (writer, coder, analyst, etc.)",
    input_schema={
        "properties": {
            "skill": {"type": "string", "description": "Skill name (writer, coder, analyst, translator, strategist, haiku, etc.)"},
            "prompt": {"type": "string", "description": "Prompt for the skill"},
        },
        "required": ["skill", "prompt"]
    },
    handler=lambda skill, prompt: _yao_skill(skill, prompt)
)

def _yao_skill(skill, prompt):
    """Run a skill via natsume agent."""
    port = AGENTS["natsume"]["port"]
    if not _check_port(port):
        _yao_start("natsume")

    skills = {
        "writer": "あなたは優秀な日本の作家です。",
        "coder": "あなたは熟練したソフトウェアエンジニアです。",
        "analyst": "あなたは優秀なデータアナリストです。",
        "translator": "あなたはプロの翻訳者です。",
        "strategist": "あなたは戦略コンサルタントです。",
        "haiku": "あなたは俳句の達人です。五・七・五を守ります。",
    }

    sys_prompt = skills.get(skill, f"あなたは{skill}の専門家です。")
    return _api_chat(port, [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": prompt}
    ], temperature=0.7)

server.register_tool(
    name="yao_imagen",
    description="Generate image with 北斎 (local SD1.5)",
    input_schema={
        "properties": {
            "prompt": {"type": "string", "description": "Image generation prompt"},
            "output": {"type": "string", "default": "output.png"},
        },
        "required": ["prompt"]
    },
    handler=lambda prompt, output="output.png": _yao_imagen(prompt, output)
)

def _yao_imagen(prompt, output):
    """Generate image via hokusai agent."""
    port = AGENTS["hokusai"]["port"]
    if not _check_port(port):
        _yao_start("hokusai")

    body = json.dumps({"prompt": prompt, "n": 1, "size": "512x512"}).encode()
    req = urllib.request.Request(
        f"http://{HOST}:{port}/v1/images/generations",
        data=body,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            with open(output, "wb") as f:
                f.write(resp.read())
            return f"Saved: {output}"
    except Exception as e:
        return f"Failed: {str(e)}"

# ========== Law Tools ==========
server.register_tool(
    name="law_search",
    description="Search Japanese building regulations (e-Gov API)",
    input_schema={
        "properties": {
            "query": {"type": "string", "description": "Search keyword"},
            "law_name": {"type": "string", "description": "Specific law name (optional)"},
        },
        "required": ["query"]
    },
    handler=lambda query, law_name=None: _law_search(query, law_name)
)

def _law_search(query, law_name=None):
    """Search law via building-standards-act-mcp."""
    mcp_dir = Path(__file__).resolve().parents[2] / "MCP" / "building-standards-act-mcp"
    index_js = mcp_dir / "dist" / "index.js"
    if not index_js.exists():
        return f"building-standards-act-mcp not found at {mcp_dir}"

    # Call as subprocess with query
    try:
        result = subprocess.run(
            ["node", str(index_js)],
            input=json.dumps({"query": query, "law_name": law_name}),
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "MCP_ACTION": "search"}
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Law search error: {str(e)}"

server.register_tool(
    name="law_check_updates",
    description="Check for amendments in Japanese laws",
    input_schema={
        "properties": {
            "law_name": {"type": "string", "description": "Law name to check"},
        },
        "required": ["law_name"]
    },
    handler=lambda law_name: _law_check_updates(law_name)
)

def _law_check_updates(law_name):
    """Check law amendments via houki law_monitor."""
    monitor_dir = Path(__file__).resolve().parents[2] / "MCP" / "houki" / "agent_flow" / "law_monitor"
    monitor_py = monitor_dir / "monitor.py"
    if not monitor_py.exists():
        return f"law_monitor not found at {monitor_dir}"

    try:
        result = subprocess.run(
            [sys.executable, str(monitor_py), "--law", law_name],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Law check error: {str(e)}"

# ========== Advisor Tools ==========
server.register_tool(
    name="advisor_sunzi",
    description="Get strategic advice from Sun Tzu (兵法)",
    input_schema={
        "properties": {
            "question": {"type": "string", "description": "Strategic question"},
            "context": {"type": "string", "default": "project-start"},
        },
        "required": ["question"]
    },
    handler=lambda question, context="project-start": _advisor_sunzi(question, context)
)

def _advisor_sunzi(question, context):
    """Get advice from Sun Tzu via sunzi-vibe-advisor."""
    advisor_dir = Path(__file__).resolve().parents[2] / "MCP" / "sunzi-vibe-advisor" / "script"
    advisor_py = advisor_dir / "advisor.py"
    if not advisor_py.exists():
        return f"sunzi-vibe-advisor not found"

    try:
        result = subprocess.run(
            [sys.executable, str(advisor_py), "--action", "strategic", "--context", context, "--question", question],
            capture_output=True, text=True, timeout=60
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Advisor error: {str(e)}"

server.register_tool(
    name="advisor_musashi",
    description="Get coding advice from Miyamoto Musashi (五輪書)",
    input_schema={
        "properties": {
            "question": {"type": "string", "description": "Coding/strategy question"},
        },
        "required": ["question"]
    },
    handler=lambda question: _advisor_musashi(question)
)

def _advisor_musashi(question):
    """Get advice from Musashi via strategic-advisors."""
    advisor_dir = Path(__file__).resolve().parents[2] / "MCP" / "strategic-advisors" / "coding" / "script"
    advisor_py = advisor_dir / "advisor.py"
    if not advisor_py.exists():
        return f"strategic-advisors/coding not found"

    try:
        result = subprocess.run(
            [sys.executable, str(advisor_py), "--action", "strategic", "--question", question],
            capture_output=True, text=True, timeout=60
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Advisor error: {str(e)}"

server.register_tool(
    name="seven_sages_meeting",
    description="Full 7-advisor council deliberation (Sun Tzu, Zhuge Liang, Musashi, etc.)",
    input_schema={
        "properties": {
            "topic": {"type": "string", "description": "Topic for council deliberation"},
        },
        "required": ["topic"]
    },
    handler=lambda topic: _seven_sages(topic)
)

def _seven_sages(topic):
    """Run seven sages meeting."""
    skills_dir = Path.home() / ".qwen" / "skills"
    skill_md = skills_dir / "seven-sages-meeting" / "SKILL.md"
    if not skill_md.exists():
        return "Seven sages skill not found in ~/.qwen/skills"

    # Use yao natsume to simulate the meeting
    port = AGENTS["natsume"]["port"]
    if not _check_port(port):
        _yao_start("natsume")

    with open(skill_md, 'r', encoding='utf-8') as f:
        skill_content = f.read()[:5000]

    prompt = f"""
七賢会議を開催してください。議題: {topic}

スキル定義:
{skill_content[:2000]}

7人の軍師（孫子、諸葛亮、耶律楚材、宮本武蔵、チャナキヤ、マキャベリ、クラウゼヴィッツ）それぞれの視点から意見を出し、最終的な合意をまとめてください。
"""
    return _api_chat(port, [{"role": "user", "content": prompt}], temperature=0.8, max_tokens=4096)

# ========== Monju (Deliberation) ==========
server.register_tool(
    name="monju_deliberate",
    description="3-AI deliberation (GPT + Gemini + Claude consensus)",
    input_schema={
        "properties": {
            "question": {"type": "string", "description": "Question for deliberation"},
        },
        "required": ["question"]
    },
    handler=lambda question: _monju_deliberate(question)
)

def _monju_deliberate(question):
    """Run monju deliberation."""
    monju_dir = Path(__file__).resolve().parents[2] / "MCP" / "monju"
    monju_py = monju_dir / "monju.py"
    if not monju_py.exists():
        return f"monju not found at {monju_dir}"

    try:
        result = subprocess.run(
            [sys.executable, str(monju_py), "--question", question],
            capture_output=True, text=True, timeout=180
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Monju error: {str(e)}"

# ========== Unified Skill Tools ==========
server.register_tool(
    name="skill_writer",
    description="Creative writing skills (SF落語, dream writing, memo creative)",
    input_schema={
        "properties": {
            "prompt": {"type": "string", "description": "Writing prompt"},
            "style": {"type": "string", "default": "general"},
        },
        "required": ["prompt"]
    },
    handler=lambda prompt, style="general": _skill_writer(prompt, style)
)

def _skill_writer(prompt, style):
    """Creative writing via natsume."""
    port = AGENTS["natsume"]["port"]
    if not _check_port(port):
        _yao_start("natsume")

    sys_prompts = {
        "rakugo": "あなたはSF落語家。未来と伝統を融合させた落語を作成してください。",
        "dream": "あなたは夢見る作家。想像力豊かなストーリーテリングが得意です。",
        "general": "あなたは優秀な日本の作家です。",
    }
    return _api_chat(port, [
        {"role": "system", "content": sys_prompts.get(style, sys_prompts["general"])},
        {"role": "user", "content": prompt}
    ], temperature=0.8)

server.register_tool(
    name="skill_cleaner",
    description="File and text cleanup skills (remove noise, format, deduplicate)",
    input_schema={
        "properties": {
            "target": {"type": "string", "description": "File or directory to clean"},
            "mode": {"type": "string", "default": "general"},
        },
        "required": ["target"]
    },
    handler=lambda target, mode="general": f"Cleaning: {target} (mode: {mode})\n\nNote: Full implementation reads and cleans the target file."
)

server.register_tool(
    name="skill_ocr",
    description="OCR and image text extraction",
    input_schema={
        "properties": {
            "image_path": {"type": "string", "description": "Path to image file"},
            "compare": {"type": "boolean", "default": False},
        },
        "required": ["image_path"]
    },
    handler=lambda image_path, compare=False: _skill_ocr(image_path, compare)
)

def _skill_ocr(image_path, compare):
    """OCR via sharaku (vision model)."""
    port = AGENTS["sharaku"]["port"]
    if not _check_port(port):
        _yao_start("sharaku")

    return _api_chat(port, [
        {"role": "system", "content": "画像内のテキストを読み取って抽出してください。"},
        {"role": "user", "content": f"画像パス: {image_path}\nテキストを抽出してください。"}
    ], temperature=0.1)

server.register_tool(
    name="skill_code_review",
    description="Code review and analysis (PR review, debug, adev)",
    input_schema={
        "properties": {
            "code": {"type": "string", "description": "Code to review"},
            "mode": {"type": "string", "default": "review"},
        },
        "required": ["code"]
    },
    handler=lambda code, mode="review": _skill_code_review(code, mode)
)

def _skill_code_review(code, mode):
    """Code review via natsume (torahiko style)."""
    port = AGENTS["natsume"]["port"]
    if not _check_port(port):
        _yao_start("natsume")

    sys_prompt = "あなたは寺田寅彦。科学と文学の両面に精通し、エンジニアリングについてエッセイ風に語ってください。コードの品質、可読性、パフォーマンスを重視します。"
    return _api_chat(port, [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"以下のコードをレビューしてください:\n\n{code}"}
    ], temperature=0.3, max_tokens=4096)

server.register_tool(
    name="skill_task_mgmt",
    description="Task and decision management (task-manager, decision-maker, tochuude)",
    input_schema={
        "properties": {
            "action": {"type": "string", "enum": ["create_task", "make_decision", "track_progress"], "default": "create_task"},
            "description": {"type": "string", "description": "Task or decision description"},
        },
        "required": ["description"]
    },
    handler=lambda action, description: _skill_task(action, description)
)

def _skill_task(action, description):
    """Task management via natsume (takuboku style)."""
    port = AGENTS["natsume"]["port"]
    if not _check_port(port):
        _yao_start("natsume")

    sys_prompt = "あなたは啄木。タスク管理、意思決定の補佐が得意です。簡潔に、実用的に答えてください。"
    return _api_chat(port, [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"操作: {action}\n内容: {description}"}
    ], temperature=0.3)

server.register_tool(
    name="skill_journal",
    description="Journal and memory management (morning journal, memory eater)",
    input_schema={
        "properties": {
            "entry": {"type": "string", "description": "Journal entry"},
            "mode": {"type": "string", "default": "write"},
        },
        "required": ["entry"]
    },
    handler=lambda entry, mode="write": _skill_journal(entry, mode)
)

def _skill_journal(entry, mode):
    """Journal via natsume."""
    port = AGENTS["natsume"]["port"]
    if not _check_port(port):
        _yao_start("natsume")

    sys_prompt = "あなたは日記の補佐役。入力から要点を抽出し、整理して記録してください。"
    return _api_chat(port, [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": entry}
    ], temperature=0.5)

server.register_tool(
    name="skill_file_ops",
    description="File operations (search, download, read, location)",
    input_schema={
        "properties": {
            "action": {"type": "string", "enum": ["read", "search", "download"], "default": "read"},
            "path": {"type": "string", "description": "File path or search query"},
        },
        "required": ["action", "path"]
    },
    handler=lambda action, path: _skill_file_ops(action, path)
)

def _skill_file_ops(action, path):
    """File operations."""
    if action == "read":
        p = Path(path)
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")[:5000]
        return f"File not found: {path}"
    elif action == "search":
        import glob
        results = glob.glob(path, recursive=True)[:20]
        return "\n".join(results) if results else f"No matches for: {path}"
    return f"Unknown action: {action}"

# ========== Helpers ==========
def _check_port(port):
    """Check if a port is responding."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((HOST, port))
        s.close()
        return True
    except:
        return False

def _api_chat(port, messages, temperature=0.7, max_tokens=2048):
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
    except Exception as e:
        return f"API error: {str(e)}"

# ========== Main ==========
GREETING = """
╔══════════════════════════════════════════════╗
║  PyPer MCP Advisor Server v1.0.0            ║
║  On-demand | Yao + Law + Advisors + Skills  ║
╚══════════════════════════════════════════════╝
"""

def main():
    sys.stderr.write(GREETING + "\n")
    sys.stderr.flush()
    server.run()

if __name__ == "__main__":
    main()
