# yao — 八百万の神々

Unified Offline LLM CLI. 八百万のエージェントを統べる司令塔。

## Agents (神々)

| 神 | モデル | Port | 役割 |
|----|--------|------|------|
| 夏目 | Qwen3 8B | 8081 | 文学論・小説・俳句 |
| 啄木 | Qwen3 8B | 8081 | 雑用・ファイル整理 |
| 寅彦 | Qwen3 8B | 8081 | コーディング・理系 |
| 星 | Qwen3 8B | 8081 | ショートショート |
| 岡潔 | Qwen3 8B | 8081 | 数学の美 |
| 写楽 | Qwen2.5-VL 3B | 8082 | 画像認識 |
| 北斎 | SD1.5 | 8083 | 画像生成 |

## Commands

```bash
yao                 # Start all agents
yao status          # Show status
yao chat            # Chat with 夏目
yao baku            # 夢喰: メモから新アイデアを生む
yao setup-mcp       # Configure Qwen Code MCP
```

## Architecture

```
yao/                 # 司令塔 (MCP + CLI)
├── yao.py           # CLI本体
├── yao-mcp.py       # MCP stdioサーバー
├── yao.ps1          # Windows entry
├── offline.py       # オフラインゲートウェイ
└── README.md

baku/                # 夢喰 (独立OSS)
├── baku.py          # WSL engine
├── baku.bat         # Windows entry
├── pyproject.toml
└── README.md
```

Both sides: Python-only. No .sh, no .bat debates.
