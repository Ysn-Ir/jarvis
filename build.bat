@echo off
title Build Laya Desktop Assistant
cd /d "%~dp0"
cls
echo ========================================================
echo   BUILDING LAYA -- Autonomous Desktop Assistant
echo ========================================================
python build.py
pause
