#!/usr/bin/env python3
"""
yao offline - Qwen Code offline gateway
When cloud is unreachable, auto-starts local model and serves OpenAI-compatible API.
"""
import os
import sys
import json
import time
import socket
import subprocess
import threading
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ---- Config ----
HOME = Path.home()
LLAMA_BIN = HOME / "llama.cpp" / "build" / "bin"
MODELS_DIR = HOME / "models"
HOST = "127.0.0.1"
LOCAL_PORT = 8081
GATEWAY_PORT = int(os.environ.get("YAO_GATEWAY_PORT", "8088"))

# Cloud check targets
CLOUD_HOSTS = [
    ("dashscope.aliyuncs.com", 443),
    ("api.openai.com", 443),
]
CLOUD_TIMEOUT = 3

# Model paths
MODEL_PATHS = [
    MODELS_DIR / "llm" / "qwen3-8b",
]

THREADS = int(os.environ.get("YAO_THREADS", "8"))
CTX = int(os.environ.get("YAO_CTX", "4096"))

server_proc = None
local_port = LOCAL_PORT


class C:
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"

def cyan(s):  return f"{C.CYAN}{s}{C.RESET}"
def green(s): return f"{C.GREEN}{s}{C.RESET}"
def yellow(s):return f"{C.YELLOW}{s}{C.RESET}"
def red(s):   return f"{C.RED}{s}{C.RESET}"

def check_cloud():
    """Check if cloud API is reachable."""
    for host, port in CLOUD_HOSTS:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(CLOUD_TIMEOUT)
            s.connect((host, port))
            s.close()
            return True
        except:
            continue
    return False

def find_model():
    """Find local GGUF model."""
    for d in MODEL_PATHS:
        if not d.is_dir():
            continue
        for f in d.glob("*.gguf"):
            if not f.name.startswith("mmproj"):
                return str(f)
    return None

def start_local(model_path, port):
    """Start llama-server in background."""
    global server_proc
    server_path = LLAMA_BIN / "llama-server"
    if not server_path.exists():
        print(red(f"llama-server not found at {server_path}"))
        return False

    print(cyan(f"Starting local model: {model_path}"))
    print(cyan(f"Port: {port}"))

    server_proc = subprocess.Popen([
        str(server_path),
        "-m", model_path,
        "--threads", str(THREADS),
        "--ctx-size", str(CTX),
        "--n-gpu-layers", "0",
        "--flash-attn", "on",
        "--jinja",
        "--port", str(port),
        "--host", HOST,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for ready
    for i in range(30):
        time.sleep(1)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((HOST, port))
            s.close()
            print(green(f"Local model ready on port {port} ({i+1}s)"))
            return True
        except:
            print(".", end="", flush=True)
    print()
    return False

def stop_local():
    """Stop local server."""
    global server_proc
    if server_proc:
        server_proc.kill()
        server_proc = None
        print(green("Local model stopped"))


class ProxyHandler(BaseHTTPRequestHandler):
    """Proxy requests to local llama-server."""

    def do_POST(self):
        self._proxy("POST")

    def do_GET(self):
        self._proxy("GET")

    def _proxy(self, method):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else None

        # Forward to local llama-server
        url = f"http://{HOST}:{local_port}{self.path}"
        cmd = ["curl", "-sf", url]

        if method == "POST":
            cmd += ["-X", "POST", "-H", "Content-Type: application/json", "-d", body.decode() if body else "{}"]

        try:
            r = subprocess.run(cmd, capture_output=True, timeout=120)
            if r.returncode == 0:
                resp_data = r.stdout
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(resp_data)
            else:
                self.send_response(502)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(r.stderr)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, format, *args):
        pass  # Silence access logs


def main():
    global local_port

    print(cyan("=" * 50))
    print(cyan("yao offline - Qwen Code gateway"))
    print(cyan("=" * 50))
    print()

    # Check cloud
    print("Checking cloud connectivity...")
    if check_cloud():
        print(green("Cloud API reachable. No local fallback needed."))
        print("Exiting — Qwen Code can use cloud directly.")
        return

    print(red("Cloud API unreachable."))
    print()

    # Find and start local model
    model = find_model()
    if not model:
        print(red("No local model found. Cannot start offline mode."))
        sys.exit(1)

    print(yellow(f"Offline mode: starting local model..."))
    print()

    if not start_local(model, local_port):
        print(red("Failed to start local model."))
        sys.exit(1)

    print()
    print(green("Local model running."))
    print()
    print(cyan(f"OpenAI-compatible API: http://{HOST}:{local_port}/v1"))
    print(f"  POST /v1/chat/completions")
    print(f"  GET  /v1/models")
    print()
    print(yellow("To use with Qwen Code, configure an OpenAI-compatible provider:"))
    print(f"  settings.json -> model: add custom provider pointing to http://{HOST}:{local_port}/v1")
    print()
    print(cyan("Press Ctrl+C to stop"))
    print()

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        print(green("Stopping..."))
        stop_local()


if __name__ == "__main__":
    main()
