@echo off
setlocal
cd /d "%~dp0"

if not exist "config.json" (
  echo FEHLER: config.json nicht gefunden.
  pause
  exit /b 1
)

if not exist "phemex_strategy_observer.py" (
  echo FEHLER: phemex_strategy_observer.py nicht gefunden.
  pause
  exit /b 1
)

python -m pip install -r requirements.txt
python phemex_strategy_observer.py --config config.json --web

pause