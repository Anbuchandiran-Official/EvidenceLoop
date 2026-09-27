$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { Write-Error 'Install Python 3.10 or newer, then run this script again.'; exit 1 }

if (-not (Test-Path '.venv\Scripts\python.exe')) {
  & $python.Source -3 -m venv .venv
  if ($LASTEXITCODE -ne 0) { & $python.Source -m venv .venv }
}
& '.\.venv\Scripts\python.exe' -m pip install --disable-pip-version-check --no-cache-dir -r requirements.lock.txt
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
Write-Host 'Setup complete. Edit .env for live Gemini/Tavily research, then run scripts\run.ps1 -OpenBrowser.' -ForegroundColor Green
