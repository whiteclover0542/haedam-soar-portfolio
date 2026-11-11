[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('start', 'lite', 'stop', 'status')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
$candidates = @(
    'D:\Docker\Docker\resources\bin\docker.exe',
    (Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe')
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

if ($candidates.Count -eq 0) {
    throw 'Docker CLI를 찾지 못했습니다. Docker Desktop 설치를 확인하세요.'
}

$docker = $candidates[0]

switch ($Action) {
    'start' {
        & $docker compose --profile '*' up -d
        & $docker compose ps
    }
    'lite' {
        # A low-memory portal demonstration. It deliberately excludes the
        # log pipeline, automation, and pfSense, so it is not a full MVP run.
        & $docker compose -f compose.yaml -f compose.lite.yaml up -d portal-db portal ticket-store
        & $docker compose -f compose.yaml -f compose.lite.yaml ps portal-db portal ticket-store
    }
    'stop' {
        & $docker compose --profile '*' stop -t 30
        & $docker compose ps --all
    }
    'status' {
        & $docker compose ps --all
        & $docker stats --no-stream
    }
}
