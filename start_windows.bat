@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

if not exist ".env" (
  copy ".env.example" ".env" > nul
  echo 已创建 .env。演示模式不需要填写密钥。
)

where docker > nul 2> nul
if errorlevel 1 (
  echo 未检测到 Docker Desktop。
  echo 请先安装并启动 Docker Desktop，然后重新双击本脚本。
  pause
  exit /b 1
)

docker info > nul 2> nul
if errorlevel 1 (
  echo Docker Desktop 已安装，但当前没有运行。
  echo 请先打开 Docker Desktop，等待左下角显示正在运行后再重试。
  pause
  exit /b 1
)

docker compose config > nul
if errorlevel 1 (
  echo docker-compose.yml 配置检查未通过，请查看上方错误信息。
  pause
  exit /b 1
)

echo 正在启动 A 股每日复盘系统，请稍候...
docker compose up -d --build

echo.
echo 启动完成后，请打开浏览器访问：
echo   中文网页：http://127.0.0.1:8501
echo   后端健康检查：http://127.0.0.1:8000/health
echo.
pause
