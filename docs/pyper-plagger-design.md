# PyPer as Plagger Wrapper - 設計思想

## 📜 概要

**PyPer** は既存の **Plagger** (Perl製RSSアグリゲータ) をラップし、
モダンなクラウド/LLM機能を統合するパイプライン実行エンジンである。

> **方針**: 「あるコードは使う」— 車輪の再発明を避け、
> 既存資産を活かしつつPythonエコシステムを融合する。

---

## 🎯 設計思想

### 1. 「Inを処理してOutするだけ」

Plaggerの本質は **pipeline** である:

```
Subscription → Filters → Publish
     ↓            ↓          ↓
  データ取得    加工/フィルタ  送信/公開
```

この単純なモデルが、**ほぼすべてのコードを取り込める理由**である:
- 入力: RSS, API, DB, Webスクレイピング
- 処理: LLM要約, 感情分析, ベクトル化, 翻訳
- 出力: Gmail, Slack, Twitter, BigQuery

### 2. 言語は問わない

PlaggerはPerlで書かれているが、PyPerはPythonでwrapする。
重要なのは **インターフェースの統一** であり、実装言語ではない。

```
┌──────────────────────────────────────────────┐
│                  plagger.yaml                 │
│                                               │
│  subscription:                                │
│    - module: subscription.rss.Plugin (Python) │
│  filters:                                     │
│    - module: filter.llm.Plugin     (Python)   │
│    - module: Filter::EntryFullText (Perl)     │ ← 既存資産
│  publish:                                     │
│    - module: publish.gmail.Plugin  (Python)   │
│    - module: Notify::Eject         (Perl)     │ ← 遊べる
└──────────────────────────────────────────────┘
```

### 3. Docker的思想

各pluginは **isolated** であるべき:
- 設定YAMLで有効/無効を切り替え
- 依存はplugin内部に閉じる
- エラー時もpipeline全体は停止しない（フォールトトレラント）

```yaml
filters:
  - module: filter.llm.Plugin
    config:
      enabled: false  # ← これだけで無効化
```

### 4. PyPerがwrapperになる理由

既存のPlagger ecosystemを捨てるのは無駄:
- **192+ plugins** (Subscription, Filter, Publish, Notify)
- **Hook system** (26箇所の拡張ポイント)
- **Rule engine** (AND/OR/NOT条件)
- **State管理** (dedup, cache)

PyPerはこれらを **subprocess or IPC** で呼び出しつつ、
クラウド/LLM機能はPythonネイティブで実装する。

---

## 🏗️ アーキテクチャ

### コアコンポーネント

```
PyPer/
├── pyper_plagger.py          # Pipeline executor
├── recipe/
│   └── plagger.yaml          # Pipeline definition
└── src/plugins/
    ├── base.py               # Entry, BasePlugin, etc.
    ├── subscription/         # Input
    │   ├── rss.py            # RSS/Atom feed
    │   ├── google_keep.py    # Google Keep
    │   └── prtimes.py        # PR Times
    ├── filter/               # Processing
    │   ├── llm_metadata_enricher.py  # Gemini LLM
    │   └── llm_vectorize.py          # Embedding
    └── publish/              # Output
        ├── nhk_gmail.py      # Gmail API (OAuth2)
        ├── twitter.py        # Twitter API
        ├── slack.py          # Slack Webhook
        └── line_notify.py    # LINE Notify
```

### データフロー

```
┌─────────────────────────────────────────────────────────────┐
│                    plagger.yaml                             │
│                                                             │
│  pipeline:                                                  │
│    name: "NHK News → Gmail"                                 │
│    subscription:                                            │
│      - module: subscription.rss.Plugin                      │
│        config: { urls: [...], limit: 5 }                    │
│    filters:                                                 │
│      - module: filter.llm_metadata_enricher.Plugin          │
│    publish:                                                 │
│      - module: publish.nhk_gmail.Plugin                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  pyper_plagger.py                           │
│                                                             │
│  1. load_config("recipe/plagger.yaml")                      │
│  2. resolve_env_vars()  # ${VAR} → 環境変数                  │
│  3. load_plugin()       # 動的import                         │
│  4. execute pipeline:                                       │
│     a. Subscription → List[Entry]                           │
│     b. Filter → List[Entry] (transform)                     │
│     c. Publish → send!                                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                     Entry (dataclass)                       │
│                                                             │
│  id: str              # SHA-256 hash                       │
│  source: str          # "Subscription::RSS::https://..."    │
│  content: str         # title + summary                     │
│  metadata: Dict       # {url, title, author, published, ...}│
│  vector: List[float]  # embedding (optional)                │
│  timestamp: int       # epoch time                          │
└─────────────────────────────────────────────────────────────┘
```

