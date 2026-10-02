param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runtimeRoot = Join-Path $projectRoot 'var'
$serviceUrl = 'http://127.0.0.1:8920'
$versionMatch = [regex]::Match([System.IO.File]::ReadAllText((Join-Path $projectRoot 'app\config.py')), '(?m)^VERSION\s*=\s*"([^"]+)"')
if (-not $versionMatch.Success) { throw 'Cannot read the local application version from app\config.py.' }
$expectedVersion = $versionMatch.Groups[1].Value
$indexPath = Join-Path $projectRoot 'web\dist\index.html'
function Get-ResearchServer {
    try {
        $health = Invoke-RestMethod "$serviceUrl/api/health" -TimeoutSec 2
        if ($health.service -eq 'Research Desk') { return $health }
    } catch {}
    return $null
}
function Show-ResearchServer($health) {
    if ($health.version -ne $expectedVersion) {
        throw "Port 8920 is running v$($health.version), but this directory contains v$expectedVersion. Stop the old service with scripts\stop.ps1, then start again."
    }
    $pageId = 'missing-build'
    if (Test-Path -LiteralPath $indexPath) {
        $hasher = [System.Security.Cryptography.SHA256]::Create()
        try { $pageId = [BitConverter]::ToString($hasher.ComputeHash([System.IO.File]::ReadAllBytes($indexPath))).Replace('-','').Substring(0,12).ToLowerInvariant() }
        finally { $hasher.Dispose() }
    }
    $openUrl = "$serviceUrl/?v=$($health.version)&ui=$pageId"
    try { $Host.UI.RawUI.WindowTitle = "Research Desk v$($health.version)" } catch {}
    Write-Host "Research Desk v$($health.version) is running." -ForegroundColor Magenta
    Write-Host "Project: $projectRoot"
    Write-Host "Open: $openUrl"
    if (-not $NoBrowser) { Start-Process $openUrl }
}
$running = Get-ResearchServer
if ($running) {
    Show-ResearchServer $running
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
    $running = Get-ResearchServer
    if ($running) {
        $listener=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8920 -State Listen | Select-Object -First 1
        $actual=Get-Process -Id $listener.OwningProcess
        @{processId=$actual.Id;startTimeUtc=$actual.StartTime.ToUniversalTime().ToString('o');url=$serviceUrl} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeRoot 'server.json') -Encoding UTF8
        Show-ResearchServer $running
        exit 0
    }
    $serverProcess.Refresh()
    if ($serverProcess.HasExited) { throw "Startup failed. Inspect $errLog" }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)
throw "Startup timed out. Inspect $errLog"
