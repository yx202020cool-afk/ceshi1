@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0\.."

python -m ashare_replay.cli ops-check
pause
