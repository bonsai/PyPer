# 🚀 v3 改善計画書: 15秒生き物雑学動画

> 3人クロスレビュー結果に基づく。目標スコア: **85/100以上**

---

## 📊 現状診断（v2 → v3目標）

| 評価項目 | v2 | v3目標 | 差分 | 優先度 |
|---|---|---|---|---|
| 🔴 BGM/SE | 20 | **80** | +60 | ★★★★★ |
| 🔴 フック力 | 55 | **85** | +30 | ★★★★★ |
| 🔴 イラスト | 50 | **85** | +35 | ★★★★★ |
| 🟡 音声品質 | 75 | **90** | +15 | ★★★★ |
| 🟡 テロップ | 65 | **80** | +15 | ★★★ |
| 🟢 構成・尺 | 72 | **80** | +8 | ★★ |
| 🟢 サムネイル | 70 | **85** | +15 | ★★ |
| **総合** | **64** | **85** | **+21** | — |

---

## 🗂️ 改善タスク一覧

### Phase 1: 即時改善（次回投稿まで）→ 予測スコア: 78-80

---

#### Task 1: BGM追加（+10-15点）

**問題:** 3者全員が「BGMなしは致命傷」と指摘。世界観ゼロ。

**解決策:**
```
BGM仕様:
├── ソース: YouTube Audio Library（著作権フリー）
├── ジャンル: "Upbeat" or "Bright"（緊迫感より楽しさ優先）
├── 音量: -25dB（音声の20-25%）
├── テンポ: 120-140 BPM（15秒に合う軽快なリズム）
├── フェードイン: 0.5秒
└── フェードアウト: 0.3秒
```

**推奨トラック（YouTube Audio Library）:**
1. `Sneaky Snitch` - Kevin MacLeod（軽快・イタズラっぽい）
2. `Carefree` - Kevin MacLeod（明るくてポップ）
3. `Local Forecast - Elevator` - Kevin MacLeod（テンポ良い）

**実装方法:**
```python
# MoviePyでBGMをループ＋音量調整
bgm = AudioFileClip("bgm.mp3")
bgm = bgm.subclip(0, 15)  # 15秒にカット
bgm = bgm.volumex(0.20)   # 20%音量
bgm = bgm.audio_fadein(0.5).audio_fadeout(0.3)

# メイン音声 + ツッコミ音声 + BGM をミックス
final_audio = CompositeAudioClip([main_audio, tsukkomi_audio, bgm])
```

---

#### Task 2: いらすとや画像差し替え（+15-20点）

**問題:** 3者とも「手描きは恥ずかしい」「いらすとや本家に及ばない」。

**解決策:**
```
画像調達方針:
├── ソース: https://www.irasutoya.com/
├── 形式: PNG（透過背景）
├── サイズ: 400x400px以上
├── ライセンス: 無料利用可（商用利用も可能）
└── クレジット表記: 不要（任意）
```

**ダウンロードすべき画像リスト:**
| ネタ | 検索キーワード | 配置位置 |
|---|---|---|
| カタツムリ | 「カタツムリ イラスト」 | 中央上 (y=0.17) |
| ハチドリ | 「蜂鳥 イラスト」or「小鳥 イラスト」 | 中央上 (y=0.17) |
| 猫 | 「猫 ゴロゴロ イラスト」 | 中央上 (y=0.17) |

**実装方法:**
```python
# Pillow手描き → 外部画像読み込みに変更
def load_illustration(filename):
    img = Image.open(filename).convert("RGBA")
    img = img.resize((400, 400), Image.LANCZOS)
    return img

# 影付き配置
illust = load_illustration(f"images/{scene_data['illustration']}.png")
shadow = illust.filter(ImageFilter.GaussianBlur(radius=8))
```

**代替ソース（いらすとやにない場合）:**
- Pixabay: https://pixabay.com/（CC0ライセンス）
- FREEPIK: https://www.freepik.com/（要帰属表示）

---

#### Task 3: フック強化（+10-15点）

**問題:** 3者とも「冒頭の衝擊力が足りない」「スクロールされる」と指摘。

**解決策:**
```
フック改善案（3パターン検証）:

案A: 驚愕ワード型
└── 「99%が知らない！生き物の衝撃事実」
└── 冒頭1秒に赤字デカめで表示

案B: 自己顕示欲刺激型
└── 「知ってたら自慢できる雑学3選」
└── 友人に自慢できる＝保存・シェア促進

案C: 生存本能刺激型
└── 「死ぬ前に知れ！生き物の意外な真実」
└── はやり動画の「【命】」フォーマットを参考
```

**採用: 案A（99%が知らない型）**
- Gen Z: 「自己顕示欲」を刺激
- 中学生: 「友達に自慢できる」動機
- プロ: 「クリック率向上」の実績多数

**実装方法:**
```python
# 冒頭1.5秒のオーバーレイテキスト
hook_text = create_text_image(
    "99%が知らない！",
    fontsize=72,
    font_color=(255, 50, 50),  # 赤
    stroke_color=(0, 0, 0),
    stroke_width=5,
)
hook_clip = ImageClip(pil_to_np(hook_text)).set_duration(1.5)
hook_clip = hook_clip.set_position(("center", 0.10))
# 1.5秒後にフェードアウト
hook_clip = hook_clip.fx(vfx.fadeout, 0.3)
```

