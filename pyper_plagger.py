#!/usr/bin/env python3
"""
PyPer Plagger Runner - Plagger pipeline executor
Usage: python pyper_plagger.py recipe/plagger.yaml
"""

import sys
import os
import yaml
import logging
import importlib
from typing import Iterator, List
from datetime import datetime

# Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add PyPer src to path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
sys.path.insert(0, SRC_DIR)

# Direct import to avoid circular import
import importlib
base_mod = importlib.import_module('plugins.base')
Entry = base_mod.Entry
SubscriptionPlugin = base_mod.SubscriptionPlugin
FilterPlugin = base_mod.FilterPlugin
PublishPlugin = base_mod.PublishPlugin


def load_config(config_path: str) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def resolve_env_vars(text: str) -> str:
    """Replace ${VAR} with environment variables"""
    import re
    def replacer(match):
        return os.environ.get(match.group(1), match.group(0))
    return re.sub(r'\$\{(\w+)\}', replacer, text)


def load_plugin(module_path: str, config: dict):
    """
    Load plugin dynamically.
    module_path: "subscription.rss.Plugin" or "publish.nhk_gmail.Plugin"
    """
    module_name = module_path.rsplit('.', 1)[0]
    class_name = module_path.rsplit('.', 1)[1]
    
    full_module = f"plugins.{module_name}"
    mod = importlib.import_module(full_module)
    plugin_class = getattr(mod, class_name)
    return plugin_class(config)


def run_pipeline(config_path: str):
    """Execute: Subscription → Filter → Publish"""
    
    config_file = os.path.abspath(config_path)
    config_text = open(config_file, encoding='utf-8').read()
    config_text = resolve_env_vars(config_text)
    config = yaml.safe_load(config_text)
    
    pipeline = config['pipeline']
    logger.info(f"🚀 Pipeline: {pipeline['name']}")
    
    entries: List[Entry] = []
    
    # ── 1. Subscription ──
    logger.info("📥 [1/3] Subscription")
    for sub_cfg in pipeline.get('subscription', []):
        if not sub_cfg.get('config', {}).get('enabled', True):
            continue
        
        plugin = load_plugin(sub_cfg['module'], sub_cfg['config'])
        logger.info(f"  → {plugin.name if hasattr(plugin, 'name') else sub_cfg['module']}")
        
        count = 0
        for entry in plugin.execute():
            entries.append(entry)
            count += 1
        logger.info(f"    ✅ {count} entries")
    
    if not entries:
        logger.warning("⚠️ No entries. Pipeline stopped.")
        return
    
    # ── 2. Filters ──
    logger.info("🔄 [2/3] Filters")
    entry_iter = iter(entries)
    
    for filter_cfg in pipeline.get('filters', []):
        if not filter_cfg.get('config', {}).get('enabled', True):
            continue
        
        plugin = load_plugin(filter_cfg['module'], filter_cfg['config'])
        logger.info(f"  → {plugin.name if hasattr(plugin, 'name') else filter_cfg['module']}")
        entry_iter = plugin.execute(entry_iter)
        entries = list(entry_iter)
        entry_iter = iter(entries)
    
    logger.info(f"  ✅ {len(entries)} entries after filters")
    
    # ── 3. Publish ──
    logger.info("📤 [3/3] Publish")
    for pub_cfg in pipeline.get('publish', []):
        if not pub_cfg.get('config', {}).get('enabled', True):
            continue
        
        plugin = load_plugin(pub_cfg['module'], pub_cfg['config'])
        logger.info(f"  → {plugin.name if hasattr(plugin, 'name') else pub_cfg['module']}")
        plugin.execute(iter(entries))
    
    logger.info("✅ Pipeline complete!")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python pyper_plagger.py <config.yaml>")
        print("Example: python pyper_plagger.py recipe/plagger.yaml")
        sys.exit(1)
    
    config_file = sys.argv[1]
    if not os.path.exists(config_file):
        logger.error(f"Config not found: {config_file}")
        sys.exit(1)
    
    run_pipeline(config_file)
