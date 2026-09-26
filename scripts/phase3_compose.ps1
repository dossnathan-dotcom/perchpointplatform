# Operates only on the Compose project perchpoint-phase3.
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin"
    if (Test-Path (Join-Path $candidate "docker.exe")) {
        $env:Path = "$candidate;" + $env:Path
    }
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not available. Install Docker Desktop and start it, then rerun this script."
}
$action = if ($args.Count -gt 0) { $args[0] } else { "config" }
switch ($action) {
    "config" { docker compose -p perchpoint-phase3 config }
    "up" { docker compose -p perchpoint-phase3 up --build migrate seed api worker web }
    "down" { docker compose -p perchpoint-phase3 down --volumes }
    "drill" {
        if (-not $env:PHASE2_DEV_PASSWORD) {
            Write-Error "Set PHASE2_DEV_PASSWORD to the disposable Compose value before the drill."
        }
        python scripts/phase3_clean_room.py
    }
    default { Write-Error "Use config, up, down, or drill." }
}
