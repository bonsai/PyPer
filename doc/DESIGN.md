# 設計ドキュメント

## 1. 概要

本プロジェクトは、`rag.yaml`ファイルに基づいて動作する、Plaggerにインスパイアされたデータ移行サービスです。
様々なデータソースから情報を収集（Subscription）、LLMなどを用いて加工し（Filter）、BigQueryなどのデータウェアハウスに格納（Publish）することを目的とします。
将来的には、蓄積したデータを活用したアイデア創発RAG（Retrieval-Augmented Generation）システムの基盤となることを目指します。

## 2. アーキテクチャ

システムは、コアエンジンとプラグインから構成されます。

### コアエンジン (`main.py`)

- `rag.yaml`を読み込み、設定に基づいてパイプラインを構築します。
- 各プラグインを順番に呼び出し、処理を実行します。
- プラグイン間で受け渡されるデータオブジェクト（`Entry`）を管理します。

### プラグイン (`src/plugins/`)

共通のインターフェースを実装した独立したPythonモジュール群です。以下の3種類に大別されます。

- **Subscription:** 外部からデータを取得し、`Entry`オブジェクトを生成します。
  - 例: `GoogleKeep`, `Gmail`, `GoogleDrive`
- **Filter:** `Entry`オブジェクトを受け取り、内容を加工・変換・追加します。
  - 例: `Vectorize`（コンテンツのベクトル化）、`MetadataEnricher`（メタデータの付与）
- **Publish:** 加工された`Entry`オブジェクトを受け取り、外部サービスに出力・保存します。
  - 例: `BigQuery`, `Gmail`（通知用）

## 3. データフロー

処理は以下の流れで実行されます。

```
+--------------------------+      +----------------------+      +-----------------------+
|  Subscription Plugins    |      |   Filter Plugins     |      |   Publish Plugins     |
| (e.g., GoogleKeep)       |----->| (e.g., Vectorize)    |----->| (e.g., BigQuery)      |
+--------------------------+      +----------------------+      +-----------------------+
           |                             |                             |
      [Entry Object]                [Entry Object]                [Result]
       - id                          - id                          - Status
       - source                      - source                      - Message
       - content                     - content
                                     - vector (added)
                                     - metadata (added)
```

1. **Subscription**プラグインがデータソース（例: Google KeepのTakeoutファイル）からデータを読み込み、`Entry`オブジェクトのリストを生成します。
2. **Filter**プラグインが`Entry`オブジェクトを一つずつ受け取り、ベクトル化やメタデータ付与などの処理を加えます。
3. **Publish**プラグインが最終的に加工された`Entry`オブジェクトを受け取り、BigQueryなどの永続化ストアに書き込みます。

## 4. ディレクトリ構成

```
rag-pipeline/
├── rag.yaml
├── STACK.md
├── DESIGN.md
├── TODO.md
├── src/
│   ├── main.py
│   └── plugins/
│       ├── __init__.py
│       ├── base.py  # プラグインの基底クラス
│       ├── google_keep.py
│       └── ... (他のプラグイン)
└── tests/
    ├── __init__.py
    ├── test_google_keep.py
    └── ... (他のテスト)
```
