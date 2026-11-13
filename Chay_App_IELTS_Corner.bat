@echo off
title IELTS Corner Desktop
cd /d "%~dp0"

where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw desktop_app\app.py
) else (
    start "" python desktop_app\app.py
)
exit

