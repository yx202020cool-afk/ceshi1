@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0\.."
python -m uvicorn ashare_replay.api:app --host 127.0.0.1 --port 8000
