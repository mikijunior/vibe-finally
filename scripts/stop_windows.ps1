#Requires -Version 5.1
<#
.SYNOPSIS
    Stop the FinAlly Docker container (Windows PowerShell).
.DESCRIPTION
    Stops and removes the running FinAlly container. The named volume
    'finally-data' (which holds the SQLite database) is preserved so
    restarting the app keeps all trades and watchlist state.

    Usage:
        .\scripts\stop_windows.ps1
#>

$ErrorActionPreference = "Stop"

Set-Location -Path (Join-Path $PSScriptRoot "..")

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker is not installed or not on PATH."
    exit 1
}

# Ignore exit codes — the stop should be idempotent even if no container
# is currently running.
try { docker compose -f docker-compose.yml -p finally down 2>$null | Out-Null } catch {}
try { docker rm -f finally 2>$null | Out-Null } catch {}

Write-Host "FinAlly stopped. Data volume 'finally-data' preserved."
