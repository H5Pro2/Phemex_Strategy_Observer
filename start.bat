@echo off
cd /d "%~dp0"

call venv\Scripts\activate



echo ================================
echo  Bot startet...
echo ================================


start "BOT" python runner.py
start "GUI" python _gui.py


echo.
echo ================================
echo  Fertig.
echo ================================
pause