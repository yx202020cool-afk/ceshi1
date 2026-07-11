# A 股每日全局复盘与板块资金分析系统

这是一个中文本地网页应用，用于每日复盘 A 股市场，从全局市场、行业板块、概念板块、资金流、生命周期、龙头评分、周线持续流入和候选观察池等角度生成结构化研究报告。

系统只用于市场研究和复盘，不构成投资建议，不承诺收益，不输出无条件买入、卖出或仓位指令，也不提供自动下单能力。

## 能做什么

- 生成 14:50 盘中预览版、15:10 收盘确认版、17:30 盘后完整版三种报告。
- 行业板块和概念板块分开排名，分别展示涨幅前三、跌幅前三和资金流排名。
- 给重点板块计算前五只代表性股票，并展示总分和子分数。
- 用确定性规则判断板块生命周期：启动、发酵、加速、高潮、分歧、退潮、修复、震荡或无法判断。
- 展示原因归因和证据；没有证据时明确写“证据不足”。
- 输出 JSON、Markdown、HTML、PDF 和 CSV 附件。
- 在演示模式下不需要任何第三方密钥即可运行。
- 提供 Docker Compose、Windows 双击脚本、macOS/Linux 脚本、API、定时任务和测试。

## 不能做什么

- 不能替你决定买入、卖出、仓位或自动下单。
- 不能保证上涨或收益。
- 不能在没有真实数据权限时伪装成真实行情。
- 不能把演示数据当成真实数据。
- 不能把不同供应商的资金流口径直接混合比较。

## 最简单启动方式：Windows

1. 安装 Docker Desktop。
2. 双击根目录的 `start_windows.bat`。
3. 等脚本完成后，用浏览器打开 `http://127.0.0.1:8501`。
4. 停止系统时，双击 `stop_windows.bat`。

第一次启动时脚本会自动把 `.env.example` 复制成 `.env`。演示模式不需要填写密钥。

## macOS / Linux 启动

在项目根目录运行：

```bash
sh start.sh
```

停止：

```bash
sh stop.sh
```

## 浏览器访问地址

- 中文网页：`http://127.0.0.1:8501`
- 后端健康检查：`http://127.0.0.1:8000/health`

## 发布到网上

本项目是 Python + Streamlit 应用，推荐发布到 Streamlit Cloud 或 Render。项目已经包含 `.streamlit/config.toml`、`Procfile` 和 `render.yaml`，详细步骤见 `docs/deploy_online.md`。

公开分享前建议设置：

```env
APP_PASSWORD=你自己的访问密码
APP_MODE=demo
REAL_PROVIDER=akshare
```

## 演示模式和真实数据模式

默认是演示模式：

```env
APP_MODE=demo
```

演示模式使用系统内置的固定规则数据，报告中会明确标注“演示数据，不代表真实行情”。

切换真实数据模式：

```env
APP_MODE=real
REAL_PROVIDER=akshare
```

`akshare` 是默认真实数据 Provider，使用免费公开数据源，不需要填写密钥。公开数据源的字段、更新时间和接口可用性可能变化；系统会把缺失的新闻、公告、资金流或指数字段标成缺失/不支持，不会静默切回演示数据，也不会把演示数据伪装成真实行情。

切换后先运行 Provider 自检：

```bash
python -m ashare_replay.cli provider-audit --save
```

也可以只检查配置、不访问外部接口：

```bash
python -m ashare_replay.cli provider-audit --no-probe
```

自检结果会明确显示缺少密钥、缺少 Python 包、接口不存在、权限不足、返回空数据等状态。

如果你后续已经有 Tushare 权限，也可以把真实源切回 Tushare：

```env
APP_MODE=real
REAL_PROVIDER=tushare
TUSHARE_TOKEN=你的密钥
```

Tushare 属于可选权限型数据源；没有密钥或权限时，系统会明确报错。

## 如何生成报告

Docker 启动后，网页里可以在“历史报告”页面手动生成。

本机 Python 方式：

```bash
python -m ashare_replay.cli generate-all --date today
```

今天如果是非交易日，命令会取最近一个交易日。2026-07-11 是周六，本项目示例报告使用 2026-07-10。

生成某个版本：

```bash
python -m ashare_replay.cli generate --date 2026-07-10 --report-type POST_CLOSE_FINAL
```

## 如何查看历史报告

网页打开“历史报告”页面即可查看。

报告文件默认保存在：

```text
outputs/reports/日期/报告版本/
```

例如：

```text
outputs/reports/2026-07-10/POST_CLOSE_FINAL/report.html
```

## 如何修改报告时间

打开 `configs/default_config.json`，修改：

```json
"report_times": {
  "PRE_CLOSE_PREVIEW": "14:50",
  "CLOSE_CONFIRMATION": "15:10",
  "POST_CLOSE_FINAL": "17:30"
}
```

修改后重新启动系统。

## 如何备份

需要备份三类内容：

- `work/data/`：本地 SQLite 数据库。
- `outputs/reports/`：已经生成的报告。
- `.env`：你的本地配置。注意不要公开分享 `.env`，里面可能有密钥。

使用 Docker PostgreSQL 时，详见 `docs/backup_restore.md`。

## 常用命令

```bash
python -m ashare_replay.cli init-db
python -m ashare_replay.cli health
python -m ashare_replay.cli provider-audit --no-probe
python -m ashare_replay.cli ops-check
python -m ashare_replay.cli build-fixture --start 2026-04-01 --end 2026-07-10
python -m ashare_replay.cli latest
python -m ashare_replay.cli backtest --start 2026-07-06 --end 2026-07-10
python -m pytest
python -m ruff check ashare_replay tests
python -m mypy ashare_replay
```

## 如何确认不是演示数据

在网页“今日总览”和报告文件里查看：

- `data_status`
- `provider`
- `quality_warnings`

如果看到 `demo` 或“演示数据”，就不是正式行情。

## 如何确认报告版本

每份报告都会显示：

- `PRE_CLOSE_PREVIEW`：14:50 盘中预览版，非最终数据。
- `CLOSE_CONFIRMATION`：15:10 收盘确认版，部分资金数据可能仍为暂定。
- `POST_CLOSE_FINAL`：17:30 盘后资金完整版，当日最终研究版本。

## 常见问题

如果网页打不开：

1. 确认 Docker Desktop 已启动。
2. 运行 `python -m ashare_replay.cli ops-check` 查看 Docker 是否满足启动条件。
3. 重新双击 `start_windows.bat`。
4. 打开 `http://127.0.0.1:8501`，不要打开文件夹路径。
5. 查看 `work/logs/ashare_replay.log`。

如果真实数据不可用：

1. 确认 `.env` 中 `APP_MODE=real`。
2. 默认免费源使用 `REAL_PROVIDER=akshare`，不需要填写密钥。
3. 确认本机或 Docker 已安装依赖；Docker 会按 `requirements.txt` 安装。
4. 运行 `python -m ashare_replay.cli provider-audit --save` 查看真实接口状态。
5. 如果使用 `REAL_PROVIDER=tushare`，再确认 `TUSHARE_TOKEN` 和账号权限。
