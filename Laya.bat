@echo off
title Laya Autonomous Desktop Assistant
cd /d "%~dp0"
cls
echo ========================================================
echo   LAYA -- Autonomous JARVIS Voice Desktop Assistant
echo   Launching Glassmorphic Desktop Application...
echo ========================================================
python -m laya.main --hud
pause
