# MCP Architecture Restructuring — Requirements Definition

**Date:** 2026-04-11
**Author:** 松岡 (MCP Expert)
**Status:** Draft — 七賢会議 review pending

---

## 1. 現状分析 (AS-IS)

### 1.1 5層の定義散在

| 層 | ファイル | 定義数 | 内容 | 問題 |
|----|---------|--------|------|------|
| ① yao.py | `SKILLS` dict | 10 | CLIスキル定義 + sysプロンプト | ハードコード |
| ② yao-mcp.py | `SKILLS` + `AGENT_TOOLS` + `handle_tool_call` | 13+17+8=38 | MCPツール定義 + sysプロンプト | ①と重複 + elif分岐地獄 |
| ③ skills/ | 37 SKILL.md + scripts | 37 | 作業バンドル | Qwen Code固有 |
| ④ settings.json | `mcpServers` | 10 | サーバー登録 | 3つ未登録(torahiko/kiyoshi/hoshi) |
| ⑤ modes/ | registry.md | 8 | コマンド層 | 文字化け、保守放棄 |

### 1.2 重複カウント

| 項目 | yao.py | yao-mcp.py | 重複 |
|------|--------|------------|------|
| AGENTS dict | 3 | 3 | ✅ 同一 |
| SKILLS dict | 10 | 13 | 10個が同一 |
| sysプロンプト | 10 | 30 | 10個が同一 |
| 起動関数 | 一式 | 一式 | ✅ 同一 |
| GREETINGS | なし | 8 | 新規 |

**合計40個のハードコードsysプロンプト。**

---

## 2. 要求定義 (Requirements)

### 2.1 ユーザー要求

| # | 要求 | 優先度 | 検証方法 |
|---|------|--------|---------|
| R1 | ハードコード(yao.py/yao-mcp.py)→MCP外部化 | P0 | Python MCPサーバーに集約 |
| R2 | エージェント定義→MD抽象化 | P0 | MDファイルでpersona管理 |
| R3 | Skillは「作業のまとまり」として維持 | P1 | 繰り返しパターンはskills/に残す |
| R4 | 速いこと | P0 | 起動3秒以内 |
| R5 | バックアップ→再現 | P0 | 1コマンドでリストア |
| R6 | 使用メトリクス取得 | P1 | どのエージェント/スキルが使われているか計測 |

### 2.2 非機能要求

| # | 要求 | 指標 |
|---|------|------|
| NF1 | 単一真理場所 | 各定義は1箇所にのみ存在 |
| NF2 | 関心の分離 | Agent定義 ≠ ツール定義 ≠ サーバー設定 |
| NF3 | 前方互換 | 既存skills/の自然言語トリガーを維持 |
| NF4 | PC移行 | `git clone` + 1コマンドで再現 |

---

## 3. 目標アーキテクチャ (TO-BE)

```
┌──────────────────────────────────────────────────────────┐
│                    Qwen Code (本体)                       │
│                                                          │
│  ┌─────────────┐    ┌──────────────────────────────────┐ │
│  │  Agents (MD) │    │        Skills (MD + scripts)     │ │
│  │  .qwen/      │    │        .qwen/skills/             │ │
│  │  agents/     │    │        37 → 15 (統合後)          │ │
│  │  persona.md  │    │        作業バンドル維持          │ │
│  │  抽象定義     │    │                                  │ │
│  └──────┬──────┘    └──────────┬───────────────────────┘ │
│         │                      │                          │
│         ▼                      ▼                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              MCP Server (Python外部化)               │ │
│  │         PyPer Yao MCP Server (統合)                  │ │
│  │                                                      │ │
│  │  - エージェントMDを読み込んで動的ツール登録          │ │
│  │  - SKILLS.jsonでパラメータ(temp, max)管理            │ │
│  │  - handle_toolcallのelif分岐→JSON駆動                │ │
│  │  - ツール数: 38 → 動的生成                           │ │
│  └─────────────────────────────────────────────────────┘ │
│         │                      │                          │
│         ▼                      ▼                          │
│  ┌─────────────┐    ┌──────────────────────────────────┐ │
│  │  settings.json│   │     Metrics (usage-log.jsonl)    │ │
│  │  MCP登録      │   │     .qwen/metrics/               │ │
│  │  10 → 最適化  │   │     ツール実行/スキル起動を記録   │ │
│  └─────────────┘    └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 3.1 責務分解

| 責務 | 現在 | 目標 | ファイル |
|------|------|------|---------|
| **Persona定義** | yao.py SKILLS, yao-mcp.py handle_toolcall | MD抽象化 | `.qwen/agents/{name}.md` |
| **ツール定義** | yao-mcp.py AGENT_TOOLS | JSON駆動 | `PyPer/src/yao-mcp-tools.json` |
| **LLMパラメータ** | yao.py/yao-mcp.py SKILLS | JSON駆動 | `PyPer/src/yao-skills-config.json` |
| **サーバー起動** | yao.py start_process() | 共通モジュール | `PyPer/src/yao-agent-runner.py` |
| **MCPプロトコル** | yao-mcp.py mcp_loop() | 共通モジュール | `PyPer/src/plugins/mcp_base.py` |
| **サーバー登録** | settings.json | 変更なし | `.qwen/settings.json` |
| **作業バンドル** | skills/ SKILL.md + scripts | 維持・統合 | `.qwen/skills/` |
| **メトリクス** | なし | 新規 | `.qwen/metrics/usage-log.jsonl` |

---

## 4. ファイル構成案

```
C:\Users\dance\.qwen\
├── agents\                          ← 新設: エージェントMD抽象化
│   ├── natsume.md                   ← Persona: 夏目漱石
│   ├── takuboku.md                  ← Persona: 石川啄木
│   ├── torahiko.md                  ← Persona: 寺田寅彦
│   ├── kiyoshi.md                   ← Persona: 岡潔
│   ├── hoshi.md                     ← Persona: 星新一
│   ├── sharaku.md                   ← Persona: 写楽
│   ├── hokusai.md                   ← Persona: 北斎
│   ├── matsuoka.md                  ← Persona: 松岡
│   └── _schema.md                   ← MDフォーマット定義
│
├── metrics\                         ← 新設: 使用状況メトリクス
│   ├── usage-log.jsonl              ← 実行ログ (append-only)
│   ├── dashboard.json               ← 集計結果
│   └── README.md                    ← メトリクス仕様
│
├── skills\                          ← 既存: 作業バンドル (維持)
│   ├── skills-profile.json          ← 既存 (見直し)
│   └── ... (37 skills)
│
└── settings.json                    ← 既存: MCP登録

