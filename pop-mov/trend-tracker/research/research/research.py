"""
YouTube雑学チャンネル 週次トレンドリサーチ (Qwen 版)
==========================================

使い方:
  python research.py              # フル実行
  python research.py --dry        # Qwen APIなしで動作確認
  python research.py --no-trends  # Googleトレンドスキップ

必要:
  pip install pytrends yt-dlp requests openai
  export QWEN_API_KEY=sk-...         # DashScope / OpenAI互換
  export YOUTUBE_API_KEY=AIza...     （オプション）
"""

import os, sys, json, time, argparse, subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

QWEN_API_KEY      = os.environ.get("QWEN_API_KEY", os.environ.get("DASHSCOPE_API_KEY", ""))
YOUTUBE_API_KEY   = os.environ.get("YOUTUBE_API_KEY", "")

SEED_KEYWORDS = ["雑学", "豆知識", "衝撃の真実", "日本の謎", "科学の不思議"]

# 監視チャンネル: {"表示名": "channel_id"} を自分でカスタム
WATCH_CHANNELS = {}

OUTPUT_DIR = Path(".")
DATA_DIR   = OUTPUT_DIR / "data"
QWEN_MODEL = "qwen-plus"
QWEN_BASE_URL = os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")


# ── ユーティリティ ──

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def save_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 1. Googleトレンド ──

def fetch_trends():
    log("Google Trends を取得中...")
    import requests

    # A: RSS（APIキー不要・安定）
    rss_items = []
    try:
        r = requests.get(
            "https://trends.google.com/trending/rss?geo=JP",
            timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        )
        root = ET.fromstring(r.content)
        rss_items = [el.text.strip() for el in root.findall(".//item/title") if el.text]
        log(f"  RSS: {len(rss_items)} 件")
    except Exception as e:
        log(f"  RSS失敗: {e}")

    # B: pytrends（関連クエリまで取得できる詳細版）
    pt_trending, pt_related = [], []
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="ja-JP", tz=540, timeout=(10, 25), retries=2, backoff_factor=0.5)
        df = pt.trending_searches(pn="japan")
        pt_trending = df[0].tolist()[:20]
        time.sleep(2)
        pt.build_payload(SEED_KEYWORDS[:5], geo="JP", timeframe="now 7-d")
        for kw, data in pt.related_queries().items():
            if data.get("top") is not None:
                for row in data["top"].head(5).to_dict("records"):
                    pt_related.append({"keyword": kw, "query": row["query"], "value": row["value"]})
        log(f"  pytrends: {len(pt_trending)} + 関連{len(pt_related)} 件")
    except Exception as e:
        log(f"  pytrends失敗: {e}")

    merged = list(dict.fromkeys(rss_items + pt_trending))[:30]
    return {"trending": merged, "related": pt_related}


# ── 2. YouTube ──

def fetch_channel_rss(channel_id):
    """チャンネルRSS（APIキー不要）"""
    import requests
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "media": "http://search.yahoo.com/mrss/",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        root = ET.fromstring(r.content)
        videos = []
        for entry in root.findall("atom:entry", ns)[:8]:
            vid_id = entry.findtext("yt:videoId", "", ns)
            vst = entry.find(".//media:statistics", ns)
            videos.append({
                "title": entry.findtext("atom:title", "", ns),
                "video_id": vid_id,
                "url": f"https://youtube.com/watch?v={vid_id}",
                "published": (entry.findtext("atom:published", "", ns) or "")[:10],
                "views": int(vst.get("views", 0)) if vst is not None else 0,
                "source": "channel_rss",
            })
        return videos
    except Exception as e:
        log(f"    チャンネルRSS失敗: {e}")
        return []

