<#
.SYNOPSIS
    Write a secret from the Windows clipboard into backend/.env, never echoing it.

.DESCRIPTION
    Reads the current clipboard content, trims whitespace, and replaces
    (or appends) the KEY=VALUE line in backend/.env. The secret value
    never appears on stdout or in PowerShell history — only the key
    name and a "✓ set / length=N" confirmation are printed.

.PARAMETER Key
    The .env variable name, e.g. SUPABASE_SERVICE_KEY. Letters, digits,
    and underscore only — anything else is rejected.

.EXAMPLE
    # 1. Copy the value from Supabase dashboard (Ctrl+C)
    # 2. Run:
    .\scripts\set-env-from-clipboard.ps1 SUPABASE_SERVICE_KEY
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern('^[A-Z_][A-Z0-9_]*$')]
    [string]$Key
)

$ErrorActionPreference = 'Stop'

$envPath = Join-Path $PSScriptRoot '..\backend\.env'
$envPath = [System.IO.Path]::GetFullPath($envPath)

if (-not (Test-Path $envPath)) {
    Write-Error "Not found: $envPath. Run scripts/bootstrap.sh first (or copy backend/.env.example to backend/.env)."
}

$value = Get-Clipboard -Raw
if ([string]::IsNullOrWhiteSpace($value)) {
    Write-Error "Clipboard is empty. Copy the secret from the Supabase dashboard first, then re-run."
}
$value = $value.Trim()

# Safety net: warn if the clipboard contains a newline (likely accidental selection of multiple lines).
if ($value -match "`n") {
    Write-Warning "Clipboard contains a newline — keeping only the first line."
    $value = ($value -split "`r?`n")[0].Trim()
}

# Build the replacement line. Quote so values with spaces or special chars stay intact.
$newLine = '{0}="{1}"' -f $Key, $value

# Read existing .env, replace-or-append.
$lines    = Get-Content -Path $envPath -Encoding utf8
$pattern  = '^\s*{0}\s*=' -f [regex]::Escape($Key)
$replaced = $false
$out      = foreach ($line in $lines) {
    if ($line -match $pattern) {
        $replaced = $true
        $newLine
    } else {
        $line
    }
}
if (-not $replaced) {
    $out = @($out) + $newLine
}

# Write atomically with LF line endings (matches Linux-style .env convention).
$tmp = "$envPath.tmp"
[System.IO.File]::WriteAllText($tmp, ($out -join "`n") + "`n", [System.Text.UTF8Encoding]::new($false))
Move-Item -Force $tmp $envPath

Write-Host ("✓ {0} set in backend/.env (length={1})" -f $Key, $value.Length) -ForegroundColor Green
