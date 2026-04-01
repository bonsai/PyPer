#!/usr/bin/env python3
"""
Gmail OAuth2 認証セットアップスクリプト

このスクリプトは Gmail API の OAuth2 認証を設定し、
リフレッシュトークンを取得します。

使用方法:
    python scripts/setup_oauth.py

事前準備:
    1. Google Cloud Console でプロジェクトを作成
    2. Gmail API を有効化
    3. OAuth 2.0 クライアント ID を作成（デスクトップアプリ）
    4. クライアント ID とシークレットを控える
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv

# 環境変数を読み込む
env_file = project_root / "config" / "envs" / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
    print(f".env.local を読み込みました：{env_file}")
else:
    print(f"警告：.env.local が見つかりません：{env_file}")
    print("config/envs/.env.example をコピーして設定してください")


def get_oauth_tokens():
    """
    OAuth2 認証フローを実行し、アクセストークンとリフレッシュトークンを取得。
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    import json
    
    # 環境変数から認証情報を取得
    client_id = os.environ.get("OAUTH_CLIENT_ID")
    client_secret = os.environ.get("OAUTH_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("\nエラー：OAuth 認証情報が見つかりません")
        print(".env.local に以下を設定してください:")
        print("  OAUTH_CLIENT_ID=your_client_id")
        print("  OAUTH_CLIENT_SECRET=your_client_secret")
        return None, None
    
    # クライアント設定を作成
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
        }
    }
    
    # 必要なスコープ
    SCOPES = [
        "https://mail.google.com/",  # Gmail 送信
    ]
    
    print("\n===== Gmail OAuth2 認証 =====")
    print(f"クライアント ID: {client_id[:20]}...")
    print(f"スコープ：{SCOPES}")
    
    try:
        # フローを作成
        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=SCOPES
        )
        
        # 認証 URL を表示
        print("\n以下の URL をブラウザで開いて認証してください:")
        print("-" * 60)
        
        # 認証 URL を生成
        auth_url, _ = flow.authorization_url(
            prompt='consent',
            access_type='offline',
            include_granted_scopes='true'
        )
        
        print(auth_url)
        print("-" * 60)
        
        # 認証コードを入力
        print("\n認証後、表示される認証コードをここに貼り付けて Enter キーを押してください:")
        auth_code = input("> ").strip()
        
        if not auth_code:
            print("認証コードが入力されませんでした")
            return None, None
        
        # トークンを取得
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials
        
        access_token = credentials.token
        refresh_token = credentials.refresh_token
        
        print("\n✓ 認証成功！")
        print(f"アクセストークン：{access_token[:20]}...")
        print(f"リフレッシュトークン：{refresh_token[:20] if refresh_token else 'N/A'}...")
        
        return access_token, refresh_token
        
    except Exception as e:
        print(f"\nエラー：{e}")
        print("\n代替方法：以下の URL を直接使用してください")
        
        # 手動認証 URL
        manual_url = (
            f"https://accounts.google.com/o/oauth2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri=urn:ietf:wg:oauth:2.0:oob"
            f"&response_type=code"
            f"&scope={'%20'.join(SCOPES)}"
            f"&access_type=offline"
            f"&prompt=consent"
        )
        print(manual_url)
        return None, None


def save_to_env(access_token: str = None, refresh_token: str = None):
    """
    取得したトークンを .env.local に保存
    """
    env_path = project_root / "config" / "envs" / ".env.local"
    
    # 既存の .env.local を読み込む
    env_content = ""
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            env_content = f.read()
    
    # トークンを更新
    lines = env_content.split('\n')
    new_lines = []
    updated = {
        'OAUTH_ACCESS_TOKEN': False,
        'OAUTH_REFRESH_TOKEN': False
    }
    
    for line in lines:
        if line.startswith('OAUTH_ACCESS_TOKEN='):
            new_lines.append(f'OAUTH_ACCESS_TOKEN={access_token}')
            updated['OAUTH_ACCESS_TOKEN'] = True
        elif line.startswith('OAUTH_REFRESH_TOKEN='):
            new_lines.append(f'OAUTH_REFRESH_TOKEN={refresh_token}')
            updated['OAUTH_REFRESH_TOKEN'] = True
        else:
            new_lines.append(line)
    
    # 存在しない場合は追加
    if not updated['OAUTH_ACCESS_TOKEN'] and access_token:
        new_lines.append(f'OAUTH_ACCESS_TOKEN={access_token}')
    if not updated['OAUTH_REFRESH_TOKEN'] and refresh_token:
        new_lines.append(f'OAUTH_REFRESH_TOKEN={refresh_token}')
    
    # 保存
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"\n✓ トークンを {env_path} に保存しました")


def main():
    """メイン関数"""
    print("=" * 60)
    print("Gmail OAuth2 セットアップ")
    print("=" * 60)
    
    # ステップ 1: 認証情報チェック
    client_id = os.environ.get("OAUTH_CLIENT_ID")
    client_secret = os.environ.get("OAUTH_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("\n[ステップ 1] 認証情報の設定")
        print("Google Cloud Console で以下を作成してください:")
        print("  1. https://console.cloud.google.com/")
        print("  2. プロジェクト作成")
        print("  3. Gmail API を有効化")
        print("  4. 同意画面を設定")
        print("  5. OAuth 2.0 クライアント ID を作成（種類：デスクトップアプリ）")
        print("  6. クライアント ID とシークレットを .env.local に設定")
        return 1
    
    print("\n[ステップ 1] 認証情報を確認 ✓")
    
    # ステップ 2: トークン取得
    print("\n[ステップ 2] OAuth トークン取得")
    access_token, refresh_token = get_oauth_tokens()
    
    if not refresh_token:
        print("\nエラー：リフレッシュトークンの取得に失敗しました")
        return 1
    
    # ステップ 3: 保存
    print("\n[ステップ 3] トークンの保存")
    save_to_env(access_token, refresh_token)
    
    # ステップ 4: 設定確認
    print("\n[ステップ 4] 設定確認")
    print(".env.local の設定:")
    print(f"  GMAIL_USERNAME={os.environ.get('GMAIL_USERNAME', '未設定')}")
    print(f"  USE_OAUTH={os.environ.get('USE_OAUTH', 'true')}")
    print(f"  OAUTH_CLIENT_ID={client_id[:20]}...")
    print(f"  OAUTH_REFRESH_TOKEN={refresh_token[:20]}...")
    
    print("\n" + "=" * 60)
    print("セットアップ完了！")
    print("=" * 60)
    print("\n次のコマンドでテスト送信できます:")
    print(f"  python {project_root / 'scripts' / 'run_prtimes.py'}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
