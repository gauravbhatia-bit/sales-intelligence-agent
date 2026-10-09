$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot

$venvPath = Join-Path $projectRoot ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"
$logPath = Join-Path $projectRoot ".logs"
$statePath = Join-Path $projectRoot ".local-services.json"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    py -3.11 -m venv $venvPath
}

New-Item -ItemType Directory -Path $logPath -Force | Out-Null
& $pythonPath -m pip install --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed. Review the pip error above."
}

$backend = Start-Process -FilePath $pythonPath `
    -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8080") `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logPath "backend.log") `
    -RedirectStandardError (Join-Path $logPath "backend-error.log") `
    -PassThru

$frontend = Start-Process -FilePath $pythonPath `
    -ArgumentList @("-m", "streamlit", "run", "frontend/app.py", "--server.address", "127.0.0.1", "--server.port", "8501", "--server.headless", "true") `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logPath "frontend.log") `
    -RedirectStandardError (Join-Path $logPath "frontend-error.log") `
    -PassThru

@{
    backend_pid = $backend.Id
    frontend_pid = $frontend.Id
} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8

$backendReady = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/" -TimeoutSec 2
        if ($health.status -eq "ok") {
            $backendReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $backendReady) {
    throw "Backend did not become healthy. See .logs/backend-error.log."
}

Write-Host "Backend:  http://127.0.0.1:8080/docs"
Write-Host "Frontend: http://127.0.0.1:8501"
Write-Host "PIDs saved to .local-services.json"