### Plugin interface

```python
# 全pluginはこのinterfaceに従う
class BasePlugin:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

class SubscriptionPlugin(BasePlugin):
    def execute(self) -> Iterator[Entry]: ...

class FilterPlugin(BasePlugin):
    def execute(self, entries: Iterator[Entry]) -> Iterator[Entry]: ...

class PublishPlugin(BasePlugin):
    def execute(self, entries: Iterator[Entry]): ...
```

---

## 📦 既存Plagger資産の統合

### 方式1: Python再実装（推奨）

既存のPlagger pluginをPythonで書き直す。
設定YAMLはそのまま流用可能。

```yaml
# Before (Plagger Perl)
- module: Subscription::Config
  config:
    feed:
      - https://news.web.nhk/...

# After (PyPer Python)
- module: subscription.rss.Plugin
  config:
    urls:
      - https://news.web.nhk/...
```

### 方式2: Subprocess呼び出し（互換モード）

Perl pluginをそのまま使う必要がある場合:

```yaml
plagger_compat:
  enabled: true
  plagger_path: "C:\\Users\\dance\\Documents\\MEGA\\plagger"
  plugins:
    - module: Filter::EntryFullText
      config:
        enabled: false
```

### 方式3: MCP連携

将来的にはMCP (Model Context Protocol) でpluginを外部サービス化:

```
PyPer → MCP Server → LLM Filter → Gmail
```

---

## 🔐 認証・セキュリティ

### OAuth2 トークン管理

```
~/.qwen/gmail_token.pickle  # Gmail API用OAuth2トークン
~/.qwen/credentials.json    # Google Cloud client_secrets
```

- トークンはpickle形式（Google auth library互換）
- 自動refresh対応（expired時に自動更新）
- 環境変数 `${GOOGLE_API_KEY}` でLLM用API key分離

### 機密情報の扱い

```yaml
publish:
  - module: publish.nhk_gmail.Plugin
    config:
      password: "${GMAIL_APP_PASSWORD}"  # 環境変数参照
      oauth_token_file: "~/.qwen/gmail_token.pickle"
```

---

## 🚀 運用

### 実行

```bash
# 手動実行
cd C:\Users\dance\Documents\MEGA\PyPer
python pyper_plagger.py recipe/plagger.yaml

# スケジュール実行（Windows Task Scheduler）
schtasks /create /tn "PyPer-NHK" /tr "python pyper_plagger.py recipe/plagger.yaml" /sc daily /st 07:00
```

### 監視

```yaml
monitoring:
  log_level: info
  metrics:
    enabled: true
    prometheus_port: 9090
  alerts:
    on_failure:
      - module: notify.line.Plugin
```

---

## 📈 拡張ロードマップ

### Phase 1: 基盤整備（完了 ✅）
- [x] Pipeline executor実装
- [x] RSS Subscription
- [x] Gmail Publish (OAuth2)
- [x] LLM Filter (Gemini)
- [x] 設定YAML設計

### Phase 2: プラグイン拡充
- [ ] Twitter/X publish
- [ ] Slack publish
- [ ] LINE notify
- [ ] ベクトルDB統合
- [ ] 画像生成 (Imagen)

### Phase 3: インテリジェンス
- [ ] LLM Filter改善（プロンプト最適化）
- [ ] 感情分析フィルタ
- [ ] 自動カテゴリ分類
- [ ] 類似記事検出

### Phase 4: 統合
- [ ] Plagger Perl互換レイヤー完成
- [ ] MCP server化
- [ ] Web UI
- [ ] スケジューラ

---

## 📚 参考文献

- [Plagger Official](http://plagger.org/) - Tatsuhiko Miyagawa
- [Plagger GitHub](https://github.com/miyagawa/Plagger) - 192+ plugins
- [PyPer README](../PyPer/README.md) - PR Times配信サービス
- [Google Gmail API](https://developers.google.com/gmail/api) - OAuth2

---

*Created: 2026-04-11*
*Author: Qwen Code + bonsai*
*Version: 0.1.0*
