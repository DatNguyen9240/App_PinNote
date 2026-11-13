@echo off
title IELTS Corner Desktop
cd /d "%~dp0"
start "" pythonw desktop_app\app.py
if errorlevel 1 (
    start "" python desktop_app\app.py
)
exit

