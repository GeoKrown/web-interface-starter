# Windows PowerShell 5.1+, Windows x64. Per-user install subject to Windows policies.
[CmdletBinding()]
param(
    [ValidatePattern('^(latest|3\.\d+\.\d+)$')][string]$PythonVersion = 'latest',
    [string]$PythonPath,
    [switch]$Plan
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\bootstrap-functions.ps1"

try {
    if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') {
        throw 'This installer supports Windows x64 only.'
    }
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    if ($PythonPath) {
        if ($Plan) { Write-Host 'Use the supplied Python executable; create .venv and install dependencies and Caddy.'; exit 0 }
        Invoke-Checked -Exe $PythonPath -Arguments @("$PSScriptRoot\bootstrap.py")
        exit 0
    }
    $page = Invoke-WebRequest 'https://www.python.org/downloads/windows/' -UseBasicParsing -TimeoutSec 60
    $release = Get-PythonInstaller -Html $page.Content -Version $PythonVersion
    $target = Join-Path $env:LOCALAPPDATA "PythonServerStarter\Python-$($release.Version)"
    $python = Join-Path $target 'python.exe'
    Write-Host "Python: $($release.Version) x64"
    Write-Host "Source: $($release.Url)"
    Write-Host "Runtime: $target"
    Write-Host "Environment: $PSScriptRoot\.venv"
    if ($Plan) { Write-Host 'Plan only: nothing downloaded or installed.'; exit 0 }

    if (-not (Test-Path -LiteralPath $python)) {
        $temp = Join-Path ([IO.Path]::GetTempPath()) ('python-starter-' + [guid]::NewGuid().ToString('N') + '.exe')
        try {
            Invoke-WebRequest $release.Url -OutFile $temp -UseBasicParsing -TimeoutSec 300
            $signature = Get-AuthenticodeSignature -LiteralPath $temp
            if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
                throw 'Installer signature is not a valid Python Software Foundation signature. Installation stopped.'
            }
            $logDir = Join-Path $PSScriptRoot 'logs'
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
            $logPath = Join-Path $logDir ('python-install-' + [guid]::NewGuid().ToString('N') + '.log')
            Write-Host "Installer log: $logPath"
            $arguments = '/quiet /log "' + $logPath + '" InstallAllUsers=0 PrependPath=1 Include_launcher=0 Include_test=0 Include_pip=1 TargetDir="' + $target + '"'
            $process = Start-Process -FilePath $temp -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
            if ($process.ExitCode -eq 1625) {
                throw "Windows policy blocked the Python installer (1625). No policy settings were changed. Inspect installer logs in $logDir and Windows Installer policies with your server administrator. Log: $logPath"
            }
            if ($process.ExitCode -notin @(0,3010)) { throw "Python installer failed: $($process.ExitCode). Log: $logPath" }
            if ($process.ExitCode -eq 3010) { Write-Warning 'Windows requests a restart.' }
        } finally {
            if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Force }
        }
    }
    if (-not (Test-Path -LiteralPath $python)) { throw 'Installer did not create python.exe.' }
    Invoke-Checked -Exe $python -Arguments @('-c', "import sys,struct; assert '.'.join(map(str,sys.version_info[:3])) == '$($release.Version)'; assert struct.calcsize('P') == 8; print(sys.version)")
    Invoke-Checked -Exe $python -Arguments @("$PSScriptRoot\bootstrap.py")
} catch {
    Write-Error -Message $_ -ErrorAction Continue
    exit 1
}
