# --------------------------------------------------
# Trading Bot Agent System - PowerShell Start
# --------------------------------------------------

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

Write-Host "--------------------------------------------------"
Write-Host "Trading Bot Agent System - Startpruefung"
Write-Host "--------------------------------------------------"

if (-not (Test-Path "phemex_strategy_observer.py")) {
    Write-Host "FEHLER: phemex_strategy_observer.py nicht gefunden."
    Write-Host "Bitte start_bot.ps1 im Projektordner ausfuehren."
    exit 1
}

if (-not (Test-Path "requirements.txt")) {
    Write-Host "FEHLER: requirements.txt nicht gefunden."
    Write-Host "Python-Abhaengigkeiten koennen nicht installiert werden."
    exit 1
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "FEHLER: Python wurde nicht gefunden."
    Write-Host "Bitte Python installieren und erneut starten."
    exit 1
}

if (-not (Test-Path "config.json")) {
    if (Test-Path "config.example.json") {
        Write-Host "HINWEIS: config.json fehlt. Erstelle lokale config.json aus config.example.json."
        Copy-Item "config.example.json" "config.json"
    } else {
        Write-Host "FEHLER: config.json fehlt und config.example.json wurde nicht gefunden."
        Write-Host "Erwartet: Copy-Item config.example.json config.json"
        exit 1
    }
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "HINWEIS: .env fehlt. Erstelle lokale .env aus .env.example."
        Copy-Item ".env.example" ".env"
    } else {
        Write-Host "WARNUNG: .env fehlt und .env.example wurde nicht gefunden."
        Write-Host "Public-Klines koennen funktionieren, private Accountdaten nicht."
    }
}

if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

if (Test-Path "prepare_dashboard_runtime.py") {
    Write-Host "--------------------------------------------------"
    Write-Host "Bereite Dashboard Runtime vor"
    Write-Host "--------------------------------------------------"
    python prepare_dashboard_runtime.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FEHLER: Dashboard Runtime konnte nicht vorbereitet werden."
        exit 1
    }
}

if (Test-Path "checks/check_agent_runtime_roles.py") {
    Write-Host "--------------------------------------------------"
    Write-Host "Pruefe Agenten-Rollenvertrag"
    Write-Host "--------------------------------------------------"
    python checks/check_agent_runtime_roles.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FEHLER: Agenten-Rollenvertrag ist ungueltig."
        exit 1
    }
}

if (Test-Path "checks/check_brain_replay_enhancements.py") {
    Write-Host "--------------------------------------------------"
    Write-Host "Pruefe Brain Replay Enhancements"
    Write-Host "--------------------------------------------------"
    python checks/check_brain_replay_enhancements.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FEHLER: Brain Replay Enhancements sind ungueltig."
        exit 1
    }
}

if (Test-Path "checks/check_brain_dashboard_enhancements.py") {
    Write-Host "--------------------------------------------------"
    Write-Host "Pruefe Brain Dashboard Enhancements"
    Write-Host "--------------------------------------------------"
    python checks/check_brain_dashboard_enhancements.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FEHLER: Brain Dashboard Enhancements sind ungueltig."
        exit 1
    }
}

Write-Host "--------------------------------------------------"
Write-Host "Installiere/pruefe Python-Abhaengigkeiten"
Write-Host "--------------------------------------------------"
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "FEHLER: Python-Abhaengigkeiten konnten nicht installiert werden."
    exit 1
}

Write-Host "--------------------------------------------------"
Write-Host "Starte Dashboard"
Write-Host "--------------------------------------------------"
python phemex_strategy_observer.py --config config.json --web
if ($LASTEXITCODE -ne 0) {
    Write-Host "FEHLER: Bot wurde mit Fehler beendet."
    exit 1
}
