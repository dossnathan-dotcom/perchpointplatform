# Operates only on the Compose project perchpoint-phase3.
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not available. Install Docker Desktop and start it, then rerun this script."
}
$action = if ($args.Count -gt 0) { $args[0] } else { "config" }
switch ($action) {
    "config" { docker compose -p perchpoint-phase3 config }
    "up" { docker compose -p perchpoint-phase3 up --build migrate seed api worker web }
    "down" { docker compose -p perchpoint-phase3 down --volumes }
    default { Write-Error "Use config, up, or down." }
}
