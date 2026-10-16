"""Install this project's environment and a checksum-verified Caddy binary."""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen
import venv
import zipfile

ROOT = Path(__file__).resolve().parent
CADDY_VERSION = "2.11.7"


def execute(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def fetch(url):
    request = Request(url, headers={"User-Agent": "GeoKrown-Web-Interface-Starter"})
    with urlopen(request, timeout=120) as response:
        return response.read()


def verify_archive(data, checksums, name):
    matches = [line.split()[0].lower() for line in checksums.splitlines()
               if len(line.split()) == 2 and line.split()[1].lstrip("*") == name]
    if len(matches) != 1 or hashlib.sha512(data).hexdigest() != matches[0]:
        raise ValueError("Caddy SHA512 verification failed. Nothing extracted.")


def install_caddy():
    directory = ROOT / "bin"
    binary = directory / "caddy.exe"
    receipt = directory / "caddy.sha256"
    if binary.exists() and receipt.exists():
        expected = receipt.read_text(encoding="ascii").strip()
        if hashlib.sha256(binary.read_bytes()).hexdigest() == expected:
            execute(binary, "version")
            return
    name = f"caddy_{CADDY_VERSION}_windows_amd64.zip"
    base = f"https://github.com/caddyserver/caddy/releases/download/v{CADDY_VERSION}/"
    print(f"Downloading Caddy {CADDY_VERSION} from the official release", flush=True)
    checksums = fetch(base + f"caddy_{CADDY_VERSION}_checksums.txt").decode("utf-8")
    data = fetch(base + name)
    verify_archive(data, checksums, name)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        executable = archive.read("caddy.exe")
    directory.mkdir(exist_ok=True)
    # Extract only the named executable, never arbitrary archive paths.
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False) as out:
        temporary = Path(out.name)
        out.write(executable)
    try:
        os.replace(temporary, binary)
        receipt.write_text(hashlib.sha256(executable).hexdigest(), encoding="ascii")
    finally:
        temporary.unlink(missing_ok=True)
    execute(binary, "version")


def main():
    if (sys.platform != "win32" or struct.calcsize("P") != 8
            or platform.machine().lower() not in {"amd64", "x86_64"}):
        raise RuntimeError("This starter targets Windows x64.")
    if sys.version_info < (3, 12):
        raise RuntimeError("Python 3.12 or later is required.")
    target = ROOT / ".venv"
    marker = target / "web-starter.json"
    expected = {"owner": "web-interface-starter", "python": list(sys.version_info[:2])}
    if target.exists():
        if not marker.exists() or json.loads(marker.read_text()) != expected:
            raise RuntimeError("Existing .venv is not owned by this setup or uses another Python. Use a new folder.")
    else:
        venv.EnvBuilder(with_pip=True).create(target)
        marker.write_text(json.dumps(expected), encoding="utf-8")
    python = target / "Scripts" / "python.exe"
    execute(python, "-m", "pip", "install", "--only-binary=:all:", "--timeout", "60",
            "--retries", "2", "-r", ROOT / "requirements.txt")
    execute(python, "-m", "pip", "check")
    install_caddy()
    execute(python, ROOT / "run.py", "--check")
    print("Ready. Start with: .\\.venv\\Scripts\\python.exe run.py")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        sys.exit(1)