---

### Phase 2: 中期改善（1-2週間以内）→ 予測スコア: 82-85

---

#### Task 4: VOICEVOX音声への切り替え（+10-15点）

**問題:** 3者とも「棒読み感が残る」「感情表現が欲しい」と指摘。

**解決策:**
```
VOICEVOX設定:
├── メイン音声: ずんだもん（Normal / 速度1.1x）
├── ツッコミ音声: 四国めたん（Tsundere / 速度1.3x）
├── エンジン: VOICEVOX API（ローカル実行）
└── フォールバック: edge-tts（API недоступな場合）
```

**実装方法:**
```python
import requests

def generate_voice_voicevox(text, speaker_id, filename):
    """VOICEVOX APIで音声生成"""
    # 1. クエリ生成
    response = requests.post(
        "http://localhost:50021/audio_query",
        params={"text": text, "speaker": speaker_id}
    )
    query = response.json()

    # 2. 音声合成
    response = requests.post(
        "http://localhost:50021/synthesis",
        params={"speaker": speaker_id},
        headers={"Content-Type": "application/json"},
        json=query
    )

    with open(filename, "wb") as f:
        f.write(response.content)

# メイン: ずんだもん (speaker_id=3)
# ツッコミ: 四国めたん (speaker_id=2)
```

**インストール手順:**
1. VOICEVOXをダウンロード: https://voicevox.hiroshiba.jp/
2. VOICEVOXを起動（APIサーバーがlocalhost:50021で起動）
3. スクリプトからAPI呼び出し

**フォールバック:**
```python
try:
    generate_voice_voicevox(text, speaker_id, filepath)
except:
    generate_voice(text, filepath, VOICE_MAIN)  # edge-ttsに fallback
```

---

#### Task 5: SE（効果音）追加（+5点）

**問題:** 音声切り替え時の「掛け合い感」が弱い。

**解決策:**
```
SE追加計画:
├── ツッコミ開始時: 「ポン」音（0.1秒）
├── 背景切り替え時: 「シュッ」音（0.2秒）
├── テロップ出現時: 「パッ」音（0.05秒）
└── 音量: -20dB（音声より十分に小さく）
```

**SEソース:**
- 効果音ラボ: https://soundeffect-lab.com/
- 魔王魂: https://maoudamashii.jokersounds.com/

---

### Phase 3: 長期改善（1ヶ月以内）→ 予測スコア: 88-90

---

#### Task 6: テロップ・UI改善（+5-10点）

```
改善内容:
├── フォントサイズ: 52px → 64px（スマホ視認性向上）
├── テロップ位置: 中央 (0.52) → やや下 (0.60)（親指隠れ防止）
├── 情報削減: 1画面3要素までに制限
├── アニメーション: テキストのscale-inアニメ（0.2秒）
└── 絵文字対応: Unicode絵文字を画像として合成
```

#### Task 7: サムネイル改善（+10点）

```
改善内容:
├── タイトル: 「生き物雑学」→「99%が知らない！生き物雑学」
├── キャラサイズ: 300px → 400px（大きく表示）
├── 背景: グラデ → レイヤード（奥行き感）
├── 数字強調: 「3選」をデカく表示
└── CTA: 「保存してね」を追加
```

#### Task 8: 30秒版の並行制作

```
30秒版仕様:
├── 尺: 30秒（1ネタ10秒）
├── ネタ数: 3（不变）
├── メイン: 6秒/ネタ（説明を丁寧に）
├── ツッコミ: 4秒/ネタ（ゆとりある反応）
└── BGM: 同じトラックを30秒に延伸
```

---

## 📅 実装スケジュール

| Phase | タスク | 所要時間 | 完了目標日 |
|---|---|---|---|
| **Phase 1** | Task 1: BGM追加 | 1時間 | 今日 |
| | Task 2: いらすとや画像 | 30分 | 今日 |
| | Task 3: フック強化 | 30分 | 今日 |
| **Phase 2** | Task 4: VOICEVOX音声 | 2時間 | 今週中 |
| | Task 5: SE追加 | 1時間 | 今週中 |
| **Phase 3** | Task 6-8: UI/音声/30秒版 | 4時間 | 1ヶ月以内 |

---

## ✅ チェックリスト（v3実装前）

- [ ] VOICEVOXインストール済みか？
- [ ] いらすとや画像3点ダウンロード済みか？
- [ ] BGMファイル準備済みか？
- [ ] SEファイル準備済みか？
- [ ] テスト再生環境整っているか？

---

## 🎯 v3成功基準

| 指標 | 目標値 | 測定方法 |
|---|---|---|
| 総合レビュースコア | **85/100以上** | 同一3名で再レビュー |
| 完視聴率推測 | **50%以上** | YouTube Analytics（投稿後） |
| CTR（クリック率） | **8%以上** | YouTube Analytics |
| 保存率 | **5%以上** | YouTube Analytics |
| シェア意向（3者） | **2名以上が「する」** | 再レビュー |

---

_作成日: 2026-04-05_
_次ステップ: Phase 1の3タスクを一括実装 → v3スクリプト生成_
