param(
  [int]$Port = 8000,
  [switch]$OpenBrowser
)

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
  Write-Error 'The virtual environment is missing. Run scripts\setup.ps1 first.'
  exit 1
}

$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
  Write-Host "EvidenceLoop is already running at http://127.0.0.1:$Port" -ForegroundColor Green
  if ($OpenBrowser) { Start-Process "http://127.0.0.1:$Port" }
  exit 0
}

$logDir = Join-Path $projectRoot 'artifacts'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$proc = Start-Process -FilePath $python -ArgumentList '-m','uvicorn','evidenceloop.app:app','--host','127.0.0.1','--port',"$Port" -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'server.stdout.log') -RedirectStandardError (Join-Path $logDir 'server.stderr.log') -PassThru
$proc.Id | Set-Content (Join-Path $logDir 'server.pid')
Start-Sleep -Seconds 2
try {
  $health = Invoke-RestMethod "http://127.0.0.1:$Port/health"
  Write-Host "EvidenceLoop is running at http://127.0.0.1:$Port (PID $($proc.Id))" -ForegroundColor Green
  Write-Host "Health: $($health.status)"
  if ($OpenBrowser) { Start-Process "http://127.0.0.1:$Port" }
} catch {
  Write-Error "The server did not become healthy. Read artifacts\server.stderr.log."
  exit 1
}
