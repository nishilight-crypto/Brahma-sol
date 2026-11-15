@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Brahma Evo Local Launcher
cd /d "D:\titech\brahma-evo-local"
call "D:\titech\brahma-evo-local\start_brahma_local.bat"
exit /b %errorlevel%
