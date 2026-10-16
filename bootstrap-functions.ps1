Set-StrictMode -Version Latest

function Get-PythonInstaller {
    param([string]$Html, [string]$Version = 'latest')
    # Only final releases with official x64 EXE installers; never prereleases/MSIX.
    $pattern = 'https://www\.python\.org/ftp/python/(?<version>3\.\d+\.\d+)/python-\k<version>-amd64\.exe'
    $items = @([regex]::Matches($Html, $pattern) | ForEach-Object {
        [pscustomobject]@{ Version = $_.Groups['version'].Value; Url = $_.Value }
    } | Sort-Object { [version]$_.Version } -Descending -Unique)
    if ($Version -ne 'latest') { $items = @($items | Where-Object Version -EQ $Version) }
    if ($items.Count -eq 0) { throw "No official stable x64 installer found for '$Version'. Nothing installed." }
    return $items[0]
}

function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE): $Exe" }
}
