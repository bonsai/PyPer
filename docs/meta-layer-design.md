# PyPer メタ層設計 - レシピ管理 & 認証管理

## 📜 設計思想

PyPerの**メタ層**は、pipeline実行とは独立した**運用インフラ**である。

> **方針**: 「設定はコードから分離し、バージョン管理可能に」
> - レシピ = **何を**実行するか（宣言的）
> - 認証 = **誰が**実行するか（機密）
> - メタ = **いつ・どこで**実行するか（運用）

---

## 🗂️ 1. レシピ管理

### 1.1 レシピの階層構造

```
recipe/
├── meta.yaml              # レシピカタログ（メタ情報）
├── plagger.yaml           # NHK News → Gmail
├── prt.yaml               # PR Times → Gmail
└── rag.yaml               # RAG pipeline
```

### 1.2 メタカタログ（meta.yaml）

全レシピのインデックスと依存関係を定義:

```yaml
# recipe/meta.yaml
version: "1.0"
recipes:
  nhk-gmail:
    file: plagger.yaml
    description: "NHKニュース5件をGmail送信"
    tags: [news, gmail, daily]
    schedule: "0 7,12,18 * * *"
    depends:
      - credential: gmail-oauth2
      - credential: nhk-rss-feed
    
  prtimes-gmail:
    file: prt.yaml
    description: "PR Times最新プレスリリース配信"
    tags: [pr, gmail, business]
    schedule: "0 9 * * 1-5"
    depends:
      - credential: gmail-oauth2
      - credential: prtimes-search

  llm-summarize:
    file: rag.yaml
    description: "LLM要約 + ベクトルDB保存"
    tags: [llm, rag, embedding]
    schedule: manual
    depends:
      - credential: google-api-key
      - credential: pinecone-api
```

### 1.3 レシピテンプレート

雛形から新規レシピ生成:

```yaml
# recipe/templates/base.yaml
pipeline:
  name: "{{ name }}"
  description: "{{ description }}"
  
  subscription:
    - module: subscription.{{ sub_type }}.Plugin
      config: {{ sub_config | to_json }}
  
  filters:
    {% for filter in filters %}
    - module: filter.{{ filter.type }}.Plugin
      config: {{ filter.config | to_json }}
    {% endfor %}
  
  publish:
    - module: publish.{{ pub_type }}.Plugin
      config: {{ pub_config | to_json }}
  
  schedule:
    cron: "{{ cron }}"
    timezone: Asia/Tokyo
  
  monitoring:
    log_level: {{ log_level | default("info") }}
    alerts:
      on_failure:
        - module: notify.line.Plugin
```

### 1.4 レシピCLI

```bash
# レシピ一覧表示
pyper recipe list

# レシピ詳細表示
pyper recipe show nhk-gmail

# 新規レシピ作成（テンプレートから）
pyper recipe create my-pipeline --template base

# レシピ実行
pyper recipe run nhk-gmail

# レシピ検証（構文チェック）
pyper recipe validate plagger.yaml
```

---

## 🔐 2. 認証管理

### 2.1 認証の階層構造

```
config/
├── credentials/
│   ├── meta.yaml              # 認証カタログ
│   ├── google/
│   │   ├── client_secret.json
│   │   ├── gmail_token.pickle
│   │   └── service_account.json
│   ├── openai/
│   │   └── api_key.txt
│   ├── twitter/
│   │   ├── api_key.txt
│   │   └── access_token.json
│   └── slack/
│       └── webhook_url.txt
└── vault.yaml                # 暗号化vault（オプション）
```

### 2.2 認証メタカタログ

