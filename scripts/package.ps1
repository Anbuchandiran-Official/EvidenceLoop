$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$stamp = Get-Date -Format 'yyyyMMdd-HHmm'
$target = Join-Path $projectRoot "EvidenceLoop-submission-$stamp.zip"
$items = Get-ChildItem -Force | Where-Object { $_.Name -notin @('.venv','.git','.env','data') -and $_.Name -notlike 'EvidenceLoop-submission-*.zip' }
Compress-Archive -Path $items.FullName -DestinationPath $target -Force
Write-Host "Created $target" -ForegroundColor Green
