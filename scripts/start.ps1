param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runtimeRoot = Join-Path $projectRoot 'var'
$serviceUrl = 'http://127.0.0.1:8920'
function Test-ResearchServer {
    try { return (Invoke-RestMethod "$serviceUrl/api/health" -TimeoutSec 2).service -eq 'Research Desk' } catch { return $false }
}
if (Test-ResearchServer) {
    Write-Host "Research Desk is running: $serviceUrl"
    if (-not $NoBrowser) { Start-Process $serviceUrl }
    exit 0
}
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run scripts\setup.ps1 first.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'web\dist\index.html'))) { throw 'Frontend not built. Run scripts\setup.ps1 first.' }
if (Get-NetTCPConnection -LocalPort 8920 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8920 is occupied by another service.' }
New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$outLog=Join-Path $runtimeRoot "server-$stamp.out.log"
$errLog=Join-Path $runtimeRoot "server-$stamp.err.log"
$serverProcess=Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8920') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $outLog -RedirectStandardError $errLog
$deadline=(Get-Date).AddSeconds(30)
do {
    if (Test-ResearchServer) {
        $listener=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8920 -State Listen | Select-Object -First 1
        $actual=Get-Process -Id $listener.OwningProcess
        @{processId=$actual.Id;startTimeUtc=$actual.StartTime.ToUniversalTime().ToString('o');url=$serviceUrl} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeRoot 'server.json') -Encoding UTF8
        Write-Host "Research Desk is running: $serviceUrl"
        if (-not $NoBrowser) { Start-Process $serviceUrl }
        exit 0
    }
    $serverProcess.Refresh()
    if ($serverProcess.HasExited) { throw "Startup failed. Inspect $errLog" }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)
throw "Startup timed out. Inspect $errLog"
