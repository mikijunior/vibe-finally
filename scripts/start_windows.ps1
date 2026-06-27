#Requires -Version 5.1
<#
.SYNOPSIS
    Start the FinAlly Docker container (Windows PowerShell).
.DESCRIPTION
    Builds the image if it does not yet exist, then starts the FinAlly
    container via docker compose. Idempotent: re-running on a healthy
    container exits 0 with a notice.

    Usage:
        .\scripts\start_windows.ps1           # start (build if needed)
        .\scripts\start_windows.ps1 -Build    # force a rebuild
#>

[CmdletBinding()]
param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

Set-Location -Path (Join-Path $PSScriptRoot "..")

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker is not installed or not on PATH."
    exit 1
}

$running = docker ps -q -f name=finally 2>$null
if ($running) {
    Write-Host "FinAlly is already running at http://localhost:8000"
    exit 0
}

$imageExists = $false
try {
    docker image inspect finally 2>$null | Out-Null
    $imageExists = $true
} catch {
    $imageExists = $false
}

if ($Build -or -not $imageExists) {
    Write-Host "Building FinAlly image (this can take a few minutes on first run)..."
    docker compose -f docker-compose.yml -p finally build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Starting FinAlly container..."
docker compose -f docker-compose.yml -p finally up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Waiting for FinAlly to be ready..."
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($ready) {
    Write-Host ""
    Write-Host "FinAlly is running at http://localhost:8000"
    exit 0
}

Write-Warning "FinAlly did not respond to /api/health within 30s. The container may still be starting. Check 'docker logs finally'."
exit 1
