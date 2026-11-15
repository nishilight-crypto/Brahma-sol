@echo off
setlocal
title Brahma Sol Celestial Installer
cd /d "%~dp0\.."
if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" "installer\install_wizard.py"
) else (
    start "" python "installer\install_wizard.py"
)
exit /b 0
