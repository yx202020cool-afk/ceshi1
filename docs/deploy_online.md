# 在线发布说明

本项目是 Python + Streamlit 应用，不适合发布到纯静态网页托管。推荐使用 Streamlit Cloud；如果需要更稳定的后台运行和持久化数据，可以用 Render、Railway 或自有服务器。

## 方案一：Streamlit Cloud

1. 把项目推送到 GitHub 仓库。
2. 打开 Streamlit Cloud，选择该仓库。
3. 主入口填写：

```text
ashare_replay/ui/streamlit_app.py
```

4. 环境变量建议：

```env
APP_MODE=demo
APP_TIMEZONE=Asia/Shanghai
REAL_PROVIDER=akshare
DATABASE_URL=sqlite:///work/data/ashare_replay.sqlite3
REPORT_OUTPUT_DIR=outputs/reports
CONFIG_PATH=configs/default_config.json
APP_PASSWORD=你自己的访问密码
LLM_ENABLED=false
```

5. 发布后把 Streamlit Cloud 生成的链接发给朋友。

## 方案二：Render

项目根目录已经包含 `render.yaml`，可以在 Render 中选择 Blueprint 导入。首次部署时至少填写：

```env
APP_PASSWORD=你自己的访问密码
```

Render 免费实例会休眠，首次访问可能较慢；SQLite 文件也可能随实例重建而变化。长期使用建议绑定持久化磁盘或改用 PostgreSQL。

## 真实数据提示

默认真实 Provider 为 AKShare，不需要密钥，但公开接口可能变化。若改用 Tushare，需要额外配置：

```env
REAL_PROVIDER=tushare
TUSHARE_TOKEN=你的密钥
```

无论使用哪种 Provider，系统不会在真实数据失败时静默切换为演示数据。
