#!/usr/bin/env python3
"""
PyPer Plagger Runner - Execute Plagger pipelines via PyPer
Usage: python plagger_runner.py recipe/plagger.yaml
"""

import sys
import os
import yaml
import logging
from typing import Iterator
from datetime import datetime

# Add PyPer src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from plugins.base import Entry, SubscriptionPlugin, FilterPlugin, PublishPlugin

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load pipeline configuration."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def resolve_env_vars(config: dict) -> dict:
    """Replace ${VAR} with environment variables."""
    import re
    config_str = yaml.dump(config)
    pattern = r'\$\{(\w+)\}'
    
    def replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    
    resolved = re.sub(pattern, replacer, config_str)
    return yaml.safe_load(resolved)


def load_plugin(module_path: str, config: dict):
    """Dynamically load plugin module."""
    import importlib
    
    # Convert module path to import path
    # e.g., "subscription.rss.Plugin" -> plugins.subscription.rss.Plugin
    full_module = f"plugins.{module_path.rsplit('.', 1)[0]}"
    class_name = module_path.rsplit('.', 1)[1]
    
    mod = importlib.import_module(full_module)
    plugin_class = getattr(mod, 'Plugin')
    return plugin_class(config)


def run_pipeline(config_path: str):
    """Execute the full pipeline: Subscription → Filter → Publish"""
    
    logger.info(f"🚀 Loading pipeline config: {config_path}")
    config = load_config(config_path)
    config = resolve_env_vars(config)
    
    pipeline = config['pipeline']
    logger.info(f"📋 Pipeline: {pipeline['name']}")
    
    # ── Step 1: Subscription ──
    logger.info("📥 Step 1: Subscription")
    entries = []
    for sub_config in pipeline['subscription']:
        if sub_config.get('config', {}).get('enabled', True) is False:
            continue
        
        plugin = load_plugin(sub_config['module'], sub_config['config'])
        logger.info(f"  → {plugin.name}")
        
        for entry in plugin.execute():
            entries.append(entry)
    
    logger.info(f"  ✅ {len(entries)} entries fetched")
    
    if not entries:
        logger.warning("⚠️ No entries. Skipping pipeline.")
        return
    
    # ── Step 2: Filters ──
    logger.info("🔄 Step 2: Filters")
    entry_iter = iter(entries)
    
    for filter_config in pipeline.get('filters', []):
        if filter_config.get('config', {}).get('enabled', True) is False:
            continue
        
        plugin = load_plugin(filter_config['module'], filter_config['config'])
        logger.info(f"  → {plugin.name}")
        entry_iter = plugin.execute(entry_iter)
        entries = list(entry_iter)
        entry_iter = iter(entries)
    
    logger.info(f"  ✅ {len(entries)} entries after filtering")
    
    # ── Step 3: Publish ──
    logger.info("📤 Step 3: Publish")
    for pub_config in pipeline['publish']:
        if pub_config.get('config', {}).get('enabled', True) is False:
            continue
        
        plugin = load_plugin(pub_config['module'], pub_config['config'])
        logger.info(f"  → {plugin.name}")
        plugin.execute(iter(entries))
    
    logger.info("✅ Pipeline complete!")


def run_plagger_compat(config_path: str):
    """Execute legacy Plagger via subprocess (compatibility mode)."""
    import subprocess
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    compat = config.get('plagger_compat', {})
    if not compat.get('enabled'):
        return
    
    plagger_path = compat['plagger_path']
    perl_cmd = compat.get('perl_cmd', 'perl')
    
    logger.info("🔧 Running legacy Plagger plugins...")
    
    for plugin in compat.get('plugins', []):
        if not plugin.get('config', {}).get('enabled', False):
            continue
        
        logger.info(f"  → {plugin['module']}")
        # Create temporary YAML for Plagger
        # This is a simplified example
        logger.warning(f"  ⚠️ Plagger compat for {plugin['module']} not fully implemented yet")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python plagger_runner.py <config.yaml>")
        print("Example: python plagger_runner.py recipe/plagger.yaml")
        sys.exit(1)
    
    config_file = sys.argv[1]
    if not os.path.exists(config_file):
        logger.error(f"Config file not found: {config_file}")
        sys.exit(1)
    
    run_pipeline(config_file)
    run_plagger_compat(config_file)
