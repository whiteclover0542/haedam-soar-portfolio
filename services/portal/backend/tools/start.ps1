param([switch]$Setup, [switch]$SeedDemo, [int]$Port = 5000)
$ErrorActionPreference = 'Stop'
$backendRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path (Split-Path -Parent $backendRoot) 'haedam-portal-frontend'
Set-Location -LiteralPath $backendRoot
$allowedSettings = @('DATABASE_URL','FRONTEND_DIST','COOKIE_SECURE','GELF_ENABLED','GELF_HOST','GELF_PORT','EVENT_LOG_PATH','ASSET_ID','RESPONSE_API_KEY','RESPONSE_ALLOWED_CIDRS','DASHBOARD_URL')
if (Test-Path -LiteralPath '.env') {
    foreach ($configLine in Get-Content -LiteralPath '.env') {
        if ($configLine -match '^\s*([A-Z_]+)\s*=(.*)$' -and $allowedSettings -contains $Matches[1]) {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim().Trim('"').Trim("'"), 'Process')
        }
    }
}
$portalPython = Join-Path $backendRoot '.venv/Scripts/python.exe'
if ($Setup) {
    python tools/bootstrap.py
    if ($LASTEXITCODE -ne 0) { throw 'Backend setup failed' }
    Push-Location -LiteralPath $frontendRoot
    try {
        npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend install failed' }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    } finally { Pop-Location }
}
if (-not (Test-Path -LiteralPath $portalPython)) { throw 'Run with -Setup first.' }
if ($SeedDemo) {
    & $portalPython -m flask --app haedam_portal:create_app seed-demo --confirm
    if ($LASTEXITCODE -ne 0) { throw 'Demo seed requires an empty database. Existing data was preserved.' }
}
Write-Host "Haedam portal: http://127.0.0.1:$Port (Ctrl+C to stop)"
& (Join-Path $backendRoot '.venv/Scripts/waitress-serve.exe') --host=127.0.0.1 "--port=$Port" --threads=4 --call haedam_portal:create_app
