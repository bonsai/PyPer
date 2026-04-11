# PyPer Plugin Roadmap 2026-2027

## 📜 設計思想

> **PyPerの使命**: Plaggerにない**モダンなプラグイン**をひたすら貯める
> 
> Plagger (2006-2010) はRSS/Atom時代の遺産。
> PyPer (2026-) は**LLM・MCP・クラウド・リアルタイム時代**のプラガブルエンジンである。

---

## 🏗️ Plugin Architecture

```
PyPer/src/plugins/
├── base.py                     # Entry, BasePlugin, etc.
├── subscription/               # データ入力 (Input)
├── filter/                     # データ処理 (Process)
├── publish/                    # データ出力 (Output)
├── processor/                  # 双方向処理 (Bidirectional)
└── notify/                     # 通知 (Alert)
```

### Entryデータモデル

```python
@dataclass
class Entry:
    id: str                     # SHA-256
    source: str                 # "Subscription::RSS::https://..."
    content: str                # 本文
    vector: List[float]         # 埋め込みベクトル
    metadata: Dict[str, Any]    # タイトル、URL、タグ等
    timestamp: int              # エポック秒
```

---

## 🗺️ ロードマップ

### Phase 1: LLM・AI統合（2026 Q2）🔥 進行中

#### Subscription

| Plugin | Description | Priority |
|--------|-------------|----------|
| `subscription.llm_chat.Plugin` | LLMとの対話をSubscriptionとして記録 | 🔴 High |
| `subscription.huggingface.Plugin` | HuggingFaceモデル/データセット監視 | 🟡 Medium |
| `subscription.openai_fine_tune.Plugin` | OpenAI Fine-tuningジョブ監視 | 🟢 Low |

#### Filter

| Plugin | Description | Priority |
|--------|-------------|----------|
| `filter.llm_summarize.Plugin` | LLMによる要約（OpenAI/Anthropic/Gemini/Qwen） | 🔴 High |
| `filter.llm_translate.Plugin` | LLM翻訳（多言語対応） | 🔴 High |
| `filter.llm_sentiment.Plugin` | 感情分析（positive/neutral/negative） | 🟡 Medium |
| `filter.llm_categorize.Plugin` | 自動カテゴリ分類 | 🟡 Medium |
| `filter.llm_extract.Plugin` | 固有表現抽出（人名、組織、金額） | 🟡 Medium |
| `filter.llm_rewrite.Plugin` | スタイル変換（カジュアル→フォーマル） | 🟢 Low |
| `filter.llm_qa.Plugin` | Q&A生成（FAQ自動作成） | 🟢 Low |
| `filter.vectorize.Plugin` | 埋め込みベクトル化（OpenAI/Gemini） | 🔴 High |
| `filter.rag_query.Plugin` | RAG検索（ベクトルDB連携） | 🔴 High |

#### Publish

| Plugin | Description | Priority |
|--------|-------------|----------|
| `publish.chat.Plugin` | LLMチャットボットとして応答 | 🔴 High |
| `publish.voice.Plugin` | テキスト→音声（ElevenLabs/OpenAI TTS） | 🟡 Medium |
| `publish.image.Plugin` | テキスト→画像（DALL-E/Stable Diffusion） | 🟡 Medium |

---

### Phase 2: モダンSaaS統合（2026 Q3）

#### Subscription

| Plugin | Description | Priority |
|--------|-------------|----------|
| `subscription.notion.Plugin` | Notion DB/Page監視 | 🔴 High |
| `subscription.google_drive.Plugin` | Google Driveファイル変更監視 | 🔴 High |
| `subscription.github.Plugin` | GitHub Issues/PR/Actions監視 | 🔴 High |
| `subscription.slack.Plugin` | Slackチャンネルメッセージ取得 | 🟡 Medium |
| `subscription.discord.Plugin` | Discordチャンネルメッセージ取得 | 🟡 Medium |
| `subscription.linear.Plugin` | Linearイシュー監視 | 🟢 Low |
| `subscription.jira.Plugin` | Jiraイシュー監視 | 🟢 Low |
| `subscription.trello.Plugin` | Trelloボード監視 | 🟢 Low |
| `subscription.asana.Plugin` | Asanaタスク監視 | 🟢 Low |
| `subscription.salesforce.Plugin` | Salesforceリード監視 | 🟢 Low |
| `subscription.hubspot.Plugin` | HubSpotコンタクト監視 | 🟢 Low |
| `subscription.shopify.Plugin` | Shopify注文監視 | 🟢 Low |

