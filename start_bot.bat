@echo off
setlocal
cd /d "%~dp0"

echo --------------------------------------------------
echo Trading Bot Agent System - Startpruefung
echo --------------------------------------------------

if not exist "phemex_strategy_observer.py" (
  echo FEHLER: phemex_strategy_observer.py nicht gefunden.
  echo Bitte start_bot.bat im Projektordner ausfuehren.
  pause
  exit /b 1
)

if not exist "requirements.txt" (
  echo FEHLER: requirements.txt nicht gefunden.
  echo Python-Abhaengigkeiten koennen nicht installiert werden.
  pause
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo FEHLER: Python wurde nicht gefunden.
  echo Bitte Python installieren und erneut starten.
  pause
  exit /b 1
)

if not exist "config.json" (
  if exist "config.example.json" (
    echo HINWEIS: config.json fehlt. Erstelle lokale config.json aus config.example.json.
    copy "config.example.json" "config.json" >nul
  ) else (
    echo FEHLER: config.json fehlt und config.example.json wurde nicht gefunden.
    echo Erwartet: Copy-Item config.example.json config.json
    pause
    exit /b 1
  )
)

if not exist ".env" (
  if exist ".env.example" (
    echo HINWEIS: .env fehlt. Erstelle lokale .env aus .env.example.
    copy ".env.example" ".env" >nul
  ) else (
    echo WARNUNG: .env fehlt und .env.example wurde nicht gefunden.
    echo Public-Klines koennen funktionieren, private Accountdaten nicht.
  )
)

if not exist "data" (
  mkdir "data"
)

if exist "prepare_dashboard_runtime.py" (
  echo --------------------------------------------------
  echo Bereite Dashboard Runtime vor
  echo --------------------------------------------------
  python prepare_dashboard_runtime.py
  if errorlevel 1 (
    echo FEHLER: Dashboard Runtime konnte nicht vorbereitet werden.
    pause
    exit /b 1
  )
)

echo --------------------------------------------------
echo Installiere/pruefe Python-Abhaengigkeiten
echo --------------------------------------------------
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo FEHLER: Python-Abhaengigkeiten konnten nicht installiert werden.
  pause
  exit /b 1
)

echo --------------------------------------------------
echo Starte Dashboard
echo --------------------------------------------------
python phemex_strategy_observer.py --config config.json --web
if errorlevel 1 (
  echo FEHLER: Bot wurde mit Fehler beendet.
  pause
  exit /b 1
)

pause