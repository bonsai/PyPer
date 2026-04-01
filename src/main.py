#!/usr/bin/env python3
""" RSS パイプライン - メインエントリーポイント 思想：YAML にフローを書く、環境変数にシークレットを書く、Python のみで動く """
import os
import sys
import json
import yaml
import logging
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Iterator
from datetime import datetime
from dotenv import load_dotenv

# src ディレクトリを Python パスに追加
SRC_DIR = Path(__file__).parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# ロギング設定
def setup_logging(log_level: str = "INFO", log_file: str = None):
    """ロギング設定"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers = [logging.StreamHandler()]
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )


class ConfigManager:
    """設定管理"""
    def __init__(self, config_path: str = None):
        self.config_path = config_path or self._find_config_file()
        self.config = self._load_config()
        self.env_vars = self._load_env_vars()

    def _find_config_file(self) -> str:
        """設定ファイルを検索"""
        candidates = [
            "config/flows/main_flow.yaml",
            "flows/main_flow.yaml",
            "main_flow.yaml",
            "recipe/main_config.yaml",
            "recipe/prtimes_config.yaml",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
        raise FileNotFoundError("設定ファイルが見つかりません")

    def _load_config(self) -> Dict[str, Any]:
        """YAML 設定ファイルを読み込む"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"設定ファイル読み込みエラー：{e}")

    def _load_env_vars(self) -> Dict[str, str]:
        """環境変数を読み込む"""
        env_files = [
            ".env.local",
            "config/envs/.env.local",
            ".env",
            "config/envs/.env"
        ]
        for env_file in env_files:
            if Path(env_file).exists():
                load_dotenv(env_file)
                break
        return dict(os.environ)

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        if key in self.env_vars:
            return self.env_vars[key]
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def interpolate(self, value: str) -> str:
        """変数展開"""
        import re
        def replace_var(match):
            var_name = match.group(1)
            return self.get(var_name, match.group(0))
        return re.sub(r'\$\{([^}]+)\}', replace_var, value)


