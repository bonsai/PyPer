# Qwen Code Offline Setup Guide

## How it works

When cloud API is unreachable, `yao offline` starts local llama-server and serves an OpenAI-compatible API on port 8081.

## Quick Start

```bash
# Check if offline mode works
yao offline
```

## Configure Qwen Code for Offline

### Option 1: Manual toggle in settings.json

When going offline, edit `~/.qwen/settings.json`:

```json
{
  "model": {
    "name": "coder-model"
  },
  "customProviders": {
    "local": {
      "baseUrl": "http://127.0.0.1:8081/v1",
      "apiKey": "local",
      "models": ["qwen3-8b"]
    }
  }
}
```

### Option 2: Use the setup script

```bash
# Set offline mode (points Qwen Code to local)
yao setup-offline

# Restore cloud mode
yao setup-online
```

## Env Vars

| Variable | Default | Description |
|----------|---------|-------------|
| `YAO_THREADS` | 8 | CPU threads |
| `YAO_CTX` | 4096 | Context size |
| `YAO_QWEN_API_KEY` | "" | Cloud API key (optional fallback) |
| `YAO_QWEN_MODEL` | qwen-plus | Cloud model name |
