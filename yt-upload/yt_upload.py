"""
YouTube Upload Script
Auto-detects latest SS-*.txt and rakugo_video.mp4
Uses YouTube Data API v3 with OAuth2
"""
import os
import sys
import glob as globmod
import re
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ============================================================
# CONFIG
# ============================================================
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "client_secret.json")
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "yt_credentials.json")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
VIDEO_FILE = os.path.join(OUTPUT_DIR, "rakugo_video.mp4")

VIDEO_CATEGORY = "24"  # Entertainment
VIDEO_PRIVACY = "private"  # private, public, unlisted

# ============================================================
# AUTO-DETECT
# ============================================================

def find_latest_rakugo():
    """Find the most recently modified SS-*.txt file."""
    base = os.path.dirname(__file__)
    files = globmod.glob(os.path.join(base, "SS-*.txt"))
    if not files:
        raise FileNotFoundError("No SS-*.txt files found!")
    return max(files, key=os.path.getmtime)


def parse_title(filepath):
    """Extract title from first h1."""
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^#\s+(.+)", line.strip())
            if m:
                return m.group(1).strip()
    return "SF落語"


def parse_subtitle(filepath):
    """Extract subtitle from first h2."""
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^##\s+(.+)", line.strip())
            if m:
                return m.group(1).strip()
    return None


def extract_keywords(filepath):
    """Extract keywords for tags."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    tag_map = {
        "落語": True, "SF": True, "AI": True, "人工知能": "人工知能" in text,
        "軽量AI": "軽量" in text or "2GB" in text or "軽い" in text,
        "llama.cpp": "llama" in text.lower() or "cpp" in text.lower(),
        "スパイス": "スパイス" in text or "カレー" in text,
        "創作落語": True, "AI落語": True,
        "西荻窪": "西荻窪" in text, "渋谷": "渋谷" in text, "東京": "東京" in text,
        "未来都市": "未来都市" in text, "ノマド": "ノマド" in text,
        "探偵": "探偵" in text, "プロジェクション": "プロジェクション" in text,
        "ラップ": "ラップ" in text or "rap" in text.lower(),
    }
    return [k for k, v in tag_map.items() if v]


def build_description(filepath):
    """Auto-generate YouTube description from rakugo file."""
    title = parse_title(filepath)
    subtitle = parse_subtitle(filepath)
    filename = os.path.basename(filepath)

    desc = f"""{title}

{subtitle if subtitle else ''}

#{" ".join(extract_keywords(filepath))}

---
ファイル: {filename}
作・編集：AI & おっさんコンビ
音声：Edge TTS（ja-JP-KeitaNeural）
サムネイル：Pillow生成イラスト
動画：MoviePy組み立て
""".strip()
    return desc


# ============================================================
# AUTH
# ============================================================

def get_authenticated_service():
    """Authenticate and return YouTube API service."""
    credentials = None

    if os.path.exists(CREDENTIALS_FILE):
        credentials = Credentials.from_authorized_user_file(CREDENTIALS_FILE, SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"[ERROR] {CLIENT_SECRETS_FILE} not found!")
                sys.exit(1)

            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES
            )
            credentials = flow.run_local_server(port=0, prompt="consent")

        with open(CREDENTIALS_FILE, "w") as f:
            f.write(credentials.to_json())
        print("[AUTH] Credentials saved/refreshed.")

    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials
    )


# ============================================================
# UPLOAD
# ============================================================

def upload_video(youtube, video_file, title, description, tags, category_id, privacy):
    """Upload video to YouTube."""
    if not os.path.exists(video_file):
        print(f"[ERROR] Video file not found: {video_file}")
        sys.exit(1)

    file_size = os.path.getsize(video_file)
    print(f"[UPLOAD] File: {video_file}")
    print(f"[UPLOAD] Size: {file_size / (1024*1024):.1f} MB")
    print(f"[UPLOAD] Title: {title}")
    print(f"[UPLOAD] Privacy: {privacy}")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": "ja",
        },
        "status": {
            "privacyStatus": privacy,
        },
    }

    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    print("[UPLOAD] Starting upload (resumable)...")
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"\r[UPLOAD] Progress: {progress}%", end="", flush=True)

    print(f"\n[UPLOAD] Complete!")
    video_id = response.get("id", "")
    print(f"[UPLOAD] Video ID: {video_id}")
    print(f"[UPLOAD] URL: https://www.youtube.com/watch?v={video_id}")
    return video_id


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  YouTube Video Uploader")
    print("=" * 60)

    # Auto-detect rakugo file
    rakugo_file = find_latest_rakugo()
    print(f"\n[AUTO] Source: {os.path.basename(rakugo_file)}")

    title = parse_title(rakugo_file)
    subtitle = parse_subtitle(rakugo_file)
    tags = extract_keywords(rakugo_file)
    description = build_description(rakugo_file)

    yt_title = f"{title}"
    if subtitle:
        yt_title += f"〜{subtitle}〜"
    else:
        yt_title += "〜AI時代の新感覚落語〜"

    print(f"  Title: {yt_title}")
    print(f"  Tags: {', '.join(tags)}")

    print("\n[AUTH] Authenticating with YouTube Data API v3...")
    youtube = get_authenticated_service()

    print("\n[UPLOAD] Uploading video...")
    video_id = upload_video(
        youtube, VIDEO_FILE, yt_title, description,
        tags, VIDEO_CATEGORY, VIDEO_PRIVACY
    )

    print("\n" + "=" * 60)
    print(f"  ✅ UPLOAD COMPLETE")
    print(f"  📺 https://www.youtube.com/watch?v={video_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