```yaml
# config/credentials/meta.yaml
version: "1.0"
credentials:
  gmail-oauth2:
    type: oauth2
    provider: google
    scopes:
      - https://www.googleapis.com/auth/gmail.send
      - https://www.googleapis.com/auth/gmail.modify
    files:
      client_secret: google/client_secret.json
      token: google/gmail_token.pickle
    status: active
    expires: 2026-05-11  # 自動更新可能ならnull
    recipes:
      - nhk-gmail
      - prtimes-gmail
  
  google-api-key:
    type: api_key
    provider: google
    env_var: GOOGLE_API_KEY
    file: google/api_key.txt
    status: active
    recipes:
      - llm-summarize
  
  twitter-api:
    type: oauth1
    provider: twitter
    files:
      api_key: twitter/api_key.txt
      api_secret: twitter/api_secret.txt
      access_token: twitter/access_token.json
    status: inactive  # 未設定
    recipes:
      - twitter-publish
```

### 2.3 認証解決ロジック

レシピ実行時に自動解決:

```python
# 擬似コード
def resolve_credentials(recipe_name: str) -> Dict[str, Any]:
    """
    レシピが必要とする認証を自動解決
    
    優先順位:
    1. 環境変数 (${VAR})
    2. credentials/meta.yaml 定義
    3. vault.yaml（暗号化）
    4. デフォルト値
    """
    meta = load_credential_meta()
    recipe = load_recipe(recipe_name)
    
    resolved = {}
    for cred_ref in recipe.depends:
        cred_name = cred_ref['credential']
        cred_info = meta['credentials'][cred_name]
        
        if cred_info['type'] == 'oauth2':
            resolved[cred_name] = load_oauth2_token(cred_info)
        elif cred_info['type'] == 'api_key':
            resolved[cred_name] = load_api_key(cred_info)
    
    return resolved
```

### 2.4 CLI

```bash
# 認証状態一覧
pyper auth status

# OAuth2認証セットアップ
pyper auth setup gmail-oauth2
  → ブラウザ起動 → OAuth flow → token保存

# API key登録
pyper auth set google-api-key
  → 対話的に入力 → 暗号化保存

# トークン更新
pyper auth refresh gmail-oauth2

# 認証テスト
pyper auth test gmail-oauth2
```

---

## 🏗️ 3. メタ層アーキテクチャ

### 3.1 コアコンポーネント

```
PyPer/
├── pyper.py                    # メタ層CLI
├── pyper_plagger.py            # Pipeline executor
├── src/
│   ├── meta/
│   │   ├── recipe_manager.py   # レシピ管理
│   │   ├── credential_manager.py # 認証管理
│   │   └── scheduler.py        # スケジュール管理
│   └── plugins/
│       └── ...
├── recipe/
│   ├── meta.yaml
│   └── ...
└── config/
    └── credentials/
        ├── meta.yaml
        └── ...
```

### 3.2 RecipeManager

```python
class RecipeManager:
    def __init__(self, recipe_dir: str):
        self.recipe_dir = recipe_dir
        self.meta = self._load_meta()
    
    def list_recipes(self, tag: str = None) -> List[Dict]:
        """レシピ一覧取得"""
        recipes = self.meta['recipes']
        if tag:
            recipes = [r for r in recipes if tag in r.get('tags', [])]
        return recipes
    
    def get_recipe(self, name: str) -> Dict:
        """レシピ詳細取得"""
        recipe_info = self.meta['recipes'][name]
        return self._load_yaml(recipe_info['file'])
    
    def validate_recipe(self, name: str) -> List[str]:
        """レシピ検証（構文・依存チェック）"""
        errors = []
        recipe = self.get_recipe(name)
        
        # プラグイン存在チェック
        for plugin in recipe['pipeline'].get('plugins', []):
            if not self._plugin_exists(plugin['module']):
                errors.append(f"Plugin not found: {plugin['module']}")
        
        # 依存認証チェック
        for dep in recipe.get('depends', []):
            if not self._credential_exists(dep['credential']):
                errors.append(f"Credential not found: {dep['credential']}")
        
        return errors
    
    def create_recipe(self, name: str, template: str, config: Dict):
        """テンプレートからレシピ生成"""
        template = self._load_template(template)
        rendered = self._render_template(template, config)
        self._save_yaml(f"recipe/{name}.yaml", rendered)
        self._update_meta(name, config)
```