def fetch_youtube_api(query):
    """YouTube Data API v3（APIキーあり時）"""
    import requests
    base = "https://www.googleapis.com/youtube/v3/"
    since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
    try:
        # 検索
        sr = requests.get(base + "search", params={
            "part": "snippet", "q": query, "type": "video",
            "regionCode": "JP", "order": "viewCount",
            "publishedAfter": since, "maxResults": 15, "key": YOUTUBE_API_KEY,
        }, timeout=10).json()
        ids = [i["id"]["videoId"] for i in sr.get("items", [])]
        if not ids:
            return []
        # 統計
        vr = requests.get(base + "videos", params={
            "part": "snippet,statistics", "id": ",".join(ids), "key": YOUTUBE_API_KEY,
        }, timeout=10).json()
        result = []
        for item in vr.get("items", []):
            sn, st = item["snippet"], item.get("statistics", {})
            result.append({
                "title": sn["title"], "channel": sn["channelTitle"],
                "video_id": item["id"], "url": f"https://youtube.com/watch?v={item['id']}",
                "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                "published": sn.get("publishedAt", "")[:10], "source": "youtube_api",
            })
        return result
    except Exception as e:
        log(f"    YouTube API失敗: {e}")
        return []

def fetch_yt_dlp(query):
    """yt-dlp 検索（APIキーなしフォールバック）"""
    week_ago = (datetime.now() - timedelta(days=8)).strftime("%Y%m%d")
    try:
        res = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--dump-json",
             "--playlist-end", "20", "--no-warnings", "--ignore-errors",
             f"ytsearch20:{query}"],
            capture_output=True, text=True, timeout=45,
        )
        videos = []
        for line in res.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                d = json.loads(line)
                upload = d.get("upload_date", "")
                if upload and upload < week_ago:
                    continue   # 今週以外はスキップ
                videos.append({
                    "title": d.get("title", ""),
                    "channel": d.get("channel", d.get("uploader", "")),
                    "video_id": d.get("id", ""),
                    "url": d.get("webpage_url", ""),
                    "views": d.get("view_count") or 0,
                    "duration": d.get("duration") or 0,
                    "published": upload, "source": "yt_dlp",
                })
            except json.JSONDecodeError:
                pass
        return videos
    except FileNotFoundError:
        log("    yt-dlp が見つかりません（pip install yt-dlp）")
        return []
    except Exception as e:
        log(f"    yt-dlp失敗: {e}")
        return []

def fetch_youtube_data(trends):
    log("YouTube データを収集中...")
    all_videos = []

    # 監視チャンネルRSS
    if WATCH_CHANNELS:
        log("  チャンネルRSS...")
        for name, ch_id in WATCH_CHANNELS.items():
            vids = fetch_channel_rss(ch_id)
            log(f"    {name}: {len(vids)} 件")
            all_videos.extend(vids)

    # キーワード検索（API or yt-dlp）
    queries = SEED_KEYWORDS[:3]
    if trends.get("trending"):
        queries = [" ".join(trends["trending"][:2]) + " 雑学"] + queries

    if YOUTUBE_API_KEY:
        log("  YouTube Data API...")
        for q in queries[:2]:
            vids = fetch_youtube_api(q)
            log(f"    [{q[:20]}]: {len(vids)} 件")
            all_videos.extend(vids)
            time.sleep(1)
    else:
        log("  yt-dlp フォールバック（APIキーなし）...")
        for q in queries[:3]:
            vids = fetch_yt_dlp(q)
            log(f"    [{q[:20]}]: {len(vids)} 件")
            all_videos.extend(vids)
            time.sleep(1)

    # 重複除去 → 再生数でソート
    seen, unique = set(), []
    for v in all_videos:
        key = v.get("video_id") or v.get("url")
        if key and key not in seen:
            seen.add(key)
            unique.append(v)
    unique.sort(key=lambda x: x.get("views", 0), reverse=True)
    log(f"  合計: {len(unique)} 件（重複除去済み）")
    return unique


# ── 3. Qwen 分析 ──

