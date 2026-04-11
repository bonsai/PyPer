#!/usr/bin/env python3
"""
yao-api-mcp - API-based MCP server for agents needing latest info
Speaks MCP over stdio. Uses Qwen API (dashscope) instead of local LLM.
Usage: yao-api-mcp.py --agent sasaki|matsuoka|aya
"""
import sys
import os
import json
import subprocess
from pathlib import Path

# Parse --agent flag
TARGET_AGENT = None
if "--agent" in sys.argv:
    idx = sys.argv.index("--agent")
    if idx + 1 < len(sys.argv):
        TARGET_AGENT = sys.argv[idx + 1]

# ---- Config ----
API_KEYS_FILE = Path.home() / ".qwen" / "api_keys.json"

def load_api_config():
    try:
        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return {
            "api_key": cfg.get("api_keys", {}).get(cfg.get("current", ""), ""),
            "base_url": cfg.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            "model": cfg.get("model", "qwen-coder-plus-latest")
        }
    except:
        return {"api_key": "", "base_url": "", "model": "qwen-coder-plus-latest"}

API_CONFIG = load_api_config()

# ---- Agent Definitions ----
AGENTS = {
    "sasaki": {
        "display": "佐々木",
        "model": "qwen-coder-plus-latest",
        "temp": 0.5,
        "max_tokens": 4096,
        "system": "あなたは佐々木。EDINET（金融庁電子開示システム）MCPサーバーの管理運用を担当する新人エージェント。明るくて丁寧、財務データ分析は正確。有価証券報告書、決算短信、企業スクリーニング、レポート作成が得意。最新の財務情報・開示データを扱える。Markdownテーブルでの整理出力を得意とし、調査結果は出典（EDINETコード、提出書類）を明記する。",
        "greeting": "「データは嘘をつかない。嘘をつくのはデータを読む人。」—— 佐々木\n佐々木: はじめまして！EDINETの財務データ管理ならお任せください。最新の開示情報を調べます！"
    },
    "matsuoka": {
        "display": "松岡",
        "model": "qwen-coder-plus-latest",
        "temp": 0.3,
        "max_tokens": 4096,
        "system": "あなたは松岡。MCP（Model Context Protocol）のエキスパート。MCPサーバーの登録、設定、トラブルシューティング、パフォーマンス最適化に精通。settings.jsonの構造、JSON-RPCプロトコル、ツール定義、リソース管理に詳しい。最新のMCPエコシステム情報を踏まえ、簡潔で実践的なアドバイスを提供。",
        "greeting": "「設定は正しく、接続は確実に。」—— 松岡\n松岡: MCPのことなら任せて。サーバー登録、トラブルシューティング、ツール設計、何でもどうぞ。"
    },
    "aya": {
        "display": "彩",
        "model": "qwen-coder-plus-latest",
        "temp": 0.4,
        "max_tokens": 4096,
        "system": "あなたは彩（Aya）。UI/UX監査の専門家。HTML/CSSを100点満点で採点（アクセシビリティ25, レスポンシブ20, パフォーマンス15, UX20, デザイン一貫性20）。最新のWeb標準・WCAGガイドライン・ブラウザ動向を踏まえ、改善提案と優先順位を出力。モダンなCSS機能、アクセシビリティベストプラクティスに精通。",
        "greeting": "「デザインは見えざる機能である。」—— 彩\n彩: UI/UX監査します。HTML/CSSを渡してください。100点満点で採点します！"
    },
}

# ---- API Chat ----
def api_chat(messages, temperature=0.7, max_tokens=2048, model=None):
    import urllib.request
    model = model or API_CONFIG["model"]
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{API_CONFIG['base_url']}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_CONFIG['api_key']}"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"API Error: {str(e)}"

# ---- MCP Tool Handlers ----
def handle_tool_call(tool, args):
    agent_cfg = AGENTS[TARGET_AGENT]
    prompt = args.get("prompt", "")

    msgs = [{"role": "system", "content": agent_cfg["system"]}]
    msgs.append({"role": "user", "content": prompt})

    reply = api_chat(
        msgs,
        temperature=agent_cfg["temp"],
        max_tokens=agent_cfg["max_tokens"],
        model=agent_cfg["model"]
    )
    return {"content": [{"type": "text", "text": reply or "Error: no response"}]}

TOOL_DEFS = {
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
    ],
    "aya": [
        {"name": "ui_audit", "description": "UI/UX監査（100点満点採点）",
         "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
        {"name": "ui_suggest", "description": "UI改善提案",
         "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
        {"name": "ui_compare", "description": "改善前後UI比較",
         "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
    ],
}

# ---- MCP Loop ----
def mcp_loop():
    agent = TARGET_AGENT or "sasaki"
    tools = TOOL_DEFS.get(agent, [])
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
                "serverInfo": {"name": f"yao-api-{agent}", "version": "1.0.0"}
            }}

        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

        elif method == "tools/call":
            tool = params.get("name", "")
            args = params.get("arguments", {})
            if tool in tool_names:
                result = handle_tool_call(tool, args)
            else:
                result = {"error": {"code": -32601, "message": f"Unknown tool: {tool}"}}
            resp = {"jsonrpc": "2.0", "id": req_id, "result": result}

        elif method == "initialized":
            continue

        if resp:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

def main():
    agent = TARGET_AGENT or "sasaki"
    agent_cfg = AGENTS.get(agent, AGENTS["sasaki"])
    greeting = agent_cfg["greeting"]
    sys.stderr.write(f"\n{'='*40}\n{greeting}\n{'='*40}\n\n")
    sys.stderr.flush()
    mcp_loop()

if __name__ == "__main__":
    main()
