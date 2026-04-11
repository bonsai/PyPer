#!/usr/bin/env python3
"""
Gmail OAuth2 認証設定スクリプト

Gmail API 送信用の OAuth2 トークンを取得し、
環境変数ファイルに設定します。

使用方法:
    python scripts/setup_oauth.py

事前準備:
    1. Google Cloud Console でプロジェクト作成
    2. Gmail API を有効化
    3. OAuth 2.0 クライアント ID を作成（デスクトップアプリ）
    4. credentials.json を config/ ディレクトリに配置
"""

import os
import sys
import json
import re
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.auth.transport.requests

# スコープ
SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.send',
]


def main():
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    credentials_file = config_dir / "credentials.json"
    token_file = config_dir / "oauth_token.json"
    env_file = config_dir / "envs" / ".env.local"
    
    print("=" * 60)
    print("Gmail OAuth2 セットアップ")
    print("=" * 60)
    
    # credentials.json の確認
    if not credentials_file.exists():
        print(f"\nエラー：{credentials_file} が見つかりません。")
        print("\n手順:")
        print("1. https://console.cloud.google.com/ にアクセス")
        print("2. 新しいプロジェクトを作成または選択")
        print("3. Gmail API を有効化")
        print("4. OAuth 同意画面を設定")
        print("5. OAuth 2.0 クライアント ID を作成（デスクトップアプリ）")
        print("6. ダウンロードした JSON ファイルを 'config/credentials.json' として保存")
        return 1
    
    print(f"\n✓ credentials.json を発見：{credentials_file}")
    
    # 既存のトークンファイルを削除（新規取得のため）
    if token_file.exists():
        token_file.unlink()
        print(f"既存のトークンファイルを削除：{token_file}")
    
    # OAuth フローを実行
    print("\nブラウザで認証を行います...")
    print("認証画面で Google アカウントにログインし、アクセスを許可してください。")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_file,
            SCOPES
        )
        
        # ローカルサーバーを使用して認証
        creds = flow.run_local_server(
            port=8080,
            bind_addr="127.0.0.1",
            open_browser=True
        )
        
        if creds is None:
            print("エラー：認証に失敗しました。")
            return 1
        
        # トークンを保存
        token_data = {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"\n✓ トークンを保存：{token_file}")
        
        # 認証情報を表示
        refresh_token = creds.refresh_token
        access_token = creds.token
        client_id = creds.client_id
        client_secret = creds.client_secret
        
        print("\n" + "=" * 60)
        print("以下の値を config/envs/.env.local に設定してください:")
        print("=" * 60)
        print(f"""
# OAuth2 設定
USE_OAUTH=true
OAUTH_CLIENT_ID={client_id}
OAUTH_CLIENT_SECRET={client_secret}
OAUTH_REFRESH_TOKEN={refresh_token}
OAUTH_ACCESS_TOKEN={access_token}
""")
        
        # .env.local の更新
        if env_file.exists():
            print(f"\n{env_file} を更新しますか？")
            response = input("y/n: ")
            if response.lower() == 'y':
                with open(env_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 既存の OAuth 設定を更新
                updates = [
                    ('USE_OAUTH', 'true'),
                    ('OAUTH_CLIENT_ID', client_id),
                    ('OAUTH_CLIENT_SECRET', client_secret),
                    ('OAUTH_REFRESH_TOKEN', refresh_token),
                    ('OAUTH_ACCESS_TOKEN', access_token),
                ]
                
                for key, value in updates:
                    if f'{key}=' in content:
                        # 既存の行を置換
                        content = re.sub(
                            f'{key}=.*',
                            f'{key}={value}',
                            content
                        )
                    else:
                        # 新規追加
                        content += f'\n{key}={value}'
                
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✓ {env_file} を更新しました")
        
        print("\n" + "=" * 60)
        print("セットアップ完了！")
        print("=" * 60)
        print("\n次に、以下のコマンドを実行してください:")
        print("  python scripts/run_prtimes.py")
        
        return 0
        
    except Exception as e:
        print(f"\nエラー：{e}")
        print("\nトラブルシューティング:")
        print("1. credentials.json が正しいことを確認")
        print("2. Gmail API が有効化されていることを確認")
        print("3. OAuth 同意画面が設定されていることを確認")
        return 1


if __name__ == "__main__":
    sys.exit(main())