#### Publish

| Plugin | Description | Priority |
|--------|-------------|----------|
| `publish.notion.Plugin` | Notionページ自動作成 | 🔴 High |
| `publish.google_docs.Plugin` | Google Docs自動作成 | 🟡 Medium |
| `publish.obsidian.Plugin` | Obsidian VaultにMarkdown追加 | 🟡 Medium |
| `publish.logseq.Plugin` | Logseqグラフにページ追加 | 🟡 Medium |
| `publish.airtable.Plugin` | Airtableレコード追加 | 🟢 Low |
| `publish.clickup.Plugin` | ClickUpタスク作成 | 🟢 Low |

---

### Phase 3: メディア・コンテンツ生成（2026 Q3-Q4）

#### Subscription

| Plugin | Description | Priority |
|--------|-------------|----------|
| `subscription.youtube.Plugin` | YouTubeチャンネル/検索監視 | 🔴 High |
| `subscription.tiktok.Plugin` | TikTokトレンド監視 | 🟡 Medium |
| `subscription.spotify.Plugin` | Spotifyプレイリスト/新曲監視 | 🟡 Medium |
| `subscription.podcast.Plugin` | ポッドキャスト新エピソード監視 | 🟡 Medium |
| `subscription.reddit.Plugin` | サブレディット投稿監視 | 🟡 Medium |
| `subscription.twitter.Plugin` | Twitter/Xリスト/キーワード監視 | 🔴 High |
| `subscription.instagram.Plugin` | Instagram投稿監視 | 🟢 Low |
| `subscription.twitch.Plugin` | Twitch配信開始通知 | 🟢 Low |

#### Filter

| Plugin | Description | Priority |
|--------|-------------|----------|
| `filter.transcribe.Plugin` | 音声→文字起こし（Whisper） | 🔴 High |
| `filter.ocr.Plugin` | 画像→テキスト（Qwen2.5-VL） | 🔴 High |
| `filter.thumbnail.Plugin` | サムネイル自動生成 | 🟡 Medium |
| `filter.video_clip.Plugin` | 動画ハイライト抽出 | 🟡 Medium |
| `filter.music_gen.Plugin` | BGM自動生成 | 🟢 Low |

#### Publish

| Plugin | Description | Priority |
|--------|-------------|----------|
| `publish.youtube.Plugin` | YouTube動画投稿 | 🟡 Medium |
| `publish.twitter_video.Plugin` | Twitter用動画生成 | 🟡 Medium |
| `publish.blog.Plugin` | ブログ自動投稿（WordPress/Hatena） | 🔴 High |
| `publish.medium.Plugin` | Medium記事投稿 | 🟢 Low |
| `publish.substack.Plugin` | Substackニュースレター送信 | 🟢 Low |

---

### Phase 4: データ基盤（2026 Q4）

#### Subscription

| Plugin | Description | Priority |
|--------|-------------|----------|
| `subscription.postgres.Plugin` | PostgreSQLクエリ監視 | 🔴 High |
| `subscription.bigquery.Plugin` | BigQueryクエリ結果取得 | 🟡 Medium |
| `subscription.snowflake.Plugin` | Snowflakeクエリ結果取得 | 🟢 Low |
| `subscription.s3.Plugin` | S3バケット変更監視 | 🟡 Medium |
| `subscription.webhook.Plugin` | Webhook受信 | 🔴 High |
| `subscription.websocket.Plugin` | WebSocketリアルタイム受信 | 🟡 Medium |
| `subscription.sse.Plugin` | Server-Sent Events受信 | 🟡 Medium |
| `subscription.kafka.Plugin` | Kafkaトピック購読 | 🟢 Low |
| `subscription.redis.Plugin` | Redis Pub/Sub購読 | 🟢 Low |

#### Filter

| Plugin | Description | Priority |
|--------|-------------|----------|
| `filter.sql.Plugin` | SQL変換・最適化 | 🟡 Medium |
| `filter.pandas.Plugin` | Pandasデータフレーム処理 | 🔴 High |
| `filter.dedup.Plugin` | 重複除外（ベクトル類似度） | 🔴 High |
| `filter.dedupe_semantic.Plugin` | 意味的重複除外 | 🟡 Medium |
| `filter.cluster.Plugin` | クラスタリング | 🟢 Low |
| `filter.anomaly.Plugin` | 異常検知 | 🟢 Low |
| `filter.forecast.Plugin` | 時系列予測 | 🟢 Low |

#### Publish

