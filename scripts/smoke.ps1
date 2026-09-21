[CmdletBinding()]
param(
    [string]$ApiUrl = "http://localhost:8000",
    [string]$FrontendUrl = "http://localhost:5173"
)

$ErrorActionPreference = "Stop"
$api = $ApiUrl.TrimEnd("/")
$frontend = $FrontendUrl.TrimEnd("/")
$results = [System.Collections.Generic.List[object]]::new()

function Get-ResponseText {
    param($Response)
    if ($Response.Content -is [byte[]]) { return [Text.Encoding]::UTF8.GetString($Response.Content) }
    return [string]$Response.Content
}

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [scriptblock]$Validate
    )
    $timer = [Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -TimeoutSec 15
        if ($response.StatusCode -ne 200) { throw "HTTP $($response.StatusCode)" }
        & $Validate $response
        $timer.Stop()
        $results.Add([pscustomobject]@{Comprobacion=$Name;Estado="OK";Milisegundos=$timer.ElapsedMilliseconds})
    }
    catch {
        $timer.Stop()
        $results.Add([pscustomobject]@{Comprobacion=$Name;Estado="ERROR";Milisegundos=$timer.ElapsedMilliseconds})
        throw "Falló '$Name' ($Url): $($_.Exception.Message)"
    }
}

Test-Endpoint "Frontend" "$frontend/" {
    param($response)
    if ((Get-ResponseText $response) -notmatch "EstampaFlow") { throw "El HTML no contiene la marca esperada." }
}
Test-Endpoint "API y PostgreSQL" "$api/api/health/" {
    param($response)
    if (((Get-ResponseText $response) | ConvertFrom-Json).status -ne "ok") { throw "La API no informó estado ok." }
}
Test-Endpoint "Regiones y comunas" "$api/api/v1/businesses/territories/" {
    param($response)
    $territories = (Get-ResponseText $response) | ConvertFrom-Json
    $communes = ($territories | ForEach-Object { $_.communes.Count } | Measure-Object -Sum).Sum
    if ($territories.Count -ne 16 -or $communes -ne 346) { throw "El catálogo territorial está incompleto." }
}
Test-Endpoint "Marketplace público" "$api/api/v1/public/marketplace/" {
    param($response)
    $marketplace = (Get-ResponseText $response) | ConvertFrom-Json
    foreach ($field in @("products", "featured_products", "featured_businesses", "categories", "regions")) {
        if ($marketplace.PSObject.Properties.Name -notcontains $field) { throw "Falta el campo $field." }
    }
}
Test-Endpoint "Esquema OpenAPI" "$api/api/schema/" {
    param($response)
    $content = Get-ResponseText $response
    if ($content -notmatch "(?m)^openapi:" -and $content -notmatch '"openapi"\s*:') { throw "La respuesta no contiene un esquema OpenAPI." }
}
Test-Endpoint "Swagger" "$api/api/docs/" {
    param($response)
    if ((Get-ResponseText $response) -notmatch "SwaggerUIBundle") { throw "Swagger UI no cargó correctamente." }
}

$results | Format-Table -AutoSize
Write-Output "Smoke test completado: $($results.Count) comprobaciones aprobadas."
