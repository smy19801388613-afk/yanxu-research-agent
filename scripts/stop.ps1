$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$stateFile=Join-Path $projectRoot 'var\server.json'
if (-not (Test-Path -LiteralPath $stateFile)) { Write-Host 'No recorded Research Desk server.'; exit 0 }
$state=Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
$process=Get-Process -Id $state.processId -ErrorAction SilentlyContinue
if ($process -and $process.StartTime.ToUniversalTime() -eq ([datetimeoffset]$state.startTimeUtc).UtcDateTime) {
    Stop-Process -Id $process.Id
    Write-Host 'Research Desk stopped. Active research workers finish separately; cancel them in the UI before stopping.'
} else { Write-Host 'The recorded process is no longer running. No process was stopped.' }
