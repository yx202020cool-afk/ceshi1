@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

where docker > nul 2> nul
if errorlevel 1 (
  echo 未检测到 Docker Desktop，无需执行 Docker 停止命令。
  pause
  exit /b 0
)

echo 正在停止 A 股每日复盘系统...
docker compose down
echo 已停止。
pause