C:\Users\dance\Documents\MEGA\PyPer\src\
├── yao-mcp-unified.py               ← 新設: 統合MCPサーバー
├── yao-agent-runner.py              ← 新設: エージェント起動ランナー
├── yao-mcp-tools.json               ← 新設: ツール定義JSON
├── yao-skills-config.json           ← 新設: スキルパラメータJSON
├── yao-metrics.py                   ← 新設: メトリクス収集
├── plugins\mcp_base.py              ← 既存: 変更なし
├── pyper-mcp-config.py              ← 既存: v2.0.0 (変更なし)
└── pyper-mcp-core.py                ← 既存: 変更なし
```

---

## 5. 実装フェーズ

### Phase 1: 基盤整備 (Week 1)
| # | タスク | 成果物 |
|---|--------|--------|
| 1.1 | agents/ ディレクトリ作成 + MDスキーマ定義 | `_schema.md` + 8 agent MD |
| 1.2 | yao-skills-config.json 作成 | 30 sysプロンプト + temp/max JSON化 |
| 1.3 | yao-mcp-tools.json 作成 | 38 ツール定義 JSON化 |
| 1.4 | metrics/ ディレクトリ作成 + 収集スクリプト | `usage-log.jsonl` + `yao-metrics.py` |

### Phase 2: 統合MCPサーバー (Week 2)
| # | タスク | 成果物 |
|---|--------|--------|
| 2.1 | yao-mcp-unified.py 作成 | MD+JSON駆動の統合MCPサーバー |
| 2.2 | yao-agent-runner.py 作成 | 起動・停止・状態管理の共通モジュール |
| 2.3 | settings.json 更新 | 10→6 (統合後) |
| 2.4 | バックアップ・リストア確認 | `mcp_backup` / `mcp_restore` |

### Phase 3: 統合検証 (Week 3)
| # | タスク | 成果物 |
|---|--------|--------|
| 3.1 | 既存yao.py/yao-mcp.py の動作テスト | 回帰テスト |
| 3.2 | skills/ との連携確認 | 既存トリガー維持 |
| 3.3 | メトリクスダッシュボード確認 | `yao-metrics.py report` |
| 3.4 | PC移行スクリプト作成 | `setup-new-pc.ps1` |

### Phase 4: 削除・クリーンアップ (Week 4)
| # | タスク | 成果物 |
|---|--------|--------|
| 4.1 | 旧yao.py/yao-mcp.py バックアップ | `yao.py.bak`, `yao-mcp.py.bak` |
| 4.2 | skills/ 統合 (37→15) | 重複削除 |
| 4.3 | modes/ registry.md 修正 | 文字化け解消 |
| 4.4 | 旧ファイル削除 | 整理完了 |

---

## 6. メトリクス仕様

### 6.1 収集項目

| 項目 | 形式 | 収集タイミング |
|------|------|---------------|
| ツール実行 | `{ts, server, tool, agent, duration_ms, success}` | tools/call 毎 |
| スキル起動 | `{ts, skill, trigger_type, duration_ms}` | skill実行毎 |
| エージェント状態 | `{ts, agent, status, port, memory_mb}` | 1分毎 |
| MCP接続 | `{ts, server, event, latency_ms}` | connect/disconnect 毎 |

### 6.2 ダッシュボード出力

```json
{
  "period": "2026-04-01 to 2026-04-11",
  "tools": {
    "mcp_diagnose": 15,
    "code": 42,
    "read_file": 8
  },
  "skills": {
    "memo-creative": 23,
    "pr-review": 5
  },
  "agents": {
    "natsume": 89,
    "takuboku": 12
  },
  "unused": ["pyper-media", "pyper-advisor", "kiyoshi", "hoshi"],
  "top_3": ["code", "memo-creative", "mcp_diagnose"]
}
```

---

## 7. リスク

| リスク | 影響 | 対策 |
|--------|------|------|
| MD駆動のオーバーヘッド | 起動遅延 | JSONキャッシュで回避 |
| メトリクス収集の性能影響 | 1ms/tool call | append-only JSONLで最小化 |
| 後方互換性破壊 | 既存skills動作停止 | テストスイート作成 |
| SUNABA締切 (2026-07-06) | 作業時間不足 | Phase 1のみ実施、他は凍結も可 |

---

## 8. 判断待ち事項

| # | 事項 | 選択肢 | 推奨 |
|---|------|--------|------|
| D1 | 実装スコープ | A: Phase1-4完遂 / B: Phase1のみ / C: 設計のみ | **B: Phase1のみ** (締切考慮) |
| D2 | skills/ 統合時期 | A: 今 / B: SUNABA後 | **B: SUNABA後** |
| D3 | metrics収集開始 | A: 今すぐ / B: 統合後 | **A: 今すぐ** (現状把握に有用) |
