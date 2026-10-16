"""Run Caddy and the API together; Ctrl+C stops only this launch's children."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
import uuid

ROOT = Path(__file__).resolve().parent
HTTP = build_opener(ProxyHandler({}))  # Local health checks never use a system proxy.


def domain_name(value):
    if len(value) > 253 or not re.fullmatch(
            r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
            r"[a-zA-Z]{2,63}", value):
        raise argparse.ArgumentTypeError("Use a domain such as app.example.com, without a scheme, port or path.")
    return value.lower()


def port_number(value):
    port = int(value)
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("Choose a port between 1024 and 65535.")
    return port


def configuration(port, api_port, domain=None):
    address = domain or f"http://127.0.0.1:{port}"
    bind = "" if domain else "bind 127.0.0.1"
    return f'''{{
    admin off
    persist_config off
}}
{address} {{
    {bind}
    encode gzip
    header X-Content-Type-Options nosniff
    @api path /api /api/*
    handle @api {{
        request_body {{
            max_size 16KB
        }}
        reverse_proxy 127.0.0.1:{api_port}
    }}
    handle {{
        root * "{(ROOT / 'public').as_posix()}"
        file_server
    }}
}}
'''


def ensure_free(port):
    with socket.socket() as sock:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"Port {port} is already in use. Choose another port; no process was stopped.") from exc


def wait_ready(url, instance, children, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            raise RuntimeError("A server exited during startup. See .runtime logs.")
        try:
            with HTTP.open(url, timeout=1) as response:
                data = json.load(response)
            if data.get("instance") == instance and data.get("status") == "ok":
                return
        except (URLError, OSError, ValueError):
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Server did not become ready: {url}. See .runtime logs.")


def stop(children):
    for child in reversed(children):
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=port_number, default=8080)
    parser.add_argument("--api-port", type=port_number, default=8001)
    parser.add_argument("--domain", type=domain_name, help="Explicitly publish this demo with automatic HTTPS")
    parser.add_argument("--check", action="store_true", help="Validate config and imports without starting servers")
    parser.add_argument("--smoke", action="store_true", help="Start locally, check health, then stop")
    args = parser.parse_args()
    if args.port == args.api_port:
        parser.error("Web and API ports must differ.")
    if args.smoke and args.domain:
        parser.error("--smoke is local-only.")
    binary = ROOT / "bin" / "caddy.exe"
    if not binary.exists():
        raise RuntimeError("Caddy is missing. Run setup.ps1 first.")
    import app  # Fail early if the environment is incomplete.
    import uvicorn
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    instance = uuid.uuid4().hex
    env = {**os.environ, "STARTER_INSTANCE": instance,
           "XDG_DATA_HOME": str(runtime / "data"), "XDG_CONFIG_HOME": str(runtime / "config")}
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with tempfile.TemporaryDirectory(prefix="run-", dir=runtime) as folder:
        config = Path(folder) / "Caddyfile"
        config.write_text(configuration(args.port, args.api_port, args.domain), encoding="utf-8")
        subprocess.run([str(binary), "validate", "--config", str(config), "--adapter", "caddyfile"],
                       env=env, check=True, creationflags=flags)
        if args.check:
            print("Configuration and Python imports OK.")
            return
        for port in ([80, 443] if args.domain else [args.port]) + [args.api_port]:
            ensure_free(port)
        children = []
        try:
            with (runtime / f"api-{instance}.log").open("w", encoding="utf-8") as api_log, \
                    (runtime / f"caddy-{instance}.log").open("w", encoding="utf-8") as caddy_log:
                children.append(subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1",
                     "--port", str(args.api_port), "--no-proxy-headers"],
                    cwd=ROOT, env=env, stdout=api_log, stderr=subprocess.STDOUT, creationflags=flags))
                wait_ready(f"http://127.0.0.1:{args.api_port}/api/health", instance, children)
                children.append(subprocess.Popen(
                    [str(binary), "run", "--config", str(config), "--adapter", "caddyfile"],
                    cwd=ROOT, env=env, stdout=caddy_log, stderr=subprocess.STDOUT, creationflags=flags))
                url = f"https://{args.domain}" if args.domain else f"http://127.0.0.1:{args.port}"
                if not args.domain:
                    wait_ready(url + "/api/health", instance, children)
                print(f"Open {url} | Ctrl+C to stop | Logs: {runtime}", flush=True)
                if args.domain:
                    print("Public startup requested. Verify DNS, firewall and certificate issuance in Caddy logs.", flush=True)
                if args.smoke:
                    print("SMOKE OK: request passed through Caddy to FastAPI.")
                    return
                while all(child.poll() is None for child in children):
                    time.sleep(0.5)
                raise RuntimeError("A server stopped unexpectedly. See .runtime logs.")
        finally:
            stop(children)


def interrupted(signum, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
    except (OSError, RuntimeError, subprocess.SubprocessError, ImportError) as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        sys.exit(1)