class PluginManager:
    """プラグインマネージャー"""
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.plugins = {}
        self.logger = logging.getLogger(__name__)
        self.src_path = Path(__file__).parent

    def _module_to_path(self, module_name: str) -> Path:
        """
        モジュール名をファイルパスに変換
        例：Subscription::PRTimes -> subscription_prtimes.py
        例：Publish::Gmail -> publish_gmail.py
        """
        if "::" in module_name:
            parts = module_name.split("::")
            category = parts[0].lower()  # subscription, publish, filter, etc.
            name = parts[1].lower()      # prtimes, gmail, etc.
            return self.src_path / "plugins" / f"{category}_{name}.py"
        else:
            # 旧形式：Subscription::RSS -> rss.py
            name = module_name.split("::")[-1].lower()
            return self.src_path / "plugins" / f"{name}.py"

    def load_plugin(self, module_name: str) -> Any:
        """プラグインを読み込む"""
        if module_name in self.plugins:
            return self.plugins[module_name]

        plugin_file = self._module_to_path(module_name)

        if not plugin_file.exists():
            raise ImportError(f"プラグインファイルが見つかりません：{plugin_file}")

        try:
            # プラグインディレクトリを sys.path に追加（spec 作成前に必要）
            plugins_dir = str(plugin_file.parent)
            path_added = False
            if plugins_dir not in sys.path:
                sys.path.insert(0, plugins_dir)
                path_added = True
            
            try:
                # 動的インポート
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Plugin クラスを取得
                plugin_class = getattr(module, "Plugin")

                # インスタンスを作成
                instance = plugin_class(config=self.config.config)
                self.plugins[module_name] = instance
                self.logger.info(f"プラグイン読み込み完了：{module_name}")
                return instance
            finally:
                # 追加したパスを元に戻す（オプション）
                if path_added and plugins_dir in sys.path:
                    sys.path.remove(plugins_dir)

        except Exception as e:
            raise RuntimeError(f"プラグイン読み込みエラー {module_name}: {e}")

    def execute_plugin(self, module_name: str, step_config: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """プラグインを実行"""
        plugin = self.load_plugin(module_name)
        
        # 設定を展開
        config = {}
        for key, value in step_config.get('config', {}).items():
            if isinstance(value, str):
                config[key] = self.config.interpolate(value)
            else:
                config[key] = value
        
        # プラグインタイプに応じて実行方法を変更
        plugin_type = module_name.split("::")[0].lower() if "::" in module_name else ""
        
        if plugin_type == "subscription":
            # Subscription プラグイン：entries を生成
            return list(plugin.execute())
        elif plugin_type == "publish":
            # Publish プラグイン：entries を受け取る
            entries = context.get("entries", [])
            plugin.execute(iter(entries))
            return {"published": len(entries)}
        elif plugin_type == "filter" or plugin_type == "processor":
            # Filter/Processor プラグイン：entries を変換
            entries = context.get("entries", [])
            result = list(plugin.execute(iter(entries)))
            context["entries"] = result
            return {"processed": len(result)}
        else:
            # デフォルト：execute メソッドを呼び出す
            return plugin.execute(config=config, context=context)


class PipelineRunner:
    """パイプライン実行機"""
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.plugins = PluginManager(config_manager)
        self.logger = logging.getLogger(__name__)

    def run_flow(self, flow_name: str = "plugins") -> Dict[str, Any]:
        """フローを実行"""
        self.logger.info(f"フロー実行開始：{flow_name}")
        
        # 設定構造をチェック
        if "plugins" in self.config.config:
            # プラグインリスト形式（prtimes_config.yaml など）
            plugin_list = self.config.config.get("plugins", [])
        else:
            # 従来形式
            plugin_list = self.config.config.get(flow_name, [])
        
        if not plugin_list:
            raise RuntimeError(f"フロー設定が見つかりません：{flow_name}")
        
        # 実行コンテキスト
        context = {
            'flow_name': flow_name,
            'start_time': datetime.now(),
            'results': {},
            'entries': []
        }
        
        # ステップを実行
        results = []
        for step in plugin_list:
            module_name = step.get('module')
            step_name = module_name.split("::")[-1] if "::" in module_name else module_name
            
            self.logger.info(f"ステップ実行：{step_name} ({module_name})")
            
            try:
                # プラグイン実行
                result = self.plugins.execute_plugin(module_name, step, context)
                
                # 結果を保存
                context['results'][step_name] = result
                results.append({
                    'step': step_name,
                    'module': module_name,
                    'status': 'success',
                    'result': result
                })
                
                # Subscription プラグインの場合は entries を保存
                if module_name.split("::")[0].lower() == "subscription":
                    context['entries'] = result
                
                self.logger.info(f"ステップ完了：{step_name}")
                
            except Exception as e:
                self.logger.error(f"ステップエラー {step_name}: {e}")
                error_config = self.config.config.get('error_handling', {})
                if error_config.get('fallback_action') == 'log_only':
                    results.append({
                        'step': step_name,
                        'module': module_name,
                        'status': 'error',
                        'error': str(e)
                    })
                    continue
                else:
                    raise
        
        # 最終結果
        final_result = {
            'flow_name': flow_name,
            'status': 'success',
            'start_time': context['start_time'].isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration': (datetime.now() - context['start_time']).total_seconds(),
            'steps': results,
            'total_steps': len(results),
            'successful_steps': len([r for r in results if r['status'] == 'success'])
        }
        
        self.logger.info(f"フロー実行完了：{flow_name} ({len(results)}ステップ)")
        return final_result


def main():
    """メイン関数"""
    try:
        config = ConfigManager()
        log_level = config.get("global.log_level", "INFO")
        log_file = config.get("global.log_file")
        setup_logging(log_level, log_file)
        logger = logging.getLogger(__name__)
        logger.info("PyPer パイプライン 開始")
        runner = PipelineRunner(config)
        result = runner.run_flow("plugins")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        logger.info("PyPer パイプライン 完了")
        return 0
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"パイプラインエラー：{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
