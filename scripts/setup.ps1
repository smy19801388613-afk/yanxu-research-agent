param([string]$PythonPath = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    if ($PythonPath) {
        & $PythonPath -m venv (Join-Path $projectRoot '.venv')
    } elseif (Get-Command py.exe -ErrorAction SilentlyContinue) {
        & py.exe -3.12 -m venv (Join-Path $projectRoot '.venv')
    } elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
        & python.exe -m venv (Join-Path $projectRoot '.venv')
    } else { throw 'Install Python 3.12, or supply -PythonPath.' }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
& $venvPython -m pip install -r (Join-Path $projectRoot 'requirements-lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
$npmCommand=Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) { throw 'Install Node.js 22.12+ and reopen PowerShell.' }
Push-Location (Join-Path $projectRoot 'web')
try {
    & $npmCommand.Source ci --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    & $npmCommand.Source run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
Write-Host 'Setup completed. Run scripts\start.ps1.'