ANALYSIS_PROMPT = """\
あなたはYouTube雑学チャンネルのコンテンツプランナーです。

## 今週の日本トレンドデータ

### Google急上昇キーワード
{trending}

### YouTube急上昇動画（今週）
{youtube}

### 関連検索クエリ（雑学軸）
{related}

---
以下の形式で出力してください。

### 📊 今週のトレンドサマリー
（3〜4文で全体傾向）

### 🔥 注目トピック TOP5
各トピック:
- **トピック名**
  - バズっている理由（1文）
  - 雑学として使えるアングル（1〜2文）
  - 推奨フォーマット: Shorts / 長尺 / 両方

### 💡 今すぐ作れる動画企画 3本
各企画:
- **タイトル案**（バズる形式で）
- 骨子（3点）
- 競合との差別化

### ⚡ 来週先取り候補（3つ）

簡潔・実践的に。前置き不要。
"""

def analyze_with_qwen(trends, videos, dry=False):
    if dry:
        log("--dry: Qwen APIスキップ")
        return "（dry run）"
    if not QWEN_API_KEY:
        return "⚠ QWEN_API_KEY 未設定"

    from openai import OpenAI
    log("Qwen で分析中...")

    fmt_views = lambda v: f"{v.get('views',0):,}" if isinstance(v.get('views'), int) else "?"
    prompt = ANALYSIS_PROMPT.format(
        trending="\n".join(f"- {k}" for k in trends.get("trending", [])[:20]) or "（なし）",
        youtube="\n".join(
            f"- {v['title']} [{v.get('channel','')}] 👁{fmt_views(v)}"
            for v in videos[:20]
        ) or "（なし）",
        related="\n".join(
            f"- [{r['keyword']}] {r['query']}" for r in trends.get("related", [])[:15]
        ) or "（なし）",
    )

    try:
        client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)
        resp = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.7,
            timeout=90,
        )
        text = resp.choices[0].message.content
        log("  → 分析完了")
        return text
    except Exception as e:
        log(f"  ⚠ Qwen APIエラー: {e}")
        return f"エラー: {e}"


# ── 4. レポート ──

def build_report(trends, videos, analysis):
    now = datetime.now()
    w0  = (now - timedelta(days=now.weekday())).strftime("%Y/%m/%d")
    w1  = (now - timedelta(days=now.weekday() - 6)).strftime("%Y/%m/%d")
    fmt = lambda v: f"{v.get('views',0):,}" if isinstance(v.get('views'), int) else "?"

    lines = [
        f"# 週次トレンドリサーチ {w0} 〜 {w1}",
        f"_生成: {now.strftime('%Y-%m-%d %H:%M')}_",
        "", "---", "## Qwen 分析", "", analysis, "",
        "---", "## 生データ: YouTube動画（今週）", "",
        *[f"{i}. [{v['title']}]({v.get('url','#')}) **{v.get('channel','')}** 👁{fmt(v)}"
          for i, v in enumerate(videos[:15], 1)],
        "", "---", "## 生データ: Googleトレンド", "",
        *[f"- {k}" for k in trends.get("trending", [])[:20]],
        "", "---", f"_次回: 来週月曜 `python research.py`_",
    ]
    return "\n".join(lines)


# ── メイン ──

def main():
    parser = argparse.ArgumentParser(description="YouTube雑学 週次トレンドリサーチ")
    parser.add_argument("--dry",        action="store_true")
    parser.add_argument("--no-trends",  action="store_true")
    parser.add_argument("--no-youtube", action="store_true")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y%m%d")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    log("=" * 55)
    log("YouTube雑学 週次トレンドリサーチ 開始")
    log("=" * 55)

    trends = fetch_trends()        if not args.no_trends  else {"trending": [], "related": []}
    time.sleep(1)
    videos = fetch_youtube_data(trends) if not args.no_youtube else []

    save_json({"trends": trends, "videos": videos, "at": datetime.now().isoformat()},
              DATA_DIR / f"raw_{date_str}.json")
    log(f"生データ → data/raw_{date_str}.json")

    analysis = analyze_with_qwen(trends, videos, dry=args.dry)
    report   = build_report(trends, videos, analysis)

    report_path = OUTPUT_DIR / f"report_{date_str}.md"
    report_path.write_text(report, encoding="utf-8")
    log(f"レポート → {report_path}")
    log("=" * 55)
    print()
    print(report[:1500])
    if len(report) > 1500:
        print(f"\n... (続き → {report_path})")

if __name__ == "__main__":
    main()
