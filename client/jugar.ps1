<#
.SYNOPSIS
    Lanza el cliente de Control del Reactor con el control físico ya configurado.

.DESCRIPTION
    Pone las variables de entorno que necesita el cliente (CONTROL_PUERTO y SERVER_URL) y lo
    arranca. Así no hay que acordarse de escribirlas cada vez ni se pierden al abrir otra terminal.

    Antes de jugar en local hay que tener el backend arriba (`docker compose up` en la raíz) y el
    Monitor Serie del Arduino IDE CERRADO, porque ocupa el puerto COM.

.PARAMETER Puerto
    Puerto del control físico. Por defecto COM5.

.PARAMETER Simulador
    Usa el simulador de hardware/simulator en vez de la placa.

.PARAMETER SinControl
    Solo teclado, sin control físico.

.PARAMETER Nube
    Juega contra la VM de Azure en vez del backend local.

.EXAMPLE
    .\jugar.ps1
    Control en COM5 contra el backend local.

.EXAMPLE
    .\jugar.ps1 -Puerto COM3
    Para cuando Windows le asigna otro puerto a la placa.

.EXAMPLE
    .\jugar.ps1 -Simulador
    Para probar sin tener el Arduino a mano.
#>
param(
    [string]$Puerto = "COM5",
    [switch]$Simulador,
    [switch]$SinControl,
    [switch]$Nube
)

$URL_NUBE = "https://control-reactor.northcentralus.cloudapp.azure.com/api"
$URL_LOCAL = "http://localhost:8000"

Set-Location $PSScriptRoot

# --- Control físico ---------------------------------------------------------------------------
if ($SinControl) {
    $env:CONTROL_PUERTO = ""
    Write-Host "Control : solo teclado" -ForegroundColor Yellow
}
elseif ($Simulador) {
    $env:CONTROL_PUERTO = "socket://localhost:7777"
    Write-Host "Control : simulador (hardware/simulator)" -ForegroundColor Cyan
}
else {
    $env:CONTROL_PUERTO = $Puerto
    Write-Host "Control : $Puerto" -ForegroundColor Cyan
}

# --- Servidor ---------------------------------------------------------------------------------
if ($Nube) {
    $env:SERVER_URL = $URL_NUBE
}
else {
    # Vacío = el cliente usa localhost:8000 por su cuenta (src/config.py)
    $env:SERVER_URL = ""
}
$servidor = if ($Nube) { $URL_NUBE } else { $URL_LOCAL }
Write-Host "Servidor: $servidor" -ForegroundColor Cyan

# --- Versión de Python ------------------------------------------------------------------------
# El cliente se prueba con Python 3.12 (la versión del CI). Con otra versión se avisa y se sigue.
$versionPython = python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null
if (-not $versionPython) {
    Write-Host "No se encontró Python. Instalá Python 3.12 desde python.org (marcá 'Add to PATH')." -ForegroundColor Red
    exit 1
}
if ($versionPython -ne "3.12") {
    Write-Host "Aviso: Python $versionPython. El juego se prueba con 3.12; si algo falla, usá un entorno con 3.12." -ForegroundColor Yellow
}
else {
    Write-Host "Python  : $versionPython" -ForegroundColor Cyan
}

# --- Dependencias -----------------------------------------------------------------------------
python -c "import pygame, requests, serial, websockets, certifi" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Faltan dependencias del cliente, instalando..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "No se pudieron instalar las dependencias." -ForegroundColor Red
        exit 1
    }
}

# --- Aviso si el backend no responde ------------------------------------------------------------
try {
    Invoke-WebRequest -Uri "$servidor/health" -TimeoutSec 3 -UseBasicParsing | Out-Null
}
catch {
    Write-Host ""
    if ($Nube) {
        Write-Host "Aviso: la nube no responde. Revisá que la VM esté encendida." -ForegroundColor Yellow
    }
    else {
        Write-Host "Aviso: el backend local no responde." -ForegroundColor Yellow
        Write-Host "       Levantalo en otra terminal, desde la raíz del proyecto: docker compose up" -ForegroundColor Yellow
    }
    Write-Host ""
}

Write-Host ""
python main.py
