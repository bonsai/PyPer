# src/main.py

import yaml
import importlib
import sys
import os
import re
from itertools import chain, tee
from typing import List, Dict, Any, Iterator
import concurrent.futures

# Add the 'src' directory to the Python path to allow sibling imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from plugins.base import Entry, SubscriptionPlugin, FilterPlugin, PublishPlugin


def expand_env_variables(value: Any) -> Any:
    """
    Recursively expand environment variables in config values.
    Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax.
    """
    if isinstance(value, str):
        # Match ${VAR_NAME} or ${VAR_NAME:-default}
        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
        
        def replace(match):
            var_name = match.group(1)
            default_value = match.group(2)
            return os.environ.get(var_name, default_value or '')
        
        return re.sub(pattern, replace, value)
    elif isinstance(value, dict):
        return {k: expand_env_variables(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_env_variables(item) for item in value]
    return value


def to_snake_case(name: str) -> str:
    """Converts a CamelCase name to snake_case."""
    name = re.sub('([a-zA-Z0-9])([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

# Module name mapping: YAML name → actual filename
MODULE_NAME_MAP = {
    "prtimes": "prtimes",
    "rss": "rss",
    "google_keep": "google_keep",
    "rss_generator": "rss_generator",
    "llm_vectorize": "llm_vectorize",
    "llm_metadata_enricher": "llm_metadata_enricher",
    "gmail": "gmail",
    "local_smtp": "local_smtp",
    "twitter": "twitter",
    "hatena": "hatena",
    "line_notify": "line_notify",
    "big_query": "big_query",
    # Pop-Mov
    "trend_tracker": "trend_tracker",
    "video_analyzer": "video_analyzer",
    # Imagen
    "kaikai_setup": "kaikai_setup",
    "kaikai_generate": "kaikai_generate",
    "kaikai_gallery": "kaikai_gallery",
    # YUpload
    "pdf_to_video": "pdf_to_video",
    "video_tool": "video_tool",
    "upload": "upload",
    # Yao
    "llm_enricher": "llm_enricher",
}

def load_plugin(plugin_config: Dict[str, Any]):
    """Dynamically loads and instantiates a plugin based on its config."""
    module_str = plugin_config.get("module")
    if not module_str:
        raise ValueError("Plugin config must have a 'module' key.")

    try:
        # Get the parts (e.g., "Subscription::PRTimes" -> ["Subscription", "PRTimes"])
        parts = module_str.split("::")
        if len(parts) < 2:
            raise ValueError(f"Invalid module name format: {module_str}")

        category = parts[0].lower()  # subscription, publish, filter, etc.
        name_part = "::".join(parts[1:])
        # Handle names with multiple '::' like 'LLM::Vectorize'
        module_identifier = "_".join(name_part.split("::"))
        # Convert the identifier to snake_case for the filename
        module_filename = to_snake_case(module_identifier)

        # Apply name mapping if exists
        module_filename = MODULE_NAME_MAP.get(module_filename, module_filename)

        # Build module path: plugins.{category}.{filename}
        # e.g., "Subscription::PRTimes" → plugins.subscription.prtimes
        module_path = f"plugins.{category}.{module_filename}"
        print(f"Loading plugin: '{module_str}' from '{module_path}'")

        plugin_module = importlib.import_module(module_path)
        plugin_class = plugin_module.Plugin

        return plugin_class(plugin_config.get("config", {}))

    except (ValueError, ImportError, AttributeError) as e:
        print(f"FATAL: Error loading plugin '{module_str}'. Module path '{module_path}.py' might be incorrect. Error: {e}")
        raise e

def run_pipeline(config_path: str):
    """Loads config and runs the full data pipeline."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Expand environment variables in config
        config = expand_env_variables(config)
    except (IOError, yaml.YAMLError) as e:
        print(f"Error loading or parsing {config_path}: {e}")
        return

    plugin_configs = config.get("plugins", [])
    if not plugin_configs:
        print("No plugins defined in config. Exiting.")
        return

    # Load and categorize plugins
    subscriptions, filters, publishers = [], [], []
    for conf in plugin_configs:
        instance = load_plugin(conf)
        if isinstance(instance, SubscriptionPlugin): subscriptions.append(instance)
        elif isinstance(instance, FilterPlugin): filters.append(instance)
        elif isinstance(instance, PublishPlugin): publishers.append(instance)

    # --- Execute the Pipeline ---
    print("\n--- Starting Pipeline Execution ---")

    # 1. Chain all subscription plugin iterators
    entry_stream: Iterator[Entry] = chain(*(sub.execute() for sub in subscriptions))

    # 2. Pass the stream through all filter plugins
    for filter_plugin in filters:
        entry_stream = filter_plugin.execute(entry_stream)

    # 3. Send the final stream to all publish plugins
    if not publishers:
        print("No publish plugins. Draining stream to activate pipeline...")
        for _ in entry_stream: pass # Consume the iterator
        return

    # For "increasing workers", we use a ThreadPoolExecutor for publishers
    max_workers = config.get("global", {}).get("max_workers", len(publishers))

    print(f"Executing publishers with {max_workers} workers...")

    if len(publishers) == 1:
        publishers[0].execute(entry_stream)
    else:
        # If multiple publishers, tee the stream so each gets all entries
        publisher_streams = tee(entry_stream, len(publishers))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i, publisher in enumerate(publishers):
                print(f"Scheduling publisher {i+1}/{len(publishers)} ({publisher.name})")
                futures.append(executor.submit(publisher.execute, publisher_streams[i]))

            # Wait for all to complete
            concurrent.futures.wait(futures)

    print("--- Pipeline Execution Finished ---")

def main():
    # Assume rag.yaml is in the parent directory of 'src'
    # Try rag.yaml first, then fall back to rag.yaml.example for demonstration
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    config_path = os.path.join(root_dir, 'rag.yaml')
    if not os.path.exists(config_path):
        config_path = os.path.join(root_dir, 'rag.yaml.example')
        print(f"Warning: rag.yaml not found. Using {config_path} as fallback.")

    run_pipeline(config_path)

if __name__ == "__main__":
    main()
