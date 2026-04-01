# TODOリスト

## MVP (Minimum Viable Product)

- [x] 設計ドキュメントの作成 (`STACK.md`, `DESIGN.md`, `TODO.md`)
- [x] プロジェクトのディレクトリ構造と空ファイルの作成
- [x] `requirements.txt` を作成し、依存ライブラリを管理する
- [x] コアエンジン (`src/main.py`) の実装
    - [x] `rag.yaml` の読み込み機能
    - [x] プラグインの動的ロード機能
    - [x] パイプライン実行ロジック
- [x] プラグインの基底クラス (`src/plugins/base.py`) の定義
- [x] `Subscription::GoogleKeep` プラグインの実装 (`src/plugins/google_keep.py`)
    - [x] Takeout JSON ファイルの読み込み
    - [x] `Entry` オブジェクトへの変換
- [x] `Publish::BigQuery` プラグインのスケルトン実装
    - [x] BigQueryへの接続とデータ書き込みの雛形作成
- [x] `Subscription::GoogleKeep` のユニットテスト (`tests/test_google_keep.py`)
    - [x] テスト用のダミーJSONファイルを用意
    - [x] ファイル読み込みが正しく行われるかテスト

## v1.1

- [x] `Filter::LLM::Vectorize` プラグインの実装
- [x] `Filter::LLM::MetadataEnricher` プラグインの実装
- [ ] `Publish::Gmail` プラグインの実装
- [ ] ロギング機能の強化
- [ ] エラーハンドリングの強化
- [ ] 他の `Subscription` プラグインの実装
