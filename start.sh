#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
  cp ".env.example" ".env"
  echo "已创建 .env。演示模式不需要填写密钥。"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "未检测到 Docker Desktop。请先安装并启动 Docker Desktop。"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop 已安装，但当前没有运行。请先启动 Docker Desktop。"
  exit 1
fi

docker compose config >/dev/null

echo "正在启动 A 股每日复盘系统..."
docker compose up -d --build
echo "中文网页：http://127.0.0.1:8501"
echo "后端健康检查：http://127.0.0.1:8000/health"
