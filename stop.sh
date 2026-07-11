#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "未检测到 Docker Desktop，无需执行 Docker 停止命令。"
  exit 0
fi

echo "正在停止 A 股每日复盘系统..."
docker compose down
echo "已停止。"
