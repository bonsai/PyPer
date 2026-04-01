#!/usr/bin/env python3
"""
PR Times プレスリリース→Gmail 送信スクリプト

使用方法:
    python scripts/run_prtimes.py

設定:
    1. config/envs/.env.local を作成し、GMAIL_USERNAME と GMAIL_PASSWORD を設定
    2. 必要に応じて prt.yaml を編集
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from main import run_pipeline
import logging

logger = logging.getLogger(__name__)


def run_prtimes_flow(config_path: str = None):
    """PR Times フローを実行"""

    # 設定ファイルのパス
    if config_path is None:
        config_path = project_root / "recipe" / "prt.yaml"

    print(f"PR Times フローを開始します...")
    print(f"設定ファイル：{config_path}")

    try:
        # パイプライン実行
        run_pipeline(str(config_path))
        return 0

    except Exception as e:
        logger.error(f"エラー：{e}")
        print(f"\nエラーが発生しました：{e}")
        return 1


if __name__ == "__main__":
    # 環境変数ファイルを読み込む
    from dotenv import load_dotenv
    env_file = project_root / "config" / "envs" / ".env.local"
    if env_file.exists():
        load_dotenv(env_file)
        print(f".env.local を読み込みました：{env_file}")
    else:
        print(f"警告：.env.local が見つかりません：{env_file}")

    sys.exit(run_prtimes_flow())