### 3.3 CredentialManager

```python
class CredentialManager:
    def __init__(self, cred_dir: str):
        self.cred_dir = cred_dir
        self.meta = self._load_meta()
    
    def status(self) -> List[Dict]:
        """認証状態一覧"""
        results = []
        for name, info in self.meta['credentials'].items():
            status = self._check_credential(name, info)
            results.append({
                'name': name,
                'type': info['type'],
                'status': status,
                'recipes': info.get('recipes', [])
            })
        return results
    
    def setup_oauth2(self, cred_name: str):
        """OAuth2セットアップ"""
        cred_info = self.meta['credentials'][cred_name]
        client_secret = self._load_json(cred_info['files']['client_secret'])
        
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret,
            scopes=cred_info['scopes']
        )
        creds = flow.run_local_server(port=0)
        
        # トークン保存
        token_path = os.path.join(self.cred_dir, cred_info['files']['token'])
        with open(token_path, 'wb') as f:
            pickle.dump(creds, f)
        
        # メタ更新
        cred_info['status'] = 'active'
        self._save_meta()
    
    def resolve(self, recipe_name: str) -> Dict[str, Any]:
        """レシピが必要とする認証を解決"""
        recipe_meta = self._get_recipe_deps(recipe_name)
        resolved = {}
        
        for cred_ref in recipe_meta.get('depends', []):
            cred_name = cred_ref['credential']
            cred_info = self.meta['credentials'][cred_name]
            
            if cred_info['type'] == 'oauth2':
                resolved[cred_name] = self._load_oauth2_token(cred_info)
            elif cred_info['type'] == 'api_key':
                # 環境変数優先
                if cred_info.get('env_var'):
                    resolved[cred_name] = os.environ.get(cred_info['env_var'])
                elif cred_info.get('file'):
                    with open(os.path.join(self.cred_dir, cred_info['file'])) as f:
                        resolved[cred_name] = f.read().strip()
        
        return resolved
    
    def refresh(self, cred_name: str):
        """トークン自動更新"""
        cred_info = self.meta['credentials'][cred_name]
        if cred_info['type'] != 'oauth2':
            return
        
        token_path = os.path.join(self.cred_dir, cred_info['files']['token'])
        if not os.path.exists(token_path):
            return
        
        with open(token_path, 'rb') as f:
            creds = pickle.load(f)
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'wb') as f:
                pickle.dump(creds, f)
```

---

## 🔄 4. 実行フロー

### 4.1 全体像

```
pyper recipe run nhk-gmail
         ↓
┌─────────────────────────────────────┐
│ 1. RecipeManager.load("nhk-gmail")  │
│    - recipe/plagger.yaml 読み込み    │
│    - 構文検証                        │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ 2. CredentialManager.resolve()      │
│    - gmail-oauth2 トークン取得       │
│    - 環境変数展開 ${VAR} → value     │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ 3. PipelineExecutor.run(recipe)     │
│    - Subscription → Filter → Publish│
│    - OAuth token 注入                │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ 4. Monitoring                       │
│    - 成功/失敗記録                   │
│    - アラート通知（LINE/Slack）       │
└─────────────────────────────────────┘
```

### 4.2 設定展開例

```yaml
# Before: recipe/plagger.yaml
publish:
  - module: publish.nhk_gmail.Plugin
    config:
      oauth_token_file: "C:\\Users\\dance\\.qwen\\gmail_token.pickle"

# After: 実行時に自動展開
publish:
  - module: publish.nhk_gmail.Plugin
    config:
      use_oauth: true
      oauth_token: <GoogleCredentials object>  # メモリ上のみ
      access_token: "ya29.a0Aa7MYiq..."       # 自動解決
```

---

## 📊 5. 状態管理

### 5.1 実行履歴

