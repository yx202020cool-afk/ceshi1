# 项目状态

已实现并验证：

- 演示 Provider。
- AKShare 免费真实 Provider 入口、健康检查和接口自检。
- Tushare 可选真实 Provider 入口、健康检查和权限自检。
- SQLite 本地数据库初始化。
- PostgreSQL Docker 迁移文件和 Compose 服务。
- 三种报告版本生成。
- JSON、Markdown、HTML、PDF、CSV 输出。
- 行业与概念板块分开排名。
- 龙头评分、生命周期、原因归因、周线资金和候选观察池。
- Streamlit 中文网页。
- FastAPI 健康检查、报告接口、Provider 自检接口和运维自检接口。
- 定时任务和手动补跑入口。
- 演示回测。
- 长周期演示 Fixture 生成。
- Docker Desktop/Compose 启动条件自检。
- pytest、ruff、mypy 检查。

当前环境无法完成的外部验证：

- Docker Desktop 实际构建和运行：当前机器没有 `docker` 命令。
- AKShare 真实接口联网探针：当前环境不能安装或访问外部依赖时，只能检查依赖缺失状态。
- Tushare 真实数据完整报告：当前没有真实密钥和接口权限。

限制：

- 演示数据仅用于功能验证，不代表真实行情。
- 默认真实 Provider 为 AKShare 免费公开数据源，不需要密钥，但公开接口字段、更新时间和可用性可能变化。
- Tushare 是可选权限型 Provider，需要用户自行申请密钥和数据权限。
- `provider-audit` 可以自动检查依赖、接口、密钥和权限状态，但不能替用户申请付费权限，也不能修复外部公开接口变化。
- `ops-check` 可以自动检查 Docker 条件，但不能替用户安装 Docker Desktop。
- LLM 总结接口预留配置，未接入具体模型供应商；无密钥时使用确定性中文模板。