| Plugin | Description | Priority |
|--------|-------------|----------|
| `publish.bigquery.Plugin` | BigQueryテーブル挿入 | 🟡 Medium |
| `publish.s3.Plugin` | S3アップロード | 🟡 Medium |
| `publish.gcs.Plugin` | Google Cloud Storageアップロード | 🟡 Medium |
| `publish.postgres.Plugin` | PostgreSQL挿入 | 🟡 Medium |
| `publish.csv.Plugin` | CSV/Excelファイル出力 | 🔴 High |
| `publish.jsonl.Plugin` | JSONLファイル出力 | 🟡 Medium |
| `publish.parquet.Plugin` | Parquetファイル出力 | 🟢 Low |
| `publish.dashboard.Plugin` | Grafana/Dashボード更新 | 🟢 Low |

---

### Phase 5: コミュニケーション（2026 Q4-2027 Q1）

#### Subscription

| Plugin | Description | Priority |
|--------|-------------|----------|
| `subscription.gmail.Plugin` | Gmail特定ラベル監視 | 🔴 High |
| `subscription.outlook.Plugin` | Outlookメール監視 | 🟡 Medium |
| `subscription.line.Plugin` | LINEメッセージ受信 | 🔴 High |
| `subscription.whatsapp.Plugin` | WhatsAppメッセージ受信 | 🟡 Medium |
| `subscription.telegram.Plugin` | Telegramチャンネル監視 | 🟡 Medium |
| `subscription.calendar.Plugin` | Google/Outlook Calendar予定監視 | 🔴 High |
| `subscription.zoom.Plugin` | Zoom会議録監視 | 🟢 Low |
| `subscription.meet.Plugin` | Google Meet議事録監視 | 🟢 Low |

#### Publish

| Plugin | Description | Priority |
|--------|-------------|----------|
| `publish.gmail.Plugin` | Gmail送信（既存） | ✅ Done |
| `publish.outlook.Plugin` | Outlook送信 | 🟡 Medium |
| `publish.line.Plugin` | LINEメッセージ送信 | 🔴 High |
| `publish.line_notify.Plugin` | LINE Notify通知（既存） | ✅ Done |
| `publish.whatsapp.Plugin` | WhatsApp送信 | 🟡 Medium |
| `publish.telegram.Plugin` | Telegram送信 | 🟡 Medium |
| `publish.slack.Plugin` | Slackメッセージ送信 | 🟡 Medium |
| `publish.discord.Plugin` | Discordメッセージ送信 | 🟡 Medium |
| `publish.teams.Plugin` | Microsoft Teams送信 | 🟢 Low |
| `publish.sms.Plugin` | SMS送信（Twilio） | 🟡 Medium |
| `publish.fax.Plugin` | FAX送信（クラウドFAX） | 🟢 Low |

---

### Phase 6: デベロッパーツール（2027 Q1）

#### Subscription

| Plugin | Description | Priority |
|--------|-------------|----------|
| `subscription.github_actions.Plugin` | GitHub Actions実行監視 | 🔴 High |
| `subscription.gitlab_ci.Plugin` | GitLab CI/CDパイプライン監視 | 🟡 Medium |
| `subscription.circleci.Plugin` | CircleCIジョブ監視 | 🟢 Low |
| `subscription.jenkins.Plugin` | Jenkinsジョブ監視 | 🟢 Low |
| `subscription.sentry.Plugin` | Sentryエラー監視 | 🔴 High |
| `subscription.datadog.Plugin` | Datadogメトリクス/アラート監視 | 🟡 Medium |
| `subscription.newrelic.Plugin` | New Relicアラート監視 | 🟢 Low |
| `subscription.pagerduty.Plugin` | PagerDutyインシデント監視 | 🟢 Low |
| `subscription.terraform.Plugin` | Terraform計画/適用結果監視 | 🟢 Low |

#### Filter

| Plugin | Description | Priority |
|--------|-------------|----------|
| `filter.code_review.Plugin` | コードレビュー自動生成 | 🔴 High |
| `filter.changelog.Plugin` | 変更履歴自動生成 | 🟡 Medium |
| `filter.release_notes.Plugin` | リリースノート自動生成 | 🟡 Medium |
| `filter.test_summary.Plugin` | テスト結果要約 | 🟡 Medium |
| `filter.security_scan.Plugin` | セキュリティスキャン結果解析 | 🔴 High |
| `filter.dependency.Plugin` | 依存関係脆弱性チェック | 🟡 Medium |

#### Publish

