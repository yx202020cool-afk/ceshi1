# 故障排查

## 网页打不开

- 确认 Docker Desktop 已启动。
- 运行 `python -m ashare_replay.cli ops-check`，查看 Docker 和 Compose 状态。
- 确认 `start_windows.bat` 没有报错。
- 浏览器访问 `http://127.0.0.1:8501`。
- 查看 `work/logs/ashare_replay.log`。

## 真实数据不可用

- 检查 `.env` 中 `APP_MODE=real`。
- 默认免费源使用 `REAL_PROVIDER=akshare`，不需要密钥。
- 确认本机或 Docker 已安装 `requirements.txt` 中的依赖。
- 运行 `python -m ashare_replay.cli provider-audit --save`。
- 如果改用 `REAL_PROVIDER=tushare`，再检查 `TUSHARE_TOKEN` 是否填写，并确认账号具备对应接口权限。

## 报告没有新闻证据

系统会显示“证据不足”。这不是错误，表示当前 Provider 在报告截止时间前没有提供可引用的新闻、公告或政策证据。

## Docker 启动慢

第一次启动会下载镜像和安装依赖，等待时间较长。后续启动会快很多。

## 端口被占用

如果 `8501` 或 `8000` 被占用，先运行 `stop_windows.bat`。仍无法解决时，修改 `.env` 中的端口或关闭占用端口的软件。