```yaml
# data/execution_history.yaml
executions:
  - recipe: nhk-gmail
    started_at: 2026-04-11T12:27:58+09:00
    finished_at: 2026-04-11T12:28:00+09:00
    status: success
    entries_processed: 5
    message_id: "19d7a951d49dc571"
  
  - recipe: prtimes-gmail
    started_at: 2026-04-11T09:00:00+09:00
    finished_at: 2026-04-11T09:00:15+09:00
    status: failed
    error: "Credential expired: gmail-oauth2"
```

### 5.2 メトリクス

```yaml
# data/metrics.yaml
recipes:
  nhk-gmail:
    total_runs: 45
    success_rate: 0.98
    avg_duration_sec: 2.3
    last_success: 2026-04-11T12:28:00+09:00
    last_failure: 2026-04-10T07:00:00+09:00
```

---

## 🚀 6. CLI実装イメージ

```python
#!/usr/bin/env python3
"""pyper.py - PyPer メタ層CLI"""

import click
from src.meta import RecipeManager, CredentialManager

recipe_mgr = RecipeManager("recipe")
cred_mgr = CredentialManager("config/credentials")

@click.group()
def cli():
    """PyPer - Pluggable Pipeline Runner"""
    pass

@cli.group()
def recipe():
    """レシピ管理"""
    pass

@recipe.command()
def list():
    """レシピ一覧表示"""
    recipes = recipe_mgr.list_recipes()
    for r in recipes:
        click.echo(f"  {r['name']}: {r['description']}")

@recipe.command()
@click.argument('name')
def run(name):
    """レシピ実行"""
    creds = cred_mgr.resolve(name)
    recipe = recipe_mgr.get_recipe(name)
    executor = PipelineExecutor(recipe, creds)
    executor.run()

@cli.group()
def auth():
    """認証管理"""
    pass

@auth.command()
def status():
    """認証状態一覧"""
    statuses = cred_mgr.status()
    for s in statuses:
        status_icon = "✅" if s['status'] == 'active' else "❌"
        click.echo(f"  {status_icon} {s['name']}: {s['status']}")

@auth.command()
@click.argument('cred_name')
def setup(cred_name):
    """OAuth2セットアップ"""
    cred_mgr.setup_oauth2(cred_name)
    click.echo(f"✅ {cred_name} configured")

if __name__ == '__main__':
    cli()
```

---

## 📐 7. ディレクトリ構造（完成形）

```
PyPer/
├── pyper.py                    # メタ層CLI
├── pyper_plagger.py            # Pipeline executor
├── src/
│   ├── meta/
│   │   ├── __init__.py
│   │   ├── recipe_manager.py
│   │   ├── credential_manager.py
│   │   └── scheduler.py
│   └── plugins/
│       ├── base.py
│       ├── subscription/
│       ├── filter/
│       └── publish/
├── recipe/
│   ├── meta.yaml               # レシピカタログ
│   ├── templates/
│   │   └── base.yaml
│   ├── plagger.yaml
│   └── prt.yaml
├── config/
│   └── credentials/
│       ├── meta.yaml           # 認証カタログ
│       ├── google/
│       ├── openai/
│       └── twitter/
├── data/
│   ├── execution_history.yaml
│   ├── metrics.yaml
│   └── states/                 # subscription state
└── docs/
    └── pyper-plagger-design.md
```

---

## 🔮 8. 将来拡張

### 8.1 Web UI

```
/pyper/dashboard
  ├── レシピ一覧
  ├── 実行履歴
  ├── 認証状態
  └── メトリクスグラフ
```

### 8.2 Git連携

```bash
# レシピをGit管理
pyper recipe commit -m "Add NHK news pipeline"
pyper recipe diff nhk-gmail
pyper recipe rollback nhk-gmail --to v1.2
```

### 8.3 共有レジストリ

```bash
# コミュニティレシピ
pyper registry search news
pyper registry install community/nhk-digest

# 公開
pyper registry publish my-recipe
```

---

*Created: 2026-04-11*
*Version: 0.1.0*
