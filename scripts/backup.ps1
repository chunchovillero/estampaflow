[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "..\backups"),
    [ValidateRange(1, 365)][int]$Keep = 14,
    [string]$ComposeFile = "docker-compose.yml"
)

$ErrorActionPreference = "Stop"
$outputPath = [IO.Path]::GetFullPath($OutputDirectory)
[IO.Directory]::CreateDirectory($outputPath) | Out-Null

$database = (& docker compose -f $ComposeFile exec -T db printenv POSTGRES_DB).Trim()
$username = (& docker compose -f $ComposeFile exec -T db printenv POSTGRES_USER).Trim()
if ($LASTEXITCODE -ne 0 -or -not $database -or -not $username) {
    throw "No fue posible leer la configuración del contenedor PostgreSQL."
}

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$fileName = "estampaflow-$timestamp.dump"
$containerFile = "/tmp/$fileName"
$destination = Join-Path $outputPath $fileName

try {
    & docker compose -f $ComposeFile exec -T db pg_dump -U $username -d $database -Fc -f $containerFile
    if ($LASTEXITCODE -ne 0) { throw "pg_dump no pudo generar el respaldo." }
    & docker compose -f $ComposeFile cp "db:$containerFile" $destination
    if ($LASTEXITCODE -ne 0) { throw "Docker no pudo copiar el respaldo al equipo." }
}
finally {
    & docker compose -f $ComposeFile exec -T db rm -f $containerFile | Out-Null
}

$backup = Get-Item -LiteralPath $destination
if ($backup.Length -eq 0) { throw "El respaldo generado está vacío." }

Get-ChildItem -LiteralPath $outputPath -Filter "estampaflow-*.dump" -File |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -Skip $Keep |
    Remove-Item -Force

Write-Output $backup.FullName
