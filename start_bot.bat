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

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if "%PYTHON_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)
if "%PYTHON_CMD%"=="" (
  echo FEHLER: Python wurde nicht gefunden.
  echo Bitte Python installieren oder den Windows Python Launcher py aktivieren.
  pause
  exit /b 1
)

echo Python Runtime: %PYTHON_CMD%

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

if exist "tools\prepare_dashboard_runtime.py" (
  echo --------------------------------------------------
  echo Bereite Dashboard Runtime vor
  echo --------------------------------------------------
  %PYTHON_CMD% tools\prepare_dashboard_runtime.py
  if errorlevel 1 (
    echo FEHLER: Dashboard Runtime konnte nicht vorbereitet werden.
    pause
    exit /b 1
  )
)

if exist "checks\check_dashboard_runtime_patches.py" (
  echo --------------------------------------------------
  echo Pruefe Dashboard Runtime Patches
  echo --------------------------------------------------
  %PYTHON_CMD% checks\check_dashboard_runtime_patches.py
  if errorlevel 1 (
    echo FEHLER: Dashboard Runtime Patches sind ungueltig.
    pause
    exit /b 1
  )
)

if exist "checks\check_agent_runtime_roles.py" (
  echo --------------------------------------------------
  echo Pruefe Agenten-Rollenvertrag
  echo --------------------------------------------------
  %PYTHON_CMD% checks\check_agent_runtime_roles.py
  if errorlevel 1 (
    echo FEHLER: Agenten-Rollenvertrag ist ungueltig.
    pause
    exit /b 1
  )
)

if exist "checks\check_brain_replay_enhancements.py" (
  echo --------------------------------------------------
  echo Pruefe Brain Replay Enhancements
  echo --------------------------------------------------
  %PYTHON_CMD% checks\check_brain_replay_enhancements.py
  if errorlevel 1 (
    echo FEHLER: Brain Replay Enhancements sind ungueltig.
    pause
    exit /b 1
  )
)

if exist "checks\check_brain_dashboard_enhancements.py" (
  echo --------------------------------------------------
  echo Pruefe Brain Dashboard Enhancements
  echo --------------------------------------------------
  %PYTHON_CMD% checks\check_brain_dashboard_enhancements.py
  if errorlevel 1 (
    echo FEHLER: Brain Dashboard Enhancements sind ungueltig.
    pause
    exit /b 1
  )
)

echo --------------------------------------------------
echo Installiere/pruefe Python-Abhaengigkeiten
echo --------------------------------------------------
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
  echo FEHLER: Python-Abhaengigkeiten konnten nicht installiert werden.
  pause
  exit /b 1
)

echo --------------------------------------------------
echo Starte Dashboard
echo --------------------------------------------------
%PYTHON_CMD% phemex_strategy_observer.py --config config.json --web
if errorlevel 1 (
  echo FEHLER: Bot wurde mit Fehler beendet.
  pause
  exit /b 1
)

pause