| Plugin | Description | Priority |
|--------|-------------|----------|
| `publish.github_issue.Plugin` | GitHub Issue自動作成 | 🔴 High |
| `publish.github_pr.Plugin` | GitHub PR自動作成 | 🟡 Medium |
| `publish.jira_issue.Plugin` | Jiraイシュー自動作成 | 🟡 Medium |
| `publish.linear_issue.Plugin` | Linearイシュー自動作成 | 🟡 Medium |
| `publish.runbook.Plugin` | Runbook自動生成 | 🟢 Low |
| `publish.postmortem.Plugin` | Postmortem自動生成 | 🟢 Low |

---

### Phase 7: IoT・物理世界（2027 Q1-Q2）

#### Subscription

| Plugin | Description | Priority |
|--------|-------------|----------|
| `subscription.mqtt.Plugin` | MQTTブローカー購読 | 🔴 High |
| `subscription.homeassistant.Plugin` | Home Assistantデバイス状態監視 | 🟡 Medium |
| `subscription.ifttt.Plugin` | IFTTT Webhook受信 | 🟡 Medium |
| `subscription.bluetooth.Plugin` | BLEビーコン監視 | 🟢 Low |
| `subscription.gps.Plugin` | GPS位置情報監視 | 🟢 Low |
| `subscription.weather.Plugin` | 気象庁API監視 | 🟡 Medium |
| `subscription.earthquake.Plugin` | 地震速報監視 | 🟡 Medium |

#### Publish

| Plugin | Description | Priority |
|--------|-------------|----------|
| `publish.mqtt.Plugin` | MQTTブローカー送信 | 🔴 High |
| `publish.homeassistant.Plugin` | Home Assistantデバイス操作 | 🟡 Medium |
| `publish.ifttt.Plugin` | IFTTTアプレット実行 | 🟡 Medium |
| `publish.smart_plug.Plugin` | スマートプラグ制御 | 🟢 Low |
| `publish.alarm.Plugin` | アラーム/サイレン制御 | 🟢 Low |
| `publish.printer.Plugin` | ネットワークプリンター印刷 | 🟢 Low |

---

### Phase 8: 金融・ビジネス（2027 Q2）

#### Subscription

| Plugin | Description | Priority |
|--------|-------------|----------|
| `subscription.crypto.Plugin` | 暗号通貨価格監視 | 🔴 High |
| `subscription.stock.Plugin` | 株式価格監視 | 🔴 High |
| `subscription.fx.Plugin` | 為替レート監視 | 🟡 Medium |
| `subscription.google_trends.Plugin` | Googleトレンド監視 | 🟡 Medium |
| `subscription.amazon.Plugin` | Amazon価格/ランキング監視 | 🟡 Medium |
| `subscription.rakuten.Plugin` | 楽天ランキング監視 | 🟡 Medium |
| `subscription.gov.Plugin` | 官報/自治体情報監視 | 🟢 Low |

#### Filter

| Plugin | Description | Priority |
|--------|-------------|----------|
| `filter.financial_analysis.Plugin` | 財務分析 | 🔴 High |
| `filter.portfolio.Plugin` | ポートフォリオ最適化提案 | 🟡 Medium |
| `filter.tax.Plugin` | 税務計算 | 🟡 Medium |

#### Publish

| Plugin | Description | Priority |
|--------|-------------|----------|
| `publish.trade.Plugin` | 自動取引（要審査） | 🟢 Low |
| `publish.report.Plugin` | 財務レポート自動生成 | 🟡 Medium |
| `publish.invoice.Plugin` | 請求書自動作成 | 🟡 Medium |

---

### Phase 9: MCP・エージェント統合（2027 Q2-Q3）🌟

#### Subscription

| Plugin | Description | Priority |
|--------|-------------|----------|
| `subscription.mcp.Plugin` | MCP Serverツール呼び出し結果取得 | 🔴 High |
| `subscription.agent.Plugin` | AIエージェント実行結果取得 | 🔴 High |
| `subscription.multi_agent.Plugin` | マルチエージェント合意取得 | 🟡 Medium |

#### Filter

| Plugin | Description | Priority |
|--------|-------------|----------|
| `filter.agent_chain.Plugin` | エージェント連鎖実行 | 🔴 High |
| `filter.reflection.Plugin` | 自己改善（Reflection） | 🔴 High |
| `filter.debate.Plugin` | エージェント間討論 | 🟡 Medium |
| `filter.vote.Plugin` | エージェント間投票 | 🟡 Medium |
| `filter.memory.Plugin` | 長期記憶コンテキスト注入 | 🔴 High |

#### Publish

