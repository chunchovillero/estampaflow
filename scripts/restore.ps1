[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$BackupFile,
    [switch]$ConfirmRestore,
    [string]$ComposeFile = "docker-compose.yml"
)

$ErrorActionPreference = "Stop"
if (-not $ConfirmRestore) {
    throw "La restauración reemplaza los datos actuales. Repite el comando con -ConfirmRestore."
}

$source = Get-Item -LiteralPath $BackupFile -ErrorAction Stop
if ($source.Length -eq 0 -or $source.Extension -ne ".dump") {
    throw "Selecciona un respaldo .dump válido y no vacío."
}

$database = (& docker compose -f $ComposeFile exec -T db printenv POSTGRES_DB).Trim()
$username = (& docker compose -f $ComposeFile exec -T db printenv POSTGRES_USER).Trim()
if ($LASTEXITCODE -ne 0 -or -not $database -or -not $username) {
    throw "No fue posible leer la configuración del contenedor PostgreSQL."
}

$containerFile = "/tmp/estampaflow-restore.dump"
& docker compose -f $ComposeFile cp $source.FullName "db:$containerFile"
if ($LASTEXITCODE -ne 0) { throw "Docker no pudo copiar el respaldo al contenedor." }

try {
    & docker compose -f $ComposeFile stop backend
    if ($LASTEXITCODE -ne 0) { throw "No fue posible detener temporalmente el backend." }
    & docker compose -f $ComposeFile exec -T db pg_restore --clean --if-exists --no-owner --no-privileges --single-transaction -U $username -d $database $containerFile
    if ($LASTEXITCODE -ne 0) { throw "La restauración falló; revisa la salida de pg_restore." }
}
finally {
    & docker compose -f $ComposeFile exec -T db rm -f $containerFile | Out-Null
    & docker compose -f $ComposeFile start backend | Out-Null
}

Write-Output "Base de datos restaurada desde $($source.FullName)"
