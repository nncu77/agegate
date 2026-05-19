<#
.SYNOPSIS
    Interactive prompt to populate the 3 SUPABASE_* values in backend/.env.

.DESCRIPTION
    For each key, the script:
      1. Tells you which Supabase dashboard field to copy.
      2. Waits for you to press ENTER (do NOT type the value here —
         it must be on the clipboard).
      3. Reads the clipboard, VALIDATES the format, and rejects
         obvious mistakes (e.g. you accidentally copied a PowerShell
         command from a chat window).
      4. Writes the validated value into backend/.env.

    The value never appears on stdout.

.EXAMPLE
    .\scripts\set-supabase-secrets.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$envPath = Join-Path $PSScriptRoot '..\backend\.env'
$envPath = [System.IO.Path]::GetFullPath($envPath)
if (-not (Test-Path $envPath)) {
    Write-Error "Not found: $envPath"
}

function Set-EnvKey {
    param(
        [string]$Key,
        [string]$Value
    )
    $newLine = '{0}="{1}"' -f $Key, $Value
    $lines   = Get-Content -Path $envPath -Encoding utf8
    $pattern = '^\s*{0}\s*=' -f [regex]::Escape($Key)
    $replaced = $false
    $out = foreach ($line in $lines) {
        if ($line -match $pattern) {
            $replaced = $true
            $newLine
        } else {
            $line
        }
    }
    if (-not $replaced) { $out = @($out) + $newLine }
    $tmp = "$envPath.tmp"
    [System.IO.File]::WriteAllText($tmp, ($out -join "`n") + "`n", [System.Text.UTF8Encoding]::new($false))
    Move-Item -Force $tmp $envPath
}

function Read-Validated {
    param(
        [string]$Key,
        [string]$WhereToFindIt,
        [scriptblock]$Validate,
        [string]$ExpectedFormat
    )
    while ($true) {
        Write-Host ""
        Write-Host "===== $Key =====" -ForegroundColor Cyan
        Write-Host $WhereToFindIt
        Write-Host "Expected format: $ExpectedFormat" -ForegroundColor DarkGray
        Read-Host "Copy the value to clipboard, then press ENTER (do NOT type the value here)" | Out-Null
        $raw = Get-Clipboard -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) {
            Write-Host "  Clipboard is empty. Try again." -ForegroundColor Yellow
            continue
        }
        $v = $raw.Trim()
        if ($v -match "`n") {
            $v = ($v -split "`r?`n")[0].Trim()
        }
        $err = & $Validate $v
        if ($err) {
            Write-Host "  REJECTED: $err" -ForegroundColor Red
            $retry = Read-Host "  Try again? [Y/n]"
            if ($retry -match '^[Nn]') { return $null }
            continue
        }
        Write-Host ("  OK (length={0})" -f $v.Length) -ForegroundColor Green
        return $v
    }
}

# --- SUPABASE_URL ---
$url = Read-Validated `
    -Key 'SUPABASE_URL' `
    -WhereToFindIt 'Supabase dashboard -> Project Settings -> API -> "Project URL" (copy the full URL)' `
    -ExpectedFormat 'https://<project-ref>.supabase.co' `
    -Validate {
        param($v)
        if ($v -like '.*' -or $v -like 'cd *' -or $v -like '*set-env*') { return "looks like a PowerShell command, not a URL" }
        if ($v -notmatch '^https://') { return "must start with https://" }
        if ($v -notmatch '\.supabase\.co/?$') { return "must end with .supabase.co" }
        if ($v -match '\s') { return "contains whitespace" }
        return $null
    }
if ($url) { Set-EnvKey -Key 'SUPABASE_URL' -Value $url }

# --- SUPABASE_SERVICE_KEY ---
$key = Read-Validated `
    -Key 'SUPABASE_SERVICE_KEY' `
    -WhereToFindIt 'Supabase dashboard -> Project Settings -> API -> "Legacy API keys" section -> service_role (NOT anon, NOT new sb_secret_*)' `
    -ExpectedFormat 'eyJ...<long base64 string with exactly 2 dots, typically 200+ chars>' `
    -Validate {
        param($v)
        if ($v -like '.*' -or $v -like 'cd *' -or $v -like '*set-env*') { return "looks like a PowerShell command, not a key" }
        if ($v -match '\s') { return "contains whitespace (JWTs do not)" }
        if ($v -like 'sb_secret_*' -or $v -like 'sb_publishable_*') { return "this is the new key format; supabase-py 2.9 needs the legacy 'eyJ...' JWT. Find the Legacy API keys section." }
        if (-not $v.StartsWith('eyJ')) { return "service_role JWT must start with 'eyJ'" }
        $dots = ($v.ToCharArray() | Where-Object { $_ -eq '.' }).Count
        if ($dots -ne 2) { return "JWT must have exactly 2 dots, found $dots" }
        if ($v.Length -lt 100) { return "too short (length=$($v.Length)); service_role JWT is typically 200+ chars" }
        return $null
    }
if ($key) { Set-EnvKey -Key 'SUPABASE_SERVICE_KEY' -Value $key }

# --- SUPABASE_JWT_SECRET ---
$jwt = Read-Validated `
    -Key 'SUPABASE_JWT_SECRET' `
    -WhereToFindIt 'Supabase dashboard -> Project Settings -> API -> "JWT Settings" -> "JWT Secret" (reveal + copy)' `
    -ExpectedFormat 'random string, typically 40-64 chars, no spaces' `
    -Validate {
        param($v)
        if ($v -like '.*' -or $v -like 'cd *' -or $v -like '*set-env*') { return "looks like a PowerShell command, not a secret" }
        if ($v -match '\s') { return "contains whitespace" }
        if ($v.Length -lt 32) { return "too short (length=$($v.Length)); JWT secret is typically 40+ chars" }
        if ($v.StartsWith('eyJ')) { return "this looks like a JWT, not the JWT *secret*. The secret is the HMAC key, not a token." }
        return $null
    }
if ($jwt) { Set-EnvKey -Key 'SUPABASE_JWT_SECRET' -Value $jwt }

Write-Host ""
Write-Host "Done. All 3 SUPABASE_* values written to backend/.env." -ForegroundColor Green