| Plugin | Description | Priority |
|--------|-------------|----------|
| `publish.mcp.Plugin` | MCP Serverツール実行 | 🔴 High |
| `publish.agent.Plugin` | AIエージェントタスク実行 | 🔴 High |
| `publish.human_handoff.Plugin` | 人間のエスカレーション | 🟡 Medium |

---

### Phase 10: プラットフォーム拡張（2027 Q3-）

#### Subscription

| Plugin | Description | Priority |
|--------|-------------|----------|
| `subscription.filesystem.Plugin` | ローカルファイル監視 | 🔴 High |
| `subscription.clipboard.Plugin` | クリップボード監視 | 🟡 Medium |
| `subscription.screen.Plugin` | スクリーンショット監視 | 🟡 Medium |
| `subscription.microphone.Plugin` | 音声入力監視 | 🟡 Medium |
| `subscription.camera.Plugin` | カメラ画像監視 | 🟢 Low |
| `subscription.keyboard.Plugin` | キー入力マクロ記録 | 🟢 Low |
| `subscription.mouse.Plugin` | マウス操作記録 | 🟢 Low |

#### Filter

| Plugin | Description | Priority |
|--------|-------------|----------|
| `filter.prompt_inject.Plugin` | プロンプトインジェクション（テンプレート） | 🔴 High |
| `filter.cache.Plugin` | 結果キャッシュ | 🔴 High |
| `filter.rate_limit.Plugin` | レート制限 | 🔴 High |
| `filter.retry.Plugin` | リトライロジック | 🟡 Medium |
| `filter.batch.Plugin` | バッチ処理 | 🟡 Medium |
| `filter.parallel.Plugin` | 並列処理 | 🟡 Medium |
| `filter.workflow.Plugin` | ワークフロー制御 | 🔴 High |

#### Publish

| Plugin | Description | Priority |
|--------|-------------|----------|
| `publish.web_scraper.Plugin` | Webスクレイピング結果保存 | 🔴 High |
| `publish.api_server.Plugin` | REST APIサーバー公開 | 🔴 High |
| `publish.graphql.Plugin` | GraphQLサーバー公開 | 🟡 Medium |
| `publish.grpc.Plugin` | gRPCサーバー公開 | 🟢 Low |
| `publish.websocket_server.Plugin` | WebSocketサーバー公開 | 🟡 Medium |
| `publish.lambda.Plugin` | AWS Lambda関数実行 | 🟡 Medium |
| `publish.cloud_run.Plugin` | Google Cloud Runコンテナ実行 | 🟡 Medium |

---

## 📊 統計

### 現在のプラグイン数

| カテゴリ | 既存 | 計画 | 合計 |
|----------|------|------|------|
| Subscription | 3 | 47 | 50 |
| Filter | 3 | 38 | 41 |
| Publish | 4 | 45 | 49 |
| Notify | 1 | 5 | 6 |
| **合計** | **11** | **135** | **146** |

### 達成度

```
Phase 1: LLM・AI統合       ████████░░ 80%
Phase 2: モダンSaaS統合     ██░░░░░░░░ 20%
Phase 3: メディア・生成      █░░░░░░░░░ 10%
Phase 4: データ基盤         ░░░░░░░░░░  0%
Phase 5: コミュニケーション  ██░░░░░░░░ 20%
Phase 6: デベロッパーツール  ░░░░░░░░░░  0%
Phase 7: IoT・物理世界      ░░░░░░░░░░  0%
Phase 8: 金融・ビジネス     ░░░░░░░░░░  0%
Phase 9: MCP・エージェント  ░░░░░░░░░░  0%
Phase 10: プラットフォーム   ░░░░░░░░░░  0%
```

---

## 🎯 優先ルール

1. **ユーザー価値が高いもの** → Gmail, LINE, Notion, LLM
2. **Plaggerにないもの** → MCP, LLM, VectorDB, IoT
3. **実装が容易なもの** → Webhook, REST API連携
4. **デモ映えするもの** → 画像生成, 音声合成, 動画編集

---

## 🔄 開発フロー

```
1. issue作成 → "Add subscription/xyz.Plugin"
2. プラグイン実装 → src/plugins/subscription/xyz.py
3. 設定サンプル → recipe/templates/xyz.yaml
4. テスト → tests/plugins/test_xyz.py
5. ドキュメント → docs/plugins/xyz.md
6. レシピカタログ更新 → recipe/meta.yaml
```

---

*Created: 2026-04-11*
*Version: 0.1.0*
*Status: Planning*
