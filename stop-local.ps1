$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$statePath = Join-Path $projectRoot ".local-services.json"

if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Host "No local service state file found."
    exit 0
}

$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
foreach ($processId in @($state.backend_pid, $state.frontend_pid)) {
    if ($processId) {
        Stop-Process -Id $processId -ErrorAction SilentlyContinue
    }
}

Remove-Item -LiteralPath $statePath -Force
Write-Host "Local services stopped."
