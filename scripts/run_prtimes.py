#!/usr/bin/env python3
"""
PR Times プレスリリース→Gmail 送信スクリプト

使用方法:
    python scripts/run_prtimes.py

設定:
    1. config/envs/.env.local を作成し、GMAIL_USERNAME と GMAIL_PASSWORD を設定
    2. 必要に応じて recipe/prtimes_config.yaml を編集
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from main import ConfigManager, PipelineRunner, setup_logging
import logging

logger = logging.getLogger(__name__)


def run_prtimes_flow(config_path: str = None):
    """PR Times フローを実行"""
    
    # 設定ファイルのパス
    if config_path is None:
        config_path = project_root / "recipe" / "prtimes_config.yaml"
    
    print(f"PR Times フローを開始します...")
    print(f"設定ファイル：{config_path}")
    
    try:
        # 設定管理
        config = ConfigManager(str(config_path))
        
        # ロギング設定
        log_level = config.get("global.log_level", "INFO")
        setup_logging(log_level)
        
        # パイプライン実行
        runner = PipelineRunner(config)
        result = runner.run_flow("plugins")
        
        # 結果表示
        print("\n===== 実行結果 =====")
        print(f"ステータス：{result['status']}")
        print(f"ステップ数：{result['total_steps']}")
        print(f"成功ステップ：{result['successful_steps']}")
        print(f"処理時間：{result['duration']:.2f}秒")
        
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
        print("config/envs/.env.example をコピーして設定してください")
    
    sys.exit(run_prtimes_flow())
