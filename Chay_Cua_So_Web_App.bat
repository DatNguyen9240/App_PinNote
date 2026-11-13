@echo off
title IELTS Corner Web Window
cd /d "%~dp0"

set "HTML_PATH=%~dp0desktop_app\standalone_window.html"

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app="file:///%HTML_PATH:\=/%" --window-size=440,560
    exit
)

if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --app="file:///%HTML_PATH:\=/%" --window-size=440,560
    exit
)

start "" "%HTML_PATH%"
exit

