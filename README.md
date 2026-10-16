# Web Interface Starter

A small Windows-first starter for a web interface: **Caddy + FastAPI + plain HTML, CSS and JavaScript**. No Docker, Node.js or database required.

Start locally, edit the demo, and optionally connect a domain later. The included Launchpad interface demonstrates live API status, sample projects and a stateless form. It is a starting point, not a production application with authentication.

## Quick start on Windows

Use a supported Windows x64 system and Windows PowerShell 5.1 or newer. Internet access is required. Start in a regular PowerShell window; managed servers may require administrator assistance for Python installation.

Download into a **new folder** on your Desktop:

```powershell
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$destination = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Web-Interface-Starter'
if (Test-Path -LiteralPath $destination) { throw "Folder already exists: $destination. Use it or choose a new destination." }
$archive = Join-Path $env:TEMP ('web-starter-' + [guid]::NewGuid().ToString('N') + '.zip')
$unpack = Join-Path $env:TEMP ('web-starter-' + [guid]::NewGuid().ToString('N'))
try {
    Invoke-WebRequest 'https://github.com/GeoKrown/web-interface-starter/archive/refs/heads/main.zip' -OutFile $archive -UseBasicParsing -TimeoutSec 120
    Expand-Archive -LiteralPath $archive -DestinationPath $unpack
    Move-Item -LiteralPath (Join-Path $unpack 'web-interface-starter-main') -Destination $destination
} finally {
    if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive }
    if ((Test-Path -LiteralPath $unpack) -and -not (Get-ChildItem -LiteralPath $unpack -Force)) { Remove-Item -LiteralPath $unpack }
}
Set-Location -LiteralPath $destination
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
```

The setup selects the newest stable Python x64 **EXE installer listed on python.org**, verifies its Windows signature, installs it per user if needed, creates `.venv`, installs the two direct Python dependencies, and downloads checksum-verified Caddy **2.11.7**. The shared Python installation lives under `%LOCALAPPDATA%\PythonServerStarter`; the project environment and Caddy remain inside this folder. It does not open firewall ports or install a Windows service.

Then start:

```powershell
.\.venv\Scripts\python.exe run.py
```

Open **http://127.0.0.1:8080** on the same computer. If you are connected by Remote Desktop, open the browser on the server. Press **Ctrl+C** to stop both servers before closing the terminal. Force-closing the terminal is not a supported shutdown method. This foreground launcher is for development and initial setup; it does not keep a site running after logout/reboot.

## Installation options

```powershell
# Show the selected download without installing anything
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -Plan

# Use an existing Python 3.12+ x64 installation
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -PythonPath 'C:\Path\To\python.exe'

# Select a specific stable release still listed on the Windows downloads page
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -PythonVersion 3.12.10

# Use different local ports
.\.venv\Scripts\python.exe run.py --port 8085 --api-port 8005
```

Dependency ranges allow compatible releases; this is not a frozen lockfile. Setup requires binary wheels and stops rather than installing compilers. Very new Python versions may not yet have dependency wheels: use an older supported Python with `-PythonPath` in a fresh project folder. Existing environments created by another tool or another Python minor version are not overwritten. Re-running setup does not start the site.

## What to edit

| File | Purpose |
| --- | --- |
| `public/index.html` | Page structure |
| `public/style.css` | Responsive styling |
| `public/app.js` | Browser behavior and API requests |
| `app.py` | FastAPI endpoints |
| `requirements.txt` | Python dependencies |
| `run.py` | Caddy configuration and foreground process supervision |
| `bootstrap.py` | Environment and Caddy installation |
| `setup.ps1` | Python installer entry point |

Caddy serves **only `public/`**. Never place secrets there. Requests under `/api` are forwarded unchanged to FastAPI on loopback; API documentation is at `/api/docs`. The example has no database and saves nothing. Replace demo data and add authentication before exposing private features.

## Optional public HTTPS

First confirm the local demo works. Point a domain's DNS A record to the server's public IPv4 address. Only publish an AAAA record if IPv6 actually reaches this server. Allow inbound TCP 80 and 443 through the host firewall, provider firewall and router/NAT where applicable. Keep the API port private.

```powershell
.\.venv\Scripts\python.exe run.py --domain app.example.com
```

Replace the example domain with yours. This command exposes the demo to the public internet. Caddy requests and renews certificates automatically when domain validation succeeds. Startup does not prove public reachability: check the HTTPS URL from another network and inspect `.runtime/caddy-*.log`. Certificates and state live under `.runtime/data`; preserve this folder between launches. Do not repeatedly erase it while debugging certificate issuance.

For continuous hosting, configure a Windows service with recovery and controlled shutdown using the [official Caddy guidance](https://caddyserver.com/docs/running#windows-service). This starter does not automate service registration, deployment, backups or application authentication.

## Verify

Run from the project folder after setup:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe run.py --check
.\.venv\Scripts\python.exe run.py --smoke
.\.venv\Scripts\python.exe -m unittest -v
```

Tests check archive integrity failures, input validation, occupied ports, real Caddy-to-FastAPI requests, inaccessible source files, oversized requests and child-process cleanup. They use temporary free ports. A full run requires installed dependencies and Caddy; otherwise the integration test is skipped.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Python installer exit 1625 | Windows policy blocked installation. Read `logs/python-install-*.log` and ask the server administrator to review installation policies. Elevation alone may not resolve a policy restriction. |
| Installer exit 3010 | Installation requests a Windows restart. Schedule it before relying on the runtime. |
| Script execution blocked | Use the process-scoped command shown above. Domain Group Policy can override it; ask the administrator instead of changing machine policy blindly. |
| Download, TLS or certificate failure | Check the system clock, proxy and trusted certificates. Required hosts include python.org, github.com and release-asset hosts, pypi.org and files.pythonhosted.org. Do not disable verification. Corporate proxies may need separate PowerShell and Python configuration. |
| Checksum or signature failure | Stop; do not run the downloaded binary. Retry on a trusted connection and check upstream release information. |
| No matching Python package distribution | Check Python/Windows support and try a supported older Python in a new folder. ARM64 and 32-bit installations are not supported by this starter. |
| Port already in use | Pick `--port` / `--api-port`, or stop the conflicting application yourself. The starter never kills unrelated processes. Public mode needs ports 80/443. |
| API or Caddy exits during startup | Inspect `.runtime/api-*.log` and `.runtime/caddy-*.log`. Check antivirus quarantine and folder write permissions. |
| Browser shows API unavailable | Run the launcher and visit its HTTP URL; do not double-click `index.html`. Check logs and `/api/health`. |
| Public HTTPS fails | Check DNS (including AAAA), NAT, inbound ports, conflicting servers and certificate authority rate limits. See [Automatic HTTPS](https://caddyserver.com/docs/automatic-https). |
| Server disappears after logout/reboot | The launcher runs in the foreground. Configure managed services for permanent hosting. |

Logs accumulate in `.runtime` and `logs`; review and remove old log files periodically while the application is stopped. Keep certificate data. To undo a local installation, stop the launcher and remove this project folder; the shared per-user Python runtime remains and can be uninstalled separately if no other projects use it.

## References

- [Caddy documentation](https://caddyserver.com/docs/)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Python on Windows](https://docs.python.org/3/using/windows.html)
- [Python Server Starter](https://github.com/GeoKrown/python-server-starter) for a broader Python toolkit

MIT licensed. Contributions and reproducible bug reports are welcome.